from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    PipelineConfig,
    TrendArticle,
    Article
)
from .llm_orchestrator import (
    generate_trend_article,
    verify_trend_article,
)
from .utils import load_pubmed_summaries

app = FastAPI(
    title="Covid PubMed LLM App",
    description="Write article using async LLM-orchestration",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in real deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}


@app.post("/write-article", response_model=TrendArticle, tags=["write-article"])
async def write_article(article: Article):
    config = PipelineConfig()
    summaries = load_pubmed_summaries(config)

    # Generate article
    trend_article_body = await generate_trend_article(article.title, summaries)

    # Perform accuracy guard for trends article
    unsupported_claims = await verify_trend_article(trend_article_body, summaries)
    trend = TrendArticle(
        title=article.title,
        body=trend_article_body,
        unsupported_claims=unsupported_claims,
    )

    return trend
