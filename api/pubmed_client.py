import asyncio
import json
import os
from pathlib import Path
import httpx

from xml.etree import ElementTree as ET

from .models import PubMedArticle, PipelineConfig

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


async def _pubmed_search_ids(config: PipelineConfig) -> list[str]:
    """Search PubMed for PMIDs matching query + year (async)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "pubmed",
                "term": f"{config.query} AND {config.year}[pdat]",
                "retmode": "json",
                "retmax": config.retmax,
            },
        )
    response.raise_for_status()

    return response.json().get("esearchresult", {}).get("idlist", [])


async def _pubmed_fetch_summaries(pmids: list[str]) -> dict:
    """Fetch summaries for PMIDs (title, journal, pubdate) asynchronously."""
    if not pmids:
        return None

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
            },
        )
    response.raise_for_status()

    return response.json().get("result", {})


async def _pubmed_fetch_abstracts(pmids: list[str]) -> dict:
    """Fetch abstracts for PMIDs asynchronously."""
    if not pmids:
        return None

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={
                "db": "pubmed",
                "rettype": "abstract",
                "retmode": "xml",
                "id": ",".join(pmids),
            },
        )
    response.raise_for_status()

    root = ET.fromstring(response.text)

    abstracts: dict[str, str] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_elem = article.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else None
        abs_elem = article.find(".//Abstract/AbstractText")
        abstract = abs_elem.text if abs_elem is not None else ""
        if pmid:
            abstracts[pmid] = abstract

    return abstracts


async def fetch_pubmed_articles(config: PipelineConfig) -> list[PubMedArticle]:
    """
    Fetch ~retmax PubMed articles for the query/year.
    Results are cached to data/pubmed_{year}.json.
    """
    file_path = DATA_DIR / f"pubmed_articles_{config.year}.json"

    pmids = await _pubmed_search_ids(config)
    summaries, abstracts = await _fetch_details(pmids)

    if not summaries:
        summaries = {}

    if not abstracts:
        abstracts = {}

    articles: list[PubMedArticle] = []
    for pmid in pmids:
        abstract = abstracts.get(pmid, "")
        if abstract is None:
            abstract = ""

        info = summaries.get(pmid, {})
        article = PubMedArticle(
            pmid=pmid,
            title=info.get("title", ""),
            abstract=abstract,
            pub_date=info.get("pubdate", None),
            journal=info.get("fulljournalname", None),
        )
        if article.abstract:
            articles.append(article)

    with file_path.open("w", encoding="utf-8") as fhandle:
        json.dump([a.model_dump() for a in articles], fhandle, ensure_ascii=False, indent=2)

    return articles


async def _fetch_details(pmids: list[str]) -> tuple[dict, dict]:
    """Helper to fetch summaries and abstracts concurrently."""
    if not pmids:
        return None, None

    # run multiple asynchronous operations and get results once they complete
    summaries, abstracts = await asyncio.gather(
        _pubmed_fetch_summaries(pmids),
        _pubmed_fetch_abstracts(pmids),
    )
    return summaries, abstracts
