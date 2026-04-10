import urllib.parse
import urllib.request
from datetime import datetime
from typing import List, Optional
import feedparser

from .models import Paper
from .logger import logger


class ArxivClient:
    """ArXiv API客户端"""
    
    def __init__(self, max_results: int = 50, categories: Optional[List[str]] = None):
        self.max_results = max_results
        self.categories = categories or ["cs.LG", "cs.AI", "stat.ML"]
        self.base_url = "http://export.arxiv.org/api/query"
    
    def fetch_papers(self, keyword: str) -> List[Paper]:
        """获取论文"""
        try:
            # 构建查询
            query = self._build_query(keyword)
            url = f"{self.base_url}?search_query={query}&max_results={self.max_results}&sortBy=lastUpdatedDate"
            url = urllib.parse.quote(url, safe="%/:=&?~#+!$,;'@()*[]")
            
            logger.info(f"Fetching papers for: {keyword}")
            
            # 请求
            response = urllib.request.urlopen(url).read().decode('utf-8')
            feed = feedparser.parse(response)
            
            # 解析
            papers = []
            for entry in feed.entries:
                paper = self._parse_entry(entry)
                # 过滤类别
                if self._matches_categories(paper):
                    papers.append(paper)
            
            logger.info(f"Fetched {len(papers)} papers for '{keyword}'")
            return papers
            
        except Exception as e:
            logger.error(f"Failed to fetch papers: {e}")
            return []
    
    def _build_query(self, keyword: str) -> str:
        """构建查询字符串"""
        return f'ti:"{keyword}"+OR+abs:"{keyword}"'
    
    def _parse_entry(self, entry: dict) -> Paper:
        """解析论文条目"""
        return Paper(
            title=self._clean_text(entry.get('title', '')),
            authors=[self._clean_text(a.get('name', '')) for a in entry.get('authors', [])],
            abstract=self._clean_text(entry.get('summary', '')),
            link=self._clean_text(entry.get('link', '')),
            tags=[t.get('term', '') for t in entry.get('tags', [])],
            comment=self._clean_text(entry.get('arxiv_comment', '')),
            date=self._parse_date(entry.get('updated', ''))
        )
    
    def _matches_categories(self, paper: Paper) -> bool:
        """检查论文是否符合目标类别"""
        for tag in paper.tags:
            for cat in self.categories:
                if tag.startswith(cat):
                    return True
        return False
    
    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(text.replace("\n", " ").split())
    
    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return datetime.now()
