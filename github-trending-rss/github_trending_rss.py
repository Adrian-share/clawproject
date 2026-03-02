#!/usr/bin/env python3
"""
GitHub Trending Python RSS 订阅器
支持下载项目详情和AI分析功能
"""

import os
import sys
import time
import logging
import requests
import feedparser
import re
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse, urljoin
import hashlib
import argparse
import sqlite3


class GitHubTrendingRSS:
    """GitHub Trending Python RSS 订阅器"""

    def __init__(self, config=None):
        self.config = config or self._load_config()
        self._setup_logging()
        self._setup_database()

    def _load_config(self):
        """加载配置文件"""
        config_file = Path("config.json")
        default_config = {
            "save_path": "github_trending",
            "download_interval": 3600,  # 1小时
            "max_downloads": 10,
            "trending_url": "https://github.com/trending/python?since=weekly",
            "rss_url": "https://github.com/trending/python?since=weekly&format=rss",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "timeout": 30
        }

        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return {**default_config, **json.load(f)}
        return default_config

    def _setup_logging(self):
        """设置日志记录"""
        log_dir = Path(self.config["save_path"]) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_dir / f"github_trending_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _setup_database(self):
        """设置数据库"""
        db_path = Path(self.config["save_path"]) / "github_trending.db"
        self.db_path = str(db_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    name TEXT,
                    author TEXT,
                    description TEXT,
                    stars INTEGER,
                    forks INTEGER,
                    language TEXT,
                    last_download TIMESTAMP,
                    last_analysis TIMESTAMP
                )
            """)
            conn.commit()

    def _get_project_hash(self, url):
        """生成项目唯一标识符"""
        return hashlib.md5(url.encode()).hexdigest()

    def _should_download(self, url):
        """检查是否应该下载项目页面"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_download FROM projects WHERE url = ?
            """, (url,))
            result = cursor.fetchone()

            if not result:
                return True

            last_download = datetime.fromisoformat(result[0])
            interval = timedelta(seconds=self.config["download_interval"])
            return datetime.now() > last_download + interval

    def _update_download_time(self, url):
        """更新下载时间"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE projects SET last_download = ? WHERE url = ?
            """, (datetime.now().isoformat(), url))
            conn.commit()

    def _save_project_info(self, project_info):
        """保存项目基本信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO projects 
                (url, name, author, description, stars, forks, language, last_download)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_info["url"],
                project_info["name"],
                project_info["author"],
                project_info["description"],
                project_info["stars"],
                project_info["forks"],
                project_info["language"],
                datetime.now().isoformat()
            ))
            conn.commit()

    def _parse_rss_feed(self, rss_url=None):
        """解析HTML页面获取项目信息"""
        trending_url = self.config["trending_url"]
        self.logger.info(f"解析 HTML 页面: {trending_url}")

        headers = {
            "User-Agent": self.config["user_agent"]
        }

        try:
            response = requests.get(trending_url, headers=headers, timeout=self.config["timeout"])
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            projects = []

            # 查找项目卡片
            project_cards = soup.find_all("article", class_="Box-row")
            self.logger.info(f"找到 {len(project_cards)} 个项目卡片")

            for card in project_cards[:self.config["max_downloads"]]:
                project = self._parse_project_card(card)
                if project:
                    projects.append(project)

            self.logger.info(f"解析到 {len(projects)} 个项目")
            return projects

        except Exception as e:
            self.logger.error(f"解析HTML页面失败: {e}")
            return []

    def _parse_project_card(self, card):
        """解析项目卡片"""
        try:
            # 提取项目链接
            repo_link = card.find("h2").find("a")
            if not repo_link:
                return None

            repo_path = repo_link["href"].strip("/")
            url = f"https://github.com/{repo_path}"

            # 提取作者和项目名
            author, name = repo_path.split("/", 1) if "/" in repo_path else (None, repo_path)

            # 提取描述
            description = ""
            desc_elem = card.find("p", class_="col-9")
            if desc_elem:
                description = desc_elem.get_text().strip()

            # 提取Stars和Forks
            stars = 0
            forks = 0

            # 查找包含Stars和Forks的div
            meta_div = card.find("div", class_="f6")
            if meta_div:
                meta_text = meta_div.get_text()
                stars_match = re.search(r"(\d+(?:\.\d+)?[kK]?) stars?", meta_text)
                if stars_match:
                    stars_str = stars_match.group(1)
                    if 'k' in stars_str.lower():
                        stars = int(float(stars_str[:-1]) * 1000)
                    else:
                        stars = int(stars_str)

                forks_match = re.search(r"(\d+(?:\.\d+)?[kK]?) forks?", meta_text)
                if forks_match:
                    forks_str = forks_match.group(1)
                    if 'k' in forks_str.lower():
                        forks = int(float(forks_str[:-1]) * 1000)
                    else:
                        forks = int(forks_str)

            return {
                "url": url,
                "name": name,
                "author": author,
                "description": description,
                "stars": stars,
                "forks": forks,
                "language": "Python"  # 默认语言
            }

        except Exception as e:
            self.logger.error(f"解析项目卡片失败: {e}")
            return None

    def _parse_feed_entry(self, entry):
        """解析RSS条目"""
        try:
            # 从标题中提取作者和项目名
            title_match = re.match(r"(.+)/(.+)", entry.title)
            if not title_match:
                return None

            author = title_match.group(1)
            name = title_match.group(2)

            # 提取项目URL
            url = entry.link
            if not url.startswith("https://github.com/"):
                url = urljoin("https://github.com/", url.lstrip("/"))

            # 解析描述
            description = entry.summary
            if description:
                soup = BeautifulSoup(description, "html.parser")
                description = soup.get_text().strip()

            # 提取星星和forks数量
            stars = 0
            forks = 0
            stars_match = re.search(r"(\d+(?:\.\d+)?[kK]?) stars", description)
            if stars_match:
                stars_str = stars_match.group(1)
                if 'k' in stars_str.lower():
                    stars = int(float(stars_str[:-1]) * 1000)
                else:
                    stars = int(stars_str)

            forks_match = re.search(r"(\d+(?:\.\d+)?[kK]?) forks", description)
            if forks_match:
                forks_str = forks_match.group(1)
                if 'k' in forks_str.lower():
                    forks = int(float(forks_str[:-1]) * 1000)
                else:
                    forks = int(forks_str)

            return {
                "url": url,
                "name": name,
                "author": author,
                "description": description,
                "stars": stars,
                "forks": forks,
                "language": "Python"  # 默认语言
            }

        except Exception as e:
            self.logger.error(f"解析RSS条目失败: {e}")
            return None

    def _download_project_page(self, url, save_dir):
        """下载项目详情页"""
        self.logger.info(f"下载项目页面: {url}")

        headers = {
            "User-Agent": self.config["user_agent"]
        }

        try:
            response = requests.get(url, headers=headers, timeout=self.config["timeout"])
            response.raise_for_status()

            # 保存HTML内容
            html_file = save_dir / "index.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(response.text)

            # 提取页面文本内容
            soup = BeautifulSoup(response.text, "html.parser")

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            # 提取主要内容
            content = ""
            readme = soup.find("div", class_="readme")
            if readme:
                content = readme.get_text()
            else:
                # 尝试其他常见的内容选择器
                main_content = soup.find("main")
                if main_content:
                    content = main_content.get_text()
                else:
                    content = soup.get_text()

            # 保存文本内容
            text_file = save_dir / "content.txt"
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(content.strip())

            return True

        except Exception as e:
            self.logger.error(f"下载项目页面失败 {url}: {e}")
            return False

    def _create_project_dir(self, project_info):
        """创建项目文件夹"""
        base_dir = Path(self.config["save_path"])
        author_dir = base_dir / project_info["author"]
        project_dir = author_dir / project_info["name"]
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def download_projects(self, projects=None):
        """下载项目详情页到本地"""
        if not projects:
            projects = self._parse_rss_feed()

        downloaded_projects = []
        for project in projects:
            if self._should_download(project["url"]):
                project_dir = self._create_project_dir(project)
                if self._download_project_page(project["url"], project_dir):
                    self._save_project_info(project)
                    self._update_download_time(project["url"])
                    downloaded_projects.append(project)
                    self.logger.info(f"成功下载项目: {project['author']}/{project['name']}")
                time.sleep(2)  # 避免请求过快

        self.logger.info(f"下载完成，共下载 {len(downloaded_projects)} 个项目")
        return downloaded_projects

    def analyze_project(self, project_info):
        """分析项目页面（AI分析）"""
        project_dir = self._create_project_dir(project_info)
        content_file = project_dir / "content.txt"

        if not content_file.exists():
            self.logger.warning(f"内容文件不存在: {content_file}")
            return None

        with open(content_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 使用简单的AI分析（可以替换为真实的LLM API）
        analysis = self._simple_analysis(content, project_info)

        # 保存分析结果
        analysis_file = project_dir / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        # 更新分析时间
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE projects SET last_analysis = ? WHERE url = ?
            """, (datetime.now().isoformat(), project_info["url"]))
            conn.commit()

        return analysis

    def _simple_analysis(self, content, project_info):
        """简单的项目分析（用于测试）"""
        self.logger.info(f"分析项目: {project_info['author']}/{project_info['name']}")

        # 简单的关键词匹配
        tech_stack = []
        keywords = {
            "Python": ["python", "django", "flask", "fastapi", "numpy", "pandas"],
            "Web": ["web", "api", "server", "client", "frontend", "backend"],
            "AI/ML": ["machine learning", "deep learning", "neural network", "ai", "ml"],
            "Data": ["data", "database", "sql", "big data", "analytics"],
            "DevOps": ["devops", "docker", "kubernetes", "ci/cd", "automation"],
            "Mobile": ["mobile", "ios", "android", "react native", "flutter"]
        }

        content_lower = content.lower()
        for category, terms in keywords.items():
            for term in terms:
                if term in content_lower:
                    tech_stack.append(category)
                    break

        # 简单的内容分析
        use_cases = []
        if "api" in content_lower or "web" in content_lower:
            use_cases.append("Web应用开发")
        if "machine learning" in content_lower or "ai" in content_lower:
            use_cases.append("人工智能应用")
        if "data" in content_lower or "analytics" in content_lower:
            use_cases.append("数据分析")
        if "automation" in content_lower or "devops" in content_lower:
            use_cases.append("自动化运维")

        return {
            "project": project_info,
            "summary": self._generate_summary(content, project_info),
            "tech_stack": list(set(tech_stack)),
            "architecture": "项目架构信息需要进一步分析",
            "use_cases": use_cases,
            "innovation_points": ["需要进一步分析项目的创新点"],
            "advantages": ["项目具有一定的技术优势"],
            "potential_issues": ["需要进一步分析项目的潜在问题"]
        }

    def _generate_summary(self, content, project_info):
        """生成项目摘要"""
        # 简单的摘要生成
        lines = content.split('\n')
        relevant_lines = []
        for line in lines:
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                relevant_lines.append(line)

        if relevant_lines:
            summary = " ".join(relevant_lines[:3])
            return summary[:300] + "..." if len(summary) > 300 else summary
        else:
            return project_info['description']

    def analyze_all_projects(self):
        """分析所有项目"""
        self.logger.info("开始分析所有项目")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, name, author, description, stars, forks, language 
                FROM projects WHERE last_download IS NOT NULL
            """)
            projects = cursor.fetchall()

        results = []
        for project_data in projects:
            project_info = {
                "url": project_data[0],
                "name": project_data[1],
                "author": project_data[2],
                "description": project_data[3],
                "stars": project_data[4],
                "forks": project_data[5],
                "language": project_data[6]
            }

            result = self.analyze_project(project_info)
            if result:
                results.append(result)

        self.logger.info(f"分析完成，共分析 {len(results)} 个项目")
        return results

    def generate_markdown_report(self, analysis):
        """生成Markdown格式的分析报告"""
        project = analysis["project"]
        report = []

        report.append(f"# {project['name']}\n")
        report.append(f"**作者**: {project['author']}\n")
        report.append(f"**语言**: {project['language']}\n")
        report.append(f"**Stars**: {project['stars']} | **Forks**: {project['forks']}\n")
        report.append(f"**链接**: {project['url']}\n")
        report.append("\n---\n")

        report.append("## 项目描述\n")
        report.append(project['description'] + "\n")
        report.append("\n---\n")

        report.append("## 项目概述\n")
        report.append(analysis['summary'] + "\n")
        report.append("\n---\n")

        if analysis['tech_stack']:
            report.append("## 技术栈\n")
            for tech in analysis['tech_stack']:
                report.append(f"- {tech}\n")
            report.append("\n---\n")

        if analysis['architecture']:
            report.append("## 架构设计\n")
            report.append(analysis['architecture'] + "\n")
            report.append("\n---\n")

        if analysis['use_cases']:
            report.append("## 应用场景\n")
            for use_case in analysis['use_cases']:
                report.append(f"- {use_case}\n")
            report.append("\n---\n")

        if analysis['innovation_points']:
            report.append("## 创新点\n")
            for point in analysis['innovation_points']:
                report.append(f"- {point}\n")
            report.append("\n---\n")

        if analysis['advantages']:
            report.append("## 优势\n")
            for advantage in analysis['advantages']:
                report.append(f"- {advantage}\n")
            report.append("\n---\n")

        if analysis['potential_issues']:
            report.append("## 潜在问题\n")
            for issue in analysis['potential_issues']:
                report.append(f"- {issue}\n")

        return "\n".join(report)

    def save_markdown_report(self, analysis):
        """保存Markdown报告"""
        project_dir = self._create_project_dir(analysis["project"])
        report_file = project_dir / "analysis.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(self.generate_markdown_report(analysis))

        self.logger.info(f"Markdown报告已保存: {report_file}")

    def run_full_pipeline(self):
        """运行完整流程：下载 -> 分析 -> 生成报告"""
        self.logger.info("开始完整流程")

        # 第一阶段：下载项目页面
        projects = self.download_projects()

        # 第二阶段：分析项目
        if projects:
            analyses = []
            for project in projects:
                analysis = self.analyze_project(project)
                if analysis:
                    analyses.append(analysis)

            # 生成报告
            for analysis in analyses:
                self.save_markdown_report(analysis)

        self.logger.info("完整流程完成")

    def get_downloaded_projects(self):
        """获取已下载项目列表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, name, author, description, stars, forks, language, last_download
                FROM projects WHERE last_download IS NOT NULL
            """)
            projects = []
            for row in cursor.fetchall():
                projects.append({
                    "url": row[0],
                    "name": row[1],
                    "author": row[2],
                    "description": row[3],
                    "stars": row[4],
                    "forks": row[5],
                    "language": row[6],
                    "last_download": row[7]
                })
        return projects


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="GitHub Trending Python RSS 订阅器"
    )
    parser.add_argument(
        "--config",
        help="配置文件路径",
        default="config.json"
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="仅下载项目页面，不进行分析"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="仅分析已下载的项目，不进行新下载"
    )
    parser.add_argument(
        "--max-downloads",
        type=int,
        help="最大下载项目数量"
    )
    parser.add_argument(
        "--rss-url",
        help="自定义RSS源URL"
    )

    args = parser.parse_args()

    # 初始化配置
    config = None
    if args.config and Path(args.config).exists():
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)

    if args.max_downloads:
        if config is None:
            config = {}
        config["max_downloads"] = args.max_downloads

    # 创建实例
    rss_parser = GitHubTrendingRSS(config)

    # 运行相应的功能
    if args.download_only:
        rss_parser.download_projects()
    elif args.analyze_only:
        rss_parser.analyze_all_projects()
    else:
        rss_parser.run_full_pipeline()


if __name__ == "__main__":
    main()
