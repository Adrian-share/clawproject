#!/usr/bin/env python3
"""
测试脚本 - 验证github_trending_rss.py的功能
"""

from github_trending_rss import GitHubTrendingRSS
import os
import json
from pathlib import Path


def test_basic_functionality():
    """测试基本功能"""
    print("=== 测试 GitHub Trending RSS 订阅器 ===")
    
    # 创建实例
    rss = GitHubTrendingRSS()
    
    # 获取已下载项目
    projects = rss.get_downloaded_projects()
    print(f"✅ 已下载项目数量: {len(projects)}")
    
    # 检查项目文件夹
    base_dir = Path(rss.config["save_path"])
    assert base_dir.exists(), "保存路径不存在"
    
    for project in projects:
        project_dir = base_dir / project["author"] / project["name"]
        print(f"\n📁 项目: {project['author']}/{project['name']}")
        
        # 检查项目文件
        html_file = project_dir / "index.html"
        content_file = project_dir / "content.txt"
        analysis_file = project_dir / "analysis.json"
        report_file = project_dir / "analysis.md"
        
        if html_file.exists():
            print("✅ HTML文件已下载")
        if content_file.exists():
            print("✅ 文本内容已提取")
        if analysis_file.exists():
            print("✅ 分析结果已生成")
        if report_file.exists():
            print("✅ Markdown报告已生成")
        
        # 检查分析结果
        if analysis_file.exists():
            with open(analysis_file, "r", encoding="utf-8") as f:
                analysis = json.load(f)
            assert "summary" in analysis, "分析结果缺少summary字段"
            assert "tech_stack" in analysis, "分析结果缺少tech_stack字段"
            assert len(analysis["tech_stack"]) > 0, "技术栈为空"


def test_analysis_quality():
    """测试分析质量"""
    print("\n=== 测试分析质量 ===")
    
    rss = GitHubTrendingRSS()
    projects = rss.get_downloaded_projects()
    
    for project in projects:
        project_dir = Path(rss.config["save_path"]) / project["author"] / project["name"]
        analysis_file = project_dir / "analysis.json"
        
        if analysis_file.exists():
            with open(analysis_file, "r", encoding="utf-8") as f:
                analysis = json.load(f)
            
            print(f"\n📊 项目: {project['author']}/{project['name']}")
            print(f"   技术栈: {', '.join(analysis['tech_stack'])}")
            print(f"   应用场景: {', '.join(analysis['use_cases'])}")
            print(f"   Stars: {project['stars']} | Forks: {project['forks']}")


def test_config():
    """测试配置"""
    print("\n=== 测试配置 ===")
    
    rss = GitHubTrendingRSS()
    assert rss.config["save_path"] == "github_trending"
    assert rss.config["max_downloads"] == 3
    assert rss.config["download_interval"] == 3600
    print("✅ 配置加载成功")


def main():
    """主测试函数"""
    try:
        test_basic_functionality()
        test_analysis_quality()
        test_config()
        
        print("\n🎉 所有功能测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    
    return True


if __name__ == "__main__":
    main()
