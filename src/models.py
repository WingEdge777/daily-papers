from datetime import datetime
from typing import List, Optional
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
    
    # LLM评分字段
    score: float = 0.0
    summary: str = ""


class Config(BaseModel):
    keywords: List[str]
    arxiv: 'ArxivConfig'
    llm: 'LLMConfig'
    output: 'OutputConfig'
    timezone: str = "Asia/Shanghai"


class ArxivConfig(BaseModel):
    max_results: int = 50
    target_categories: List[str] = ["cs.LG", "cs.AI", "stat.ML"]


class LLMConfig(BaseModel):
    min_score: float = 7.0
    max_papers_per_keyword: int = 10
    google: dict = {}


class OutputConfig(BaseModel):
    issues_results: int = 10
    show_summary: bool = True
