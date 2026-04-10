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
            base_url=self.config.arxiv.base_url,
            categories=self.config.arxiv.categories
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
            
            # 1. 获取最新论文
            all_papers = self.arxiv_client.fetch_papers()
            logger.info(f"Total papers: {len(all_papers)}")
            
            # 2. LLM评分和分类
            scored_papers = self._score_papers(all_papers)
            
            # 3. 过滤低分论文
            filtered_papers = [
                p for p in scored_papers
                if p.score >= self.config.llm.min_score and p.category
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
            
            # 5. 按分类分组输出
            papers_content = ""
            daily_content = self._build_daily_header(current_date)
            
            for keyword in self.config.keywords:
                keyword_papers = [
                    p for p in filtered_papers
                    if p.category == keyword
                ][:self.config.llm.max_papers_per_keyword]
                
                if keyword_papers:
                    papers_content += self._format_papers(keyword, keyword_papers)
                    daily_content += self._format_papers_detail(keyword, keyword_papers)
            
            # 写入文件
            readme_content = self._build_readme(current_date, papers_content)
            self._write_files(readme_content, daily_content, current_date)
            
            logger.info("\n" + "=" * 50)
            logger.info("✅ DailyPapers completed successfully!")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"❌ DailyPapers failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def _score_papers(self, papers):
        """对论文进行评分和分类"""
        logger.info(f"Scoring {len(papers)} papers...")
        
        last_request_time = 0
        min_interval = self.config.llm.rate_limit_interval
        
        for i, paper in enumerate(papers, 1):
            current_time = time.time()
            elapsed = current_time - last_request_time
            if elapsed < min_interval and last_request_time > 0:
                wait_time = min_interval - elapsed
                logger.debug(f"Waiting {wait_time:.1f}s to maintain rate limit...")
                time.sleep(wait_time)
            
            logger.info(f"[{i}/{len(papers)}] Scoring: {paper.title[:50]}...")
            
            score, summary, reason, category = self.llm_scorer.score_paper(
                paper.title,
                paper.abstract,
                self.config.keywords
            )
            
            last_request_time = time.time()
            
            paper.score = score
            paper.summary = summary
            paper.reason = reason
            paper.category = category
        
        return papers
    
    def _build_readme(self, current_date: str, papers_content: str) -> str:
        marker = "<!-- PAPERS_START -->"
        
        try:
            with open("README.md", "r", encoding='utf-8') as f:
                content = f.read()
            if marker in content:
                return content.split(marker)[0] + marker + "\n\n" + papers_content
        except FileNotFoundError:
            pass
        
        return (
            "# Daily Papers - AI精选论文\n\n"
            "**自动抓取ArXiv论文，使用 Google Gemini 评分筛选高质量内容**\n\n"
            "专为 **CV（计算机视觉）** 和 **LLM（大语言模型）** 研究者设计\n\n"
            "## ✨ 特性\n\n"
            "- **🆓 完全免费** - 使用 Google AI Studio 免费 API\n"
            "- **🤖 自动运行** - GitHub Actions 每天自动运行\n"
            "- **🎯 智能评分** - 四维度评估（0-100分）\n"
            "- **💡 AI摘要** - 自动生成论文核心贡献摘要\n\n"
            f"**最后更新**: {current_date}\n\n"
            "[📖 查看历史论文](papers/)\n\n"
            "---\n\n"
            f"{marker}\n\n{papers_content}"
        )
    
    def _build_daily_header(self, current_date: str) -> str:
        return f"# 精选论文 - {current_date}\n\n"
    
    def _format_papers(self, keyword: str, papers) -> str:
        """格式化论文列表（README）"""
        lines = [f"## {keyword}\n"]
        lines.append("| 标题 | 评分 | 摘要 | 日期 |")
        lines.append("|------|------|------|------|")
        
        for paper in papers:
            title = f"**[{paper.title}]({paper.link})**"
            score = f"⭐ {paper.score:.0f}/100"
            date = paper.date.strftime("%Y-%m-%d")
            
            abstract_preview = paper.abstract[:100] + "..." if len(paper.abstract) > 100 else paper.abstract
            summary_cell = f"{paper.summary}<br><details><summary>📄 原始摘要</summary>{abstract_preview}</details>"
            
            lines.append(f"| {title} | {score} | {summary_cell} | {date} |")
        
        return "\n".join(lines) + "\n\n"
    
    def _format_papers_detail(self, keyword: str, papers) -> str:
        """格式化论文列表（详细版）"""
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
    
    def _write_files(self, readme: str, daily: str, date: str):
        """写入文件"""
        # 写入 README
        with open("README.md", "w", encoding='utf-8') as f:
            f.write(readme)
        
        # 写入每日文件
        papers_dir = Path("papers")
        papers_dir.mkdir(exist_ok=True)
        
        daily_file = papers_dir / f"{date}.md"
        with open(daily_file, "w", encoding='utf-8') as f:
            f.write(daily)
        
        logger.info(f"✅ Files updated: README.md, papers/{date}.md")


def main():
    app = DailyPapers()
    app.run()


if __name__ == "__main__":
    main()
