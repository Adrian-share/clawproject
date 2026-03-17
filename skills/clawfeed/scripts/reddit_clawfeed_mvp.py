#!/usr/bin/env python3
"""
ClawFeed 本地 Reddit MVP 管道（ingest -> store -> render）

用途：
1) 从 Reddit 公共 JSON 拉取帖子（可配置 preset）
2) 统一写入本地 SQLite(signal_items)
3) 去重、打分后生成 ClawFeed digest（写入 digests 表）

运行示例：
  # 仅拉取并入库（不生成 digest）
  python3 scripts/reddit_clawfeed_mvp.py --preset ai_builders --ingest-only

  # 拉取+渲染为 clawfeed digest（默认行为）
  python3 scripts/reddit_clawfeed_mvp.py --preset ai_builders --type daily

  # 使用自定义 subreddit 列表
  python3 scripts/reddit_clawfeed_mvp.py --subreddit LocalLLaMA --subreddit MachineLearning --limit 20
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "digest.db"
USER_AGENT = "clawfeed-reddit-mvp/0.1"

PRESETS: Dict[str, Dict] = {
    "ai_builders": {
        "subreddits": ["LocalLLaMA", "MachineLearning", "OpenAI", "LangChain", "MCP"],
        "sort": "hot",
    },
    "product_news": {
        "subreddits": ["technology", "artificial", "singularity", "startups"],
        "sort": "top",
    },
}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS signal_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source TEXT NOT NULL,
          external_id TEXT NOT NULL,
          title TEXT NOT NULL,
          url TEXT NOT NULL,
          url_norm TEXT NOT NULL,
          author TEXT DEFAULT '',
          subreddit TEXT DEFAULT '',
          score REAL NOT NULL DEFAULT 0,
          comments INTEGER NOT NULL DEFAULT 0,
          published_at TEXT NOT NULL,
          raw_json TEXT DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_signal_items_source_external ON signal_items(source, external_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_signal_items_url_norm ON signal_items(url_norm);
        CREATE INDEX IF NOT EXISTS idx_signal_items_published_at ON signal_items(published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_signal_items_score ON signal_items(score DESC);
        """
    )


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def normalize_url(url: str) -> str:
    try:
        u = urllib.parse.urlparse(url)
        q = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
        q = [(k, v) for k, v in q if not k.lower().startswith("utm_")]
        query = urllib.parse.urlencode(q)
        return urllib.parse.urlunparse((u.scheme.lower(), u.netloc.lower(), u.path.rstrip("/"), "", query, ""))
    except Exception:
        return url.strip().lower()


def reddit_fetch(subreddit: str, sort: str, limit: int) -> List[dict]:
    endpoint = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    payload = http_json(endpoint)
    items = []
    for child in payload.get("data", {}).get("children", []):
        d = child.get("data", {})
        ext_id = d.get("id")
        if not ext_id or d.get("stickied"):
            continue
        url = d.get("url") or f"https://reddit.com{d.get('permalink', '')}"
        title = (d.get("title") or "").strip()
        if not title:
            continue
        created = dt.datetime.fromtimestamp(d.get("created_utc", 0), tz=dt.timezone.utc).isoformat()
        items.append(
            {
                "source": "reddit",
                "external_id": f"reddit:{ext_id}",
                "title": title,
                "url": url,
                "url_norm": normalize_url(url),
                "author": d.get("author", ""),
                "subreddit": d.get("subreddit", subreddit),
                "score": float(d.get("score", 0)),
                "comments": int(d.get("num_comments", 0)),
                "published_at": created,
                "raw_json": json.dumps(d, ensure_ascii=False),
            }
        )
    return items


def upsert_items(conn: sqlite3.Connection, items: Iterable[dict]) -> Dict[str, int]:
    inserted, updated = 0, 0
    sql = """
    INSERT INTO signal_items
      (source, external_id, title, url, url_norm, author, subreddit, score, comments, published_at, raw_json)
    VALUES
      (:source, :external_id, :title, :url, :url_norm, :author, :subreddit, :score, :comments, :published_at, :raw_json)
    ON CONFLICT(source, external_id) DO UPDATE SET
      title=excluded.title,
      url=excluded.url,
      url_norm=excluded.url_norm,
      author=excluded.author,
      subreddit=excluded.subreddit,
      score=excluded.score,
      comments=excluded.comments,
      published_at=excluded.published_at,
      raw_json=excluded.raw_json
    """
    for row in items:
      exists = conn.execute(
          "SELECT 1 FROM signal_items WHERE source=? AND external_id=?",
          (row["source"], row["external_id"]),
      ).fetchone()
      conn.execute(sql, row)
      if exists:
          updated += 1
      else:
          inserted += 1
    conn.commit()
    return {"inserted": inserted, "updated": updated}


