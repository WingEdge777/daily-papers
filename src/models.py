from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class Paper(BaseModel):
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    title: str
    authors: List[str]
    abstract: str
    link: str
    tags: List[str]
    comment: str
    date: datetime
    
    score: float = 0.0
    summary: str = ""
    reason: str = ""
    keywords: List[str] = []


class Config(BaseModel):
    keywords: List[str]
    arxiv: 'ArxivConfig'
    llm: 'LLMConfig'
    timezone: str = "Asia/Shanghai"


class ArxivConfig(BaseModel):
    max_results: int = 500
    base_url: str = "http://export.arxiv.org/api/query"
    categories: List[str] = ["cs.CV", "cs.CL", "cs.AI", "cs.LG", "cs.MM"]


class LLMConfig(BaseModel):
    min_score: float = 70.0
    max_papers_per_keyword: int = 5
    rate_limit_interval: float = 4.1
    google: dict = {}
