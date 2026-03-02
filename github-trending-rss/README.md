# GitHub Trending Python RSS 订阅器

一个用于跟踪 GitHub Trending Python 项目的 RSS 订阅器，支持项目详情下载和 AI 分析功能。

## 功能特性

### 第一阶段：项目下载
- **自动解析**：定期抓取 GitHub Trending Python 项目
- **本地存储**：为每个项目创建单独的文件夹
- **HTML和内容提取**：保存项目详情页的HTML和文本内容
- **去重机制**：避免重复下载相同项目的页面
- **灵活配置**：支持配置保存路径和下载间隔
- **日志记录**：详细的日志记录功能

### 第二阶段：AI分析
- **内容分析**：对下载的项目页面进行内容提取
- **技术栈识别**：自动识别项目使用的技术栈
- **架构评估**：分析项目的架构设计
- **使用场景**：识别项目的应用场景
- **创新点分析**：分析项目的创新点和优势
- **报告生成**：生成Markdown格式的分析报告

## 安装依赖

```bash
pip3 install --break-system-packages beautifulsoup4 feedparser requests
```

## 使用方法

### 基本使用

```bash
# 运行完整流程：下载 -> 分析 -> 生成报告
python3 github_trending_rss.py

# 仅下载项目页面
python3 github_trending_rss.py --download-only

# 仅分析已下载的项目
python3 github_trending_rss.py --analyze-only
```

### 配置选项

创建 `config.json` 文件来自定义配置：

```json
{
    "save_path": "github_trending",
    "download_interval": 3600,
    "max_downloads": 10,
    "trending_url": "https://github.com/trending/python?since=weekly",
    "rss_url": "https://github.com/trending/python?since=weekly&format=rss",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "timeout": 30
}
```

### 命令行参数

```bash
python3 github_trending_rss.py --help

options:
  -h, --help         show this help message and exit
  --config CONFIG    配置文件路径
  --download-only    仅下载项目页面，不进行分析
  --analyze-only     仅分析已下载的项目，不进行新下载
  --max-downloads    最大下载项目数量
  --rss-url          自定义RSS源URL
```

## 输出目录结构

```
github_trending/
├── github_trending.db          # 数据库文件
├── logs/                       # 日志文件
├── huggingface/
│   └── skills/
│       ├── index.html          # 项目详情页HTML
│       ├── content.txt         # 提取的文本内容
│       ├── analysis.json       # 分析结果
│       └── analysis.md         # Markdown报告
└── [其他项目文件夹...]
```

## 测试

运行测试脚本来验证功能：

```bash
python3 test_script.py
```

## AI分析功能

当前使用简单的关键词匹配进行分析。如需更精确的分析，可以：

1. 集成 OpenAI GPT API
2. 使用 Claude API
3. 集成其他LLM服务

## 技术栈

- **Python 3.8+**
- **Beautiful Soup 4** - HTML解析
- **Requests** - HTTP请求
- **SQLite3** - 数据库存储
- **JSON** - 配置和数据分析

## 注意事项

- 请遵守 GitHub 的使用条款
- 建议合理设置下载间隔，避免请求过快
- 项目使用 SQLite 数据库，无需额外的数据库服务

## 许可证

MIT License