def load_ranked(conn: sqlite3.Connection, topn: int = 20) -> List[dict]:
    rows = conn.execute(
        """
        SELECT source, title, url, url_norm, author, subreddit, score, comments, published_at
        FROM signal_items
        ORDER BY published_at DESC
        LIMIT 500
        """
    ).fetchall()
    seen = set()
    ranked = []
    for r in rows:
        url_norm = r[3]
        tnorm = re.sub(r"\W+", "", (r[1] or "").lower())
        key = url_norm or tnorm
        if key in seen:
            continue
        seen.add(key)
        # 轻量融合评分：热度 + 评论 + 新鲜度
        published = dt.datetime.fromisoformat((r[8] or "").replace("Z", "+00:00"))
        age_h = max((dt.datetime.now(dt.timezone.utc) - published).total_seconds() / 3600, 1)
        rank = r[6] + (r[7] * 0.8) - (math.log(age_h, 1.6) * 8)
        ranked.append(
            {
                "source": r[0],
                "title": r[1],
                "url": r[2],
                "author": r[4],
                "subreddit": r[5],
                "score": r[6],
                "comments": r[7],
                "published_at": r[8],
                "rank": rank,
            }
        )
    ranked.sort(key=lambda x: x["rank"], reverse=True)
    return ranked[:topn]


def build_markdown(ranked: List[dict], preset: str, subs: List[str]) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"☀️ ClawFeed | {now} Asia/Shanghai",
        "",
        "## Reddit Signals",
        f"- Preset: `{preset}`",
        f"- Subreddits: {', '.join('r/' + s for s in subs)}",
        "",
        "## Merged Ranked Feed",
    ]
    if not ranked:
        lines.append("- 暂无数据")
        return "\n".join(lines) + "\n"

    for i, x in enumerate(ranked, 1):
        lines.append(
            f"{i}. [{x['title']}]({x['url']}) "
            f"(r/{x['subreddit']} u/{x['author']} · ⬆ {int(x['score'])} · 💬 {int(x['comments'])})"
        )
    return "\n".join(lines) + "\n"


def insert_digest(conn: sqlite3.Connection, digest_type: str, content: str, metadata: dict) -> int:
    cur = conn.execute(
        "INSERT INTO digests(type, content, metadata) VALUES (?, ?, ?)",
        (digest_type, content, json.dumps(metadata, ensure_ascii=False)),
    )
    conn.commit()
    return int(cur.lastrowid)


def main() -> None:
    ap = argparse.ArgumentParser(description="Local ClawFeed Reddit MVP pipeline")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--preset", default="ai_builders", choices=sorted(PRESETS.keys()))
    ap.add_argument("--subreddit", action="append", default=[])
    ap.add_argument("--sort", default=None, choices=["hot", "new", "top", "rising"])
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--topn", type=int, default=12)
    ap.add_argument("--type", default="daily", choices=["4h", "daily", "weekly", "monthly"])
    ap.add_argument("--ingest-only", action="store_true")
    args = ap.parse_args()

    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))

    ensure_schema(conn)

    preset = PRESETS[args.preset]
    subreddits = args.subreddit if args.subreddit else list(preset["subreddits"])
    sort = args.sort or preset["sort"]

    all_items = []
    for s in subreddits:
        all_items.extend(reddit_fetch(s, sort=sort, limit=args.limit))

    stats = upsert_items(conn, all_items)
    print(f"[ingest] total={len(all_items)} inserted={stats['inserted']} updated={stats['updated']}")

    if args.ingest_only:
        return

    ranked = load_ranked(conn, topn=args.topn)
    md = build_markdown(ranked, args.preset, subreddits)
    digest_id = insert_digest(
        conn,
        digest_type=args.type,
        content=md,
        metadata={
            "pipeline": "reddit_clawfeed_mvp",
            "preset": args.preset,
            "subreddits": subreddits,
            "sort": sort,
            "ingest_stats": stats,
            "ranked_count": len(ranked),
        },
    )
    print(f"[render] digest_id={digest_id} type={args.type} ranked={len(ranked)}")


if __name__ == "__main__":
    main()
