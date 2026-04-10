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
            
            readme_content = self._build_header(current_date)
            issue_content = self._build_issue_header(current_date)
            
            for keyword in self.config.keywords:
                logger.info(f"\n{'=' * 50}")
                logger.info(f"Processing: {keyword}")
                logger.info(f"{'=' * 50}")
                
                # 1. 拉取论文
                papers = self.arxiv_client.fetch_papers(keyword)
                
                if not papers:
                    logger.warning(f"No papers found for '{keyword}'")
                    continue
                
                # 2. LLM评分
                scored_papers = self._score_papers(papers)
                
                # 3. 过滤低分论文
                filtered_papers = [
                    p for p in scored_papers
                    if p.score >= self.config.llm.min_score
                ]
                
                # 4. 只保留Top N
                filtered_papers = sorted(
                    filtered_papers,
                    key=lambda p: p.score,
                    reverse=True
                )[:self.config.llm.max_papers_per_keyword]
                
                logger.info(
                    f"Filtered: {len(papers)} → {len(filtered_papers)} papers "
                    f"(score >= {self.config.llm.min_score})"
                )
                
                # 5. 生成输出
                if filtered_papers:
                    readme_content += self._format_papers(keyword, filtered_papers)
                    issue_content += self._format_papers_issue(keyword, filtered_papers)
            
            # 写入文件
            self._write_files(readme_content, issue_content)
            
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
        
        for i, paper in enumerate(papers, 1):
            logger.info(f"[{i}/{len(papers)}] Scoring: {paper.title[:50]}...")
            
            score, summary = self.llm_scorer.score_paper(
                paper.title,
                paper.abstract
            )
            
            paper.score = score
            paper.summary = summary
            
            # 避免API限流
            time.sleep(1)
        
        return papers
    
    def _build_header(self, current_date: str) -> str:
        return (
            "# Daily Papers (AI Curated)\n\n"
            "精选高质量论文，由AI评分筛选。\n\n"
            f"最后更新: {current_date}\n\n"
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
            score = f"⭐ {paper.score:.1f}/10"
            summary = paper.summary or "-"
            date = paper.date.strftime("%Y-%m-%d")
            
            lines.append(f"| {title} | {score} | {summary} | {date} |")
        
        return "\n".join(lines) + "\n\n"
    
    def _format_papers_issue(self, keyword: str, papers) -> str:
        """格式化论文列表（Issue）"""
        top_papers = papers[:self.config.output.issues_results]
        
        lines = [f"## {keyword}\n"]
        lines.append("| 标题 | 评分 |")
        lines.append("|------|------|")
        
        for paper in top_papers:
            title = f"**[{paper.title[:40]}...]({paper.link})**"
            score = f"⭐ {paper.score:.1f}"
            
            lines.append(f"| {title} | {score} |")
        
        return "\n".join(lines) + "\n\n"
    
    def _write_files(self, readme: str, issue: str):
        """写入文件"""
        with open("README.md", "w", encoding='utf-8') as f:
            f.write(readme)
        
        Path(".github/ISSUE_TEMPLATE.md").parent.mkdir(parents=True, exist_ok=True)
        with open(".github/ISSUE_TEMPLATE.md", "w", encoding='utf-8') as f:
            f.write(issue)
        
        logger.info("✅ Files updated")


def main():
    app = DailyPapers()
    app.run()


if __name__ == "__main__":
    main()
