import os
import json
from pathlib import Path

from .models import PubMedArticle, PipelineConfig, SummaryResult

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

def load_pubmed_articles(config: PipelineConfig):
    """Load pubmed articles from JSON file"""
    file_path = DATA_DIR / f"pubmed_{config.year}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"File located at: '{file_path}' does not exist")

    with file_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    return [PubMedArticle(**row) for row in articles]


def load_pubmed_summaries(config: PipelineConfig):
    """Load pubmed summaries from JSON file"""
    file_path = DATA_DIR / f"pubmed_summaries_{config.year}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"File located at: '{file_path}' does not exist")

    with file_path.open("r", encoding="utf-8") as f:
        summaries = json.load(f)

    return [SummaryResult(**row) for row in summaries]