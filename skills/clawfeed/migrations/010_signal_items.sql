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
