"""
Pipeline to fetch articles from PubMed API
"""
import os
import json
import asyncio
from pathlib import Path

from api.pubmed_client import fetch_pubmed_articles
from api.models import PipelineConfig, SummaryResult
from api.llm_orchestrator import (
    generate_lay_summary,
    check_hallucinations,
)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    config = PipelineConfig()
    # 1. Fetch data from PubMed API
    articles = asyncio.run(fetch_pubmed_articles(config))

    if not articles:
        raise Exception("No articles found for given config")

    # 2 & 3. Summaries + hallucination check (sequential for clarity;
    # can be parallelised later with asyncio.gather in small batches)
    summaries: list[SummaryResult] = []
    for article in articles:
        summary_text = asyncio.run(generate_lay_summary(article))
        score, questionable_claims = asyncio.run(check_hallucinations(article, summary_text))
        summaries.append(
            SummaryResult(
                pmid=article.pmid,
                title=article.title,
                summary=summary_text,
                hallucination_score=score,
                questionable_claims=questionable_claims,
            )
        )

    summaries_file = DATA_DIR / f"pubmed_summaries_{config.year}.json"
    with summaries_file.open("w", encoding="utf-8") as fhandle:
        json.dump([a.model_dump() for a in summaries], fhandle, ensure_ascii=False, indent=2)