import sys
import time
from datetime import datetime
from pathlib import Path
import pytz

from src.config import ConfigManager
from src.api import ArxivClient
from src.llm_scorer import LLMScorer
from src.models import Config
from src.logger import logger


class DailyPapers:
    """简化版论文抓取系统"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config: Config = ConfigManager(config_path).load()
        self.timezone = pytz.timezone(self.config.timezone)
        
        # 初始化客户端
        self.arxiv_client = ArxivClient(
            max_results=self.config.arxiv.max_results,
            categories=self.config.arxiv.target_categories
        )
        
        self.llm_scorer = self._init_llm_scorer()
    
    def _init_llm_scorer(self) -> LLMScorer:
        """初始化LLM评分器"""
        return LLMScorer(config=self.config.llm.google)
    
    def run(self) -> None:
        """主流程"""
        logger.info("=" * 50)
        logger.info("Starting DailyPapers")
        logger.info("=" * 50)
        
        try:
            current_date = datetime.now(self.timezone).strftime("%Y-%m-%d")
            
            # 1. 收集所有论文并去重
            all_papers = []
            paper_keywords = {}
            
            for keyword in self.config.keywords:
                logger.info(f"Fetching papers for: {keyword}")
                papers = self.arxiv_client.fetch_papers(keyword)
                
                for paper in papers:
                    paper_id = paper.link.split("/")[-1]
                    if paper_id not in paper_keywords:
                        all_papers.append(paper)
                        paper_keywords[paper_id] = [keyword]
                    else:
                        paper_keywords[paper_id].append(keyword)
            
            logger.info(f"Total unique papers: {len(all_papers)}")
            
            # 2. LLM评分
            scored_papers = self._score_papers(all_papers)
            
            # 3. 过滤低分论文
            filtered_papers = [
                p for p in scored_papers
                if p.score >= self.config.llm.min_score
            ]
            
            # 4. 按分数排序
            filtered_papers = sorted(
                filtered_papers,
                key=lambda p: p.score,
                reverse=True
            )
            
            logger.info(
                f"Filtered: {len(all_papers)} → {len(filtered_papers)} papers "
                f"(score >= {self.config.llm.min_score})"
            )
            
            # 5. 按关键词分组输出
            readme_content = self._build_header(current_date)
            issue_content = self._build_issue_header(current_date)
            
            for keyword in self.config.keywords:
                keyword_papers = [
                    p for p in filtered_papers
                    if keyword in paper_keywords.get(p.link.split("/")[-1], [])
                ][:self.config.llm.max_papers_per_keyword]
                
                if keyword_papers:
                    readme_content += self._format_papers(keyword, keyword_papers)
                    issue_content += self._format_papers_issue(keyword, keyword_papers)
            
            # 写入文件
            self._write_files(readme_content, issue_content)
            
            # 追加历史记录
            self._append_history(current_date, issue_content)
            
            logger.info("\n" + "=" * 50)
            logger.info("✅ DailyPapers completed successfully!")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"❌ DailyPapers failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def _score_papers(self, papers):
        """对论文进行评分"""
        logger.info(f"Scoring {len(papers)} papers...")
        
        last_request_time = 0
        min_interval = 4.1  # 每分钟最多15次，间隔4秒，加0.1秒缓冲
        
        for i, paper in enumerate(papers, 1):
            # 确保请求间隔
            current_time = time.time()
            elapsed = current_time - last_request_time
            if elapsed < min_interval and last_request_time > 0:
                wait_time = min_interval - elapsed
                logger.debug(f"Waiting {wait_time:.1f}s to maintain rate limit...")
                time.sleep(wait_time)
            
            logger.info(f"[{i}/{len(papers)}] Scoring: {paper.title[:50]}...")
            
            score, summary, reason = self.llm_scorer.score_paper(
                paper.title,
                paper.abstract
            )
            
            last_request_time = time.time()
            
            paper.score = score
            paper.summary = summary
            paper.reason = reason
        
        return papers
    
    def _build_header(self, current_date: str) -> str:
        return (
            "# Daily Papers (AI Curated)\n\n"
            "精选高质量论文，由AI评分筛选。\n\n"
            f"最后更新: {current_date}\n\n"
            "[📖 查看历史论文](HISTORY.md)\n\n"
            "---\n\n"
        )
    
    def _build_issue_header(self, current_date: str) -> str:
        date_str = datetime.now(self.timezone).strftime("%B %d, %Y")
        return (
            "---\n"
            f"title: 精选论文 - {date_str}\n"
            "labels: documentation\n"
            "---\n"
            "**请查看 [GitHub](https://github.com/zezhishao/daily-papers) 获取完整列表。**\n\n"
        )
    
    def _format_papers(self, keyword: str, papers) -> str:
        """格式化论文列表（README）"""
        lines = [f"## {keyword}\n"]
        lines.append("| 标题 | 评分 | AI摘要 | 日期 |")
        lines.append("|------|------|--------|------|")
        
        for paper in papers:
            title = f"**[{paper.title}]({paper.link})**"
            score = f"⭐ {paper.score:.0f}/100"
            summary = paper.summary or "-"
            date = paper.date.strftime("%Y-%m-%d")
            
            lines.append(f"| {title} | {score} | {summary} | {date} |")
        
        return "\n".join(lines) + "\n\n"
    
    def _format_papers_issue(self, keyword: str, papers) -> str:
        """格式化论文列表（Issue）- 详细版"""
        lines = [f"## {keyword}\n"]
        
        for i, paper in enumerate(papers, 1):
            title = f"**[{paper.title}]({paper.link})**"
            score = f"⭐ {paper.score:.0f}/100"
            date = paper.date.strftime("%Y-%m-%d")
            authors = ", ".join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors += " et al."
            tags = " ".join([f"`{tag}`" for tag in paper.tags[:3]])
            
            lines.append(f"### {i}. {title}")
            lines.append(f"- **评分**: {score} | **日期**: {date}")
            lines.append(f"- **作者**: {authors}")
            lines.append(f"- **标签**: {tags}")
            lines.append(f"- **AI摘要**: {paper.summary}")
            
            # 下拉展示原始摘要
            lines.append(f"<details>")
            lines.append(f"<summary>📄 原始摘要</summary>")
            lines.append(f"")
            lines.append(f"{paper.abstract[:500]}{'...' if len(paper.abstract) > 500 else ''}")
            lines.append(f"</details>")
            
            # 评分理由
            if paper.reason:
                lines.append(f"- **评分理由**: {paper.reason}")
            
            lines.append("")
        
        return "\n".join(lines) + "\n"
    
    def _write_files(self, readme: str, issue: str):
        """写入文件"""
        with open("README.md", "w", encoding='utf-8') as f:
            f.write(readme)
        
        Path(".github/ISSUE_TEMPLATE.md").parent.mkdir(parents=True, exist_ok=True)
        with open(".github/ISSUE_TEMPLATE.md", "w", encoding='utf-8') as f:
            f.write(issue)
        
        logger.info("✅ Files updated")
    
    def _append_history(self, date: str, issue_content: str):
        """追加历史记录"""
        history_file = Path("HISTORY.md")
        
        if not history_file.exists():
            header = "# 论文历史记录\n\n本文档记录每天的精选论文。\n\n---\n\n"
            with open(history_file, "w", encoding='utf-8') as f:
                f.write(header)
        
        # 移除 frontmatter
        content_lines = issue_content.split('\n')
        if content_lines[0] == '---':
            end_idx = content_lines.index('---', 1)
            content = '\n'.join(content_lines[end_idx + 1:])
        else:
            content = issue_content
        
        with open(history_file, "a", encoding='utf-8') as f:
            f.write(f"\n## 📅 {date}\n\n")
            f.write(content)
            f.write("\n---\n")
        
        logger.info("✅ History updated")


def main():
    app = DailyPapers()
    app.run()


if __name__ == "__main__":
    main()
