#!/usr/bin/env python3
"""
GitHub Trending Python RSS Fetcher and Parser
Part of x-tweet-fetcher skill
支持直接抓取网页和解析RSS源
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.request
import datetime
import re
from bs4 import BeautifulSoup
import feedparser

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data')
DB_PATH = os.path.join(DATA_DIR, 'github_trending.db')
RSS_CONFIG_PATH = os.path.join(DATA_DIR, 'rss_feeds.json')
DEFAULT_CONFIG = {
    "github_trending_python": {
        "name": "GitHub Trending Python",
        "url": "https://github.com/trending/python",
        "description": "每日热门 Python 项目",
        "poll_interval": "12h",
        "last_fetched": None,
        "enabled": True
    }
}


def init_db():
    """初始化数据库"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建项目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT,
            repo_url TEXT UNIQUE,
            description TEXT,
            language TEXT,
            stars INTEGER,
            forks INTEGER,
            today_stars INTEGER,
            created_at TEXT,
            fetched_at TEXT
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_repo_url ON projects(repo_url)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fetched_at ON projects(fetched_at)')
    
    conn.commit()
    conn.close()


def load_config():
    """加载配置"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if not os.path.exists(RSS_CONFIG_PATH):
        with open(RSS_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    
    with open(RSS_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config):
    """保存配置"""
    with open(RSS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def fetch_rss_feed(url):
    """获取RSS源"""
    try:
        print(f"Fetching RSS feed from: {url}")
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
        
        return feedparser.parse(content)
        
    except Exception as e:
        print(f"Error fetching RSS feed: {e}", file=sys.stderr)
        return None


def parse_rss_feed(feed):
    """解析RSS源"""
    projects = []
    
    if feed.bozo != 0:
        print(f"RSS feed parsing error: {feed.bozo_exception}", file=sys.stderr)
        return []
    
    for entry in feed.entries:
        try:
            # 解析项目信息
            repo_name = entry.title
            repo_url = entry.link
            
            # 从链接中提取项目名称（格式: https://github.com/user/repo）
            if 'github.com' in repo_url:
                parts = repo_url.strip('/').split('/')
                if len(parts) >= 4:
                    repo_name = parts[3] + "/" + parts[4]
            
            description = entry.get('summary', '').replace('<[^<]+?>', '')  # 去除HTML标签
            
            projects.append({
                "repo_name": repo_name,
                "repo_url": repo_url,
                "description": description,
                "language": "Python",
                "stars": 0,
                "forks": 0,
                "today_stars": 0,
                "created_at": entry.get('published', ''),
                "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        except Exception as e:
            print(f"Error parsing RSS entry: {e}", file=sys.stderr)
            continue
    
    print(f"Parsed {len(projects)} projects from RSS feed")
    return projects


def fetch_github_trending():
    """获取 GitHub Trending Python 数据（直接抓取网页）"""
    config = load_config()
    url = config["github_trending_python"]["url"]
    
    try:
        print(f"Fetching GitHub Trending Python from: {url}")
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
        
        return html
        
    except Exception as e:
        print(f"Error fetching GitHub Trending: {e}", file=sys.stderr)
        return None


def parse_html(html):
    """解析 GitHub Trending 网页"""
    soup = BeautifulSoup(html, 'html.parser')
    projects = []
    
    # 找到所有项目行
    repo_rows = soup.find_all('article', {'class': 'Box-row'})
    
    for row in repo_rows:
        try:
            # 解析项目信息
            repo_name = row.find('h2', {'class': 'h3'}).find('a').text.strip().replace(' ', '').replace('\n', '')
            
            repo_url = 'https://github.com' + row.find('h2', {'class': 'h3'}).find('a')['href']
            
            description = ''
            desc_elem = row.find('p', {'class': 'col-9'})
            if desc_elem:
                description = desc_elem.text.strip()
            
            # 解析语言
            language = ''
            lang_elem = row.find('span', {'itemprop': 'programmingLanguage'})
            if lang_elem:
                language = lang_elem.text.strip()
            
            # 解析星标和 Fork 数量
            stars = 0
            forks = 0
            today_stars = 0
            
            # 查找星标、Fork、和今天新增的星标
            meta_info = row.find_all('a', {'class': 'Link'})
            for item in meta_info:
                if '/stargazers' in item['href']:
                    stars_text = item.text.strip().replace(',', '')
                    if stars_text:
                        stars = int(stars_text)
                elif '/forks' in item['href']:
                    forks_text = item.text.strip().replace(',', '')
                    if forks_text:
                        forks = int(forks_text)
            
            # 查找今天新增的星标
            today_stars_elem = row.find('span', {'class': 'd-inline-block'})
            if today_stars_elem and 'stars today' in today_stars_elem.text:
                today_stars_text = today_stars_elem.text.strip().replace(' stars today', '').replace(',', '')
                if today_stars_text:
                    today_stars = int(today_stars_text)
            
            projects.append({
                "repo_name": repo_name,
                "repo_url": repo_url,
                "description": description,
                "language": language,
                "stars": stars,
                "forks": forks,
                "today_stars": today_stars,
                "created_at": '',
                "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        except Exception as e:
            print(f"Error parsing project: {e}", file=sys.stderr)
            continue
    
    print(f"Parsed {len(projects)} projects")
    return projects


def store_projects(projects):
    """存储项目到数据库"""
    if not projects:
        return 0, 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_count = 0
    updated_count = 0
    
    for project in projects:
        try:
            # 检查是否已存在
            cursor.execute('SELECT id FROM projects WHERE repo_url = ?', (project["repo_url"],))
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有项目
                cursor.execute('''
                    UPDATE projects 
                    SET description = ?, language = ?, stars = ?, forks = ?, 
                        today_stars = ?, fetched_at = ?
                    WHERE repo_url = ?
                ''', (
                    project["description"], project["language"], 
                    project["stars"], project["forks"], 
                    project["today_stars"], project["fetched_at"],
                    project["repo_url"]
                ))
                updated_count += 1
            else:
                # 插入新项目
                cursor.execute('''
                    INSERT OR IGNORE INTO projects 
                    (repo_name, repo_url, description, language, stars, 
                     forks, today_stars, created_at, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project["repo_name"], project["repo_url"],
                    project["description"], project["language"],
                    project["stars"], project["forks"],
                    project["today_stars"], 
                    project["created_at"],
                    project["fetched_at"]
                ))
                new_count += 1
        
        except Exception as e:
            print(f"Error storing project {project.get('repo_name', 'Unknown')}: {e}", file=sys.stderr)
            continue
    
    conn.commit()
    conn.close()
    
    return new_count, updated_count


def get_recent_projects(days=7):
    """获取最近 days 天的项目"""
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT repo_name, repo_url, description, language, stars, forks, today_stars, fetched_at
        FROM projects
        WHERE fetched_at >= datetime('now', '-{} days')
        ORDER BY stars DESC
    '''.format(days))
    
    projects = []
    for row in cursor.fetchall():
        projects.append({
            "repo_name": row[0],
            "repo_url": row[1],
            "description": row[2],
            "language": row[3],
            "stars": row[4],
            "forks": row[5],
            "today_stars": row[6],
            "fetched_at": row[7]
        })
    
    conn.close()
    return projects


def print_projects(projects, format='json'):
    """打印项目信息"""
    if format == 'text':
        for project in projects:
            print(f"📦 {project['repo_name']}")
            print(f"⭐ Stars: {project['stars']} | Forks: {project['forks']} | Today: {project['today_stars']}")
            print(f"📄 {project['description']}")
            print(f"🔗 {project['repo_url']}")
            print(f"💻 {project['language']}")
            print(f"⏰ {project['fetched_at']}")
            print('-' * 50)
    else:
        print(json.dumps(projects, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Trending Python RSS Fetcher"
    )
    parser.add_argument('--fetch', action='store_true', help='获取最新数据')
    parser.add_argument('--list', action='store_true', help='列出项目')
    parser.add_argument('--days', type=int, default=7, help='列出最近几天的项目（默认7天）')
    parser.add_argument('--format', choices=['json', 'text'], default='json', 
                       help='输出格式（默认 JSON）')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--config', action='store_true', help='显示配置信息')
    parser.add_argument('--rss-url', help='使用指定的RSS源URL')
    parser.add_argument('--download-only', action='store_true', help='仅下载项目页面')
    parser.add_argument('--analyze-only', action='store_true', help='仅分析已下载的项目')
    
    args = parser.parse_args()
    
    # 初始化配置
    config = load_config()
    
    if args.init:
        print("初始化数据库...")
        init_db()
        print("✅ 数据库初始化完成")
        return 0
    
    if args.config:
        print("配置信息:")
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0
    
    # 确保数据库存在
    init_db()
    
    if args.fetch:
        print("开始获取 GitHub Trending Python 数据...")
        
        projects = []
        
        if args.rss_url:
            # 使用指定的RSS源
            feed = fetch_rss_feed(args.rss_url)
            if feed:
                projects = parse_rss_feed(feed)
        else:
            # 使用默认方式
            html = fetch_github_trending()
            if html:
                projects = parse_html(html)
        
        if projects:
            new_count, updated_count = store_projects(projects)
            
            # 更新配置中的 last_fetched
            config["github_trending_python"]["last_fetched"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_config(config)
            
            print(f"✅ 获取完成")
            print(f"📊 新项目: {new_count} | 更新项目: {updated_count}")
            
            return 0 if new_count > 0 or updated_count > 0 else 1
        else:
            print("❌ 未能获取到数据", file=sys.stderr)
            return 1
    
    if args.list:
        print(f"列出最近 {args.days} 天的 GitHub Trending Python 项目...")
        projects = get_recent_projects(args.days)
        
        if projects:
            print_projects(projects, args.format)
            print(f"📊 共 {len(projects)} 个项目")
            return 0
        else:
            print("❌ 没有找到项目", file=sys.stderr)
            return 2
    
    # 如果没有指定参数，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"程序错误: {e}", file=sys.stderr)
        sys.exit(1)
