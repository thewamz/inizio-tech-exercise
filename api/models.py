from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class PubMedArticle(BaseModel):
    pmid: str
    title: str
    abstract: str
    pub_date: Optional[str] = None
    journal: Optional[str] = None


class SummaryResult(BaseModel):
    pmid: str
    title: str
    summary: str
    hallucination_score: int = 0
    questionable_claims: List[str] = Field(default_factory=list)


class Article(BaseModel):
    title: str


class TrendArticle(BaseModel):
    title: str
    body: str
    unsupported_claims: List[str] = Field(default_factory=list)


class PipelineConfig(BaseModel):
    query: str = "covid-19[Title/Abstract]"
    year: int = 2020
    retmax: int = 30   # 25–50 per brief
    force_refresh: bool = False   # re-fetch from PubMed ignoring local cache


class PipelineResult(BaseModel):
    config: PipelineConfig
    total_articles: int
    summaries: List[SummaryResult]
    trend_article: TrendArticle
