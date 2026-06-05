import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import List, Optional

import feedparser

from src.logger import logger
from src.models import Paper

ARXIV_REQUEST_TIMEOUT_SEC = 30
ARXIV_MAX_RETRIES = 3
ARXIV_RETRY_DELAY_429_SEC = 10
ARXIV_RETRY_DELAY_NETWORK_SEC = 5
ARXIV_RETRYABLE_HTTP_CODES = (429, 502, 503, 504)
ARXIV_USER_AGENT = "DailyPapersBot/1.0 (+https://github.com/WingEdge777/daily-papers; mailto:handkodu@gmail.com)"


class ArxivClient:
    """ArXiv API client"""

    def __init__(
        self,
        max_results: int = 500,
        base_url: str = "https://export.arxiv.org/api/query",
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

        body = self._fetch_feed_body(url)

        feed = feedparser.parse(body)
        if getattr(feed, "bozo", False) and feed.bozo_exception:
            logger.warning(f"ArXiv feed parse warning: {feed.bozo_exception}")

        papers: List[Paper] = []
        for entry in feed.entries:
            paper = self._parse_entry(entry)
            papers.append(paper)

        logger.info(f"Fetched {len(papers)} papers")
        return papers

    def _fetch_feed_body(self, url: str) -> str:
        """Fetch ArXiv feed with custom User-Agent and retry on transient errors."""
        headers = {"User-Agent": ARXIV_USER_AGENT}
        req = urllib.request.Request(url, headers=headers)

        for attempt in range(1, ARXIV_MAX_RETRIES + 1):
            try:
                with urllib.request.urlopen(req, timeout=ARXIV_REQUEST_TIMEOUT_SEC) as resp:
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                if e.code in ARXIV_RETRYABLE_HTTP_CODES and attempt < ARXIV_MAX_RETRIES:
                    if e.code == 429:
                        retry_after = e.headers.get("Retry-After")
                        sleep_sec = self._parse_retry_after(retry_after, ARXIV_RETRY_DELAY_429_SEC)
                    else:
                        sleep_sec = (2 ** (attempt - 1)) + 3
                    logger.warning(
                        f"ArXiv HTTP {e.code}, sleeping {sleep_sec}s "
                        f"before retry {attempt + 1}/{ARXIV_MAX_RETRIES}"
                    )
                    time.sleep(sleep_sec)
                    continue
                logger.error(f"ArXiv HTTP error: {e.code} {e.reason}")
                raise
            except urllib.error.URLError as e:
                if attempt < ARXIV_MAX_RETRIES:
                    sleep_sec = (2 ** (attempt - 1)) + 3
                    logger.warning(
                        f"ArXiv network error: {e.reason}, sleeping "
                        f"{sleep_sec}s before retry "
                        f"{attempt + 1}/{ARXIV_MAX_RETRIES}"
                    )
                    time.sleep(sleep_sec)
                    continue
                logger.error(f"ArXiv network error: {e.reason}")
                raise
            except (TimeoutError, socket.timeout) as e:
                if attempt < ARXIV_MAX_RETRIES:
                    sleep_sec = (2 ** (attempt - 1)) + 3
                    logger.warning(
                        f"ArXiv timeout error: {e}, sleeping "
                        f"{sleep_sec}s before retry "
                        f"{attempt + 1}/{ARXIV_MAX_RETRIES}"
                    )
                    time.sleep(sleep_sec)
                    continue
                logger.error(f"ArXiv timeout error: {e}")
                raise

        raise RuntimeError("ArXiv fetch retries exhausted")

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
    def _parse_retry_after(retry_after: Optional[str], default: int) -> int:
        try:
            if retry_after is None:
                return default
            parsed = int(retry_after)
            return parsed if parsed > 0 else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError, OSError) as e:
            logger.warning(f"Failed to parse date {date_str!r}: {e}")
            return datetime.now()
