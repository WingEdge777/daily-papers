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


class Config(BaseModel):
    keywords: List[str]
    arxiv: 'ArxivConfig'
    llm: 'LLMConfig'
    timezone: str = "Asia/Shanghai"


class ArxivConfig(BaseModel):
    max_results: int = 50
    target_categories: List[str] = ["cs.LG", "cs.AI", "stat.ML"]


class LLMConfig(BaseModel):
    min_score: float = 70.0
    max_papers_per_keyword: int = 5
    google: dict = {}
