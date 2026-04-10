import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import List, Optional

import feedparser

from src.logger import logger
from src.models import Paper

ARXIV_REQUEST_TIMEOUT_SEC = 60


class ArxivClient:
    """ArXiv API client"""

    def __init__(
        self,
        max_results: int = 500,
        base_url: str = "http://export.arxiv.org/api/query",
        categories: Optional[List[str]] = None,
    ):
        self.max_results = max_results
        self.base_url = base_url
        self.categories = categories or ["cs.CV", "cs.CL", "cs.AI", "cs.LG", "cs.MM"]

    def fetch_papers(self) -> List[Paper]:
        """Fetch latest papers"""
        query = " OR ".join([f"cat:{cat}" for cat in self.categories])
        params = {
            "search_query": query,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = self.base_url + "?" + urllib.parse.urlencode(params)

        logger.info(f"Fetching latest {self.max_results} papers from cs categories...")

        try:
            with urllib.request.urlopen(url, timeout=ARXIV_REQUEST_TIMEOUT_SEC) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            logger.error(f"ArXiv HTTP error: {e.code} {e.reason}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"ArXiv network error: {e.reason}")
            raise

        feed = feedparser.parse(body)
        if getattr(feed, "bozo", False) and feed.bozo_exception:
            logger.warning(f"ArXiv feed parse warning: {feed.bozo_exception}")

        papers: List[Paper] = []
        for entry in feed.entries:
            paper = self._parse_entry(entry)
            papers.append(paper)

        logger.info(f"Fetched {len(papers)} papers")
        return papers

    def _parse_entry(self, entry: dict) -> Paper:
        """Parse paper entry"""
        return Paper(
            title=self._clean_text(entry.get("title", "")),
            authors=[self._clean_text(a.get("name", "")) for a in entry.get("authors", [])],
            abstract=self._clean_text(entry.get("summary", "")),
            link=self._clean_text(entry.get("link", "")),
            tags=[t.get("term", "") for t in entry.get("tags", [])],
            comment=self._clean_text(entry.get("arxiv_comment", "")),
            date=self._parse_date(entry.get("published", "")),
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(text.replace("\n", " ").split())

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError, OSError) as e:
            logger.warning(f"Failed to parse date {date_str!r}: {e}")
            return datetime.now()
