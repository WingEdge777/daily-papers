import html
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Set

import pytz

from src.api import ArxivClient
from src.category_match import resolve_category
from src.config import ConfigManager
from src.llm_scorer import LLMScorer
from src.logger import logger
from src.models import Config, Paper


class DailyPapers:
    """Simplified paper fetching system"""
    SEEN_IDS_FILE = "arxiv_seen_ids.tsv"
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config: Config = ConfigManager(config_path).load()
        self.timezone = pytz.timezone(self.config.timezone)
        
        # Initialize clients
        self.arxiv_client = ArxivClient(
            max_results=self.config.arxiv.max_results,
            base_url=self.config.arxiv.base_url,
            categories=self.config.arxiv.categories
        )
        
        self.llm_scorer = self._init_llm_scorer()
    
    def _init_llm_scorer(self) -> LLMScorer:
        """Initialize LLM scorer"""
        return LLMScorer(config=self.config.llm.google)
    
    def run(self) -> None:
        """Main workflow"""
        logger.info("=" * 50)
        logger.info("Starting DailyPapers")
        logger.info("=" * 50)
        
        try:
            current_date = datetime.now(self.timezone).strftime("%Y-%m-%d")
            
            # 1. Fetch latest papers
            all_papers = self.arxiv_client.fetch_papers()
            logger.info(f"Total papers fetched: {len(all_papers)}")

            # 1.1 Deduplicate against persisted historical IDs
            seen_ids = self._load_seen_ids(current_date)
            all_papers = self._deduplicate_papers(all_papers, seen_ids)
            logger.info(f"Total papers after deduplication: {len(all_papers)}")
            
            # 2. LLM scoring and categorization
            scored_papers = self._score_papers(all_papers)
            
            # 3. Filter low-scoring papers
            filtered_papers = [
                p for p in scored_papers
                if p.score >= self.config.llm.min_score and p.category
            ]
            
            # 4. Sort by score
            filtered_papers = sorted(
                filtered_papers,
                key=lambda p: p.score,
                reverse=True
            )
            
            logger.info(
                f"Filtered: {len(all_papers)} → {len(filtered_papers)} papers "
                f"(score >= {self.config.llm.min_score})"
            )
            
            # 5. Group output by category
            papers_content = ""
            daily_content = self._build_daily_header(current_date)
            selected_papers: List[Paper] = []
            
            for keyword in self.config.keywords:
                keyword_papers = [
                    p for p in filtered_papers
                    if p.category == keyword
                ][:self.config.llm.max_papers_per_keyword]
                
                if keyword_papers:
                    selected_papers.extend(keyword_papers)
                    papers_content += self._format_papers(keyword, keyword_papers)
                    daily_content += self._format_papers_detail(keyword, keyword_papers)
            
            # Write files
            readme_content = self._build_readme(current_date, papers_content)
            self._write_files(readme_content, daily_content, current_date)
            self._append_seen_ids(current_date, selected_papers)
            
            logger.info("\n" + "=" * 50)
            logger.info("✅ DailyPapers completed successfully!")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"❌ DailyPapers failed: {e}")
            traceback.print_exc()
            sys.exit(1)

    def _load_seen_ids(self, current_date: str) -> Set[str]:
        """Load persisted arXiv IDs from the index file."""
        papers_dir = Path("papers")
        papers_dir.mkdir(exist_ok=True)
        seen_file = papers_dir / self.SEEN_IDS_FILE

        if not seen_file.exists():
            self._bootstrap_seen_ids_index(seen_file)

        seen_ids: Set[str] = set()
        try:
            lines = seen_file.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            logger.warning(f"Failed to read seen IDs file {seen_file}: {e}")
            return set()

        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                logger.debug(f"Skipping malformed seen IDs record: {line}")
                continue
            record_date, arxiv_id = parts[0].strip(), parts[1].strip()
            if record_date and arxiv_id:
                seen_ids.add(arxiv_id)

        logger.info(f"Loaded {len(seen_ids)} IDs from {seen_file} for deduplication")
        return seen_ids

    def _bootstrap_seen_ids_index(self, seen_file: Path) -> None:
        """Initialize seen IDs index from historical markdown files once."""
        papers_dir = seen_file.parent
        records: Set[str] = set()

        for paper_file in papers_dir.glob("*.md"):
            file_date = paper_file.stem
            try:
                content = paper_file.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning(f"Failed to read historical file {paper_file}: {e}")
                continue

            paper_ids = self._extract_arxiv_ids_from_markdown(content)
            for paper_id in paper_ids:
                records.add(f"{file_date}\t{paper_id}")

        sorted_records = sorted(records)
        try:
            with open(seen_file, "w", encoding="utf-8") as f:
                for record in sorted_records:
                    f.write(f"{record}\n")
        except OSError as e:
            logger.warning(f"Failed to initialize seen IDs file {seen_file}: {e}")
            return

        logger.info(
            f"Initialized {seen_file} with {len(sorted_records)} records from history"
        )

    def _extract_arxiv_ids_from_markdown(self, content: str) -> Set[str]:
        """Extract normalized arXiv IDs from markdown text."""
        paper_ids: Set[str] = set()
        for url in re.findall(r"https?://arxiv\.org/(?:abs|pdf)/[^\s\)\]<>\"']+", content):
            normalized_id = self._normalize_arxiv_id(url)
            if normalized_id:
                paper_ids.add(normalized_id)
        return paper_ids

    def _append_seen_ids(self, current_date: str, papers: List[Paper]) -> None:
        """Append today's selected paper IDs to seen IDs index."""
        seen_file = Path("papers") / self.SEEN_IDS_FILE
        today_ids: Set[str] = set()
        for paper in papers:
            paper_id = self._normalize_arxiv_id(paper.link)
            if paper_id:
                today_ids.add(paper_id)

        if not today_ids:
            return

        existing_today: Set[str] = set()
        if seen_file.exists():
            try:
                lines = seen_file.read_text(encoding="utf-8").splitlines()
            except OSError as e:
                logger.warning(f"Failed to read seen IDs file {seen_file}: {e}")
                lines = []

            for line in lines:
                if not line.strip():
                    continue
                parts = line.split("\t", 1)
                if len(parts) != 2:
                    continue
                record_date, arxiv_id = parts[0].strip(), parts[1].strip()
                if record_date == current_date and arxiv_id:
                    existing_today.add(arxiv_id)

        new_ids = sorted(today_ids - existing_today)
        if not new_ids:
            return

        try:
            with open(seen_file, "a", encoding="utf-8") as f:
                for paper_id in new_ids:
                    f.write(f"{current_date}\t{paper_id}\n")
        except OSError as e:
            logger.warning(f"Failed to append seen IDs to {seen_file}: {e}")
            return

        logger.info(f"Appended {len(new_ids)} IDs to {seen_file}")

    @staticmethod
    def _normalize_arxiv_id(value: str) -> str:
        """Normalize arXiv URL/ID to an ID without version suffix."""
        text = (value or "").strip()
        if not text:
            return ""

        match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#\s]+)", text)
        if match:
            text = match.group(1)

        text = text.replace(".pdf", "").strip()
        text = re.sub(r"^arxiv:", "", text, flags=re.IGNORECASE)
        text = re.sub(r"v\d+$", "", text, flags=re.IGNORECASE)
        return text.lower()

    def _paper_dedup_key(self, paper: Paper) -> str:
        """Generate a stable deduplication key for a paper."""
        arxiv_id = self._normalize_arxiv_id(paper.link)
        if arxiv_id:
            return arxiv_id
        return f"title:{paper.title.strip().lower()}"

    def _deduplicate_papers(self, papers: List[Paper], historical_ids: Set[str]) -> List[Paper]:
        """Deduplicate fetched papers against history and within current batch."""
        fetched_unique_ids: Set[str] = set()
        for paper in papers:
            fetched_unique_ids.add(self._paper_dedup_key(paper))

        overlap_count = len(fetched_unique_ids & historical_ids)
        logger.info(
            f"Dedup stats: seen_ids={len(historical_ids)}, "
            f"fetched_unique_ids={len(fetched_unique_ids)}, "
            f"overlap_before_dedup={overlap_count}"
        )

        seen_ids = set(historical_ids)
        unique_papers: List[Paper] = []
        dropped_from_history = 0
        dropped_within_batch = 0

        for paper in papers:
            dedup_key = self._paper_dedup_key(paper)
            if dedup_key in seen_ids:
                if dedup_key in historical_ids:
                    dropped_from_history += 1
                else:
                    dropped_within_batch += 1
                continue
            seen_ids.add(dedup_key)
            unique_papers.append(paper)

        logger.info(
            f"Dedup result: dropped_from_history={dropped_from_history}, "
            f"dropped_within_batch={dropped_within_batch}, "
            f"remaining={len(unique_papers)}"
        )
        return unique_papers
    
    def _score_papers(self, papers: List[Paper]) -> List[Paper]:
        """Score and categorize papers"""
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
            paper.category = resolve_category(category, self.config.keywords)
        
        return papers
    
    def _build_readme(self, current_date: str, papers_content: str) -> str:
        marker = "<!-- PAPERS_START -->"
        
        try:
            with open("README.md", "r", encoding='utf-8') as f:
                content = f.read()
            if marker in content:
                return content.split(marker)[0] + marker + f"\n\n## {current_date}\n\n" + papers_content
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
            "---\n\n"
            f"{marker}\n\n## {current_date}\n\n{papers_content}"
        )
    
    def _build_daily_header(self, current_date: str) -> str:
        return f"# 精选论文 - {current_date}\n\n"
    
    @staticmethod
    def _markdown_table_cell(text: str) -> str:
        """避免表格列被 | 或换行打断。"""
        return " ".join(text.replace("\n", " ").split()).replace("|", "\\|")

    def _format_papers(self, keyword: str, papers: List[Paper]) -> str:
        """Format paper list for README"""
        lines = [f"## {keyword}\n"]
        lines.append("| 标题 | 评分 | Gemini 摘要 | 评分理由 | 原始摘要 |")
        lines.append("|------|------|-------------|----------|----------|")
        
        for paper in papers:
            title = (
                f"**[{self._markdown_table_cell(paper.title)}]({paper.link})**"
            )
            score = f"⭐ {paper.score:.0f}/100"
            summary = self._markdown_table_cell(paper.summary)
            reason = self._markdown_table_cell(paper.reason) if paper.reason else ""
            abstract_safe = html.escape(
                " ".join(paper.abstract.replace("\n", " ").split()),
                quote=False,
            )
            details = (
                f"<details><summary>展开</summary>{abstract_safe}</details>"
            )
            lines.append(f"| {title} | {score} | {summary} | {reason} | {details} |")
        
        return "\n".join(lines) + "\n\n"
    
    def _format_papers_detail(self, keyword: str, papers: List[Paper]) -> str:
        """Format detailed paper list"""
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
            
            # Dropdown for original abstract
            lines.append("<details>")
            lines.append("<summary>原始摘要</summary>")
            lines.append("")
            lines.append(
                html.escape(
                    " ".join(paper.abstract.replace("\n", " ").split()),
                    quote=False,
                )
            )
            lines.append("</details>")
            
            # Scoring reason
            if paper.reason:
                lines.append(f"- **评分理由**: {paper.reason}")
            
            lines.append("")
        
        return "\n".join(lines) + "\n"
    
    def _write_files(self, readme: str, daily: str, date: str):
        """Write output files"""
        # Write README
        with open("README.md", "w", encoding='utf-8') as f:
            f.write(readme)
        
        # Write daily file
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
