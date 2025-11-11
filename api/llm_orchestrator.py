from __future__ import annotations

import json
import os
from typing import List, Tuple

from langchain_openai import ChatOpenAI
# from langchain.schema import HumanMessage
from langchain_core.messages import HumanMessage

from .models import PubMedArticle, SummaryResult, TrendArticle

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

LLM = ChatOpenAI(
    model=OPENAI_MODEL,
    temperature=0.2,
)


async def generate_lay_summary(article: PubMedArticle) -> str:
    """Generate a 1-paragraph layperson summary of the article abstract (async)."""
    prompt = f"""
    You are a medical science writer for the general public.

    Write ONE short paragraph (4-6 sentences) in plain English explaining this Covid-19 research article
    to a high-school-level reader.

    Avoid jargon. If you must use a technical term, briefly define it.

    Make sure you mention:
    - Who or what the study looked at (epidemiology / population).
    - Any key risk factors or causes discussed.
    - How Covid-19 was diagnosed or measured in the study.
    - What happened over time or outcomes (disease progression / prognosis).
    - Any prevention or treatment ideas (vaccines, drugs, public health measures, etc.) if mentioned.

    Do NOT add any information that is not in the abstract.

    ARTICLE METADATA:
    Title: {article.title}
    Journal: {article.journal}
    Publication date: {article.pub_date}
    PMID: {article.pmid}

    ABSTRACT:
    \"\"\"{article.abstract}\"\"\""""

    resp = await LLM.ainvoke([HumanMessage(content=prompt)])
    return resp.content.strip()


async def check_hallucinations(article: PubMedArticle, summary: str) -> Tuple[int, List[str]]:
    """
    Ask the LLM to identify claims in the summary that are NOT supported by the original abstract.
    Returns (hallucination_score, questionable_claims).
    """
    prompt = f"""
    You are checking a summary for factual accuracy against a source abstract.

    TASK:
    1. Read the original abstract.
    2. Read the lay summary.
    3. Identify any statements in the summary that are NOT clearly supported by the abstract.

    Return JSON ONLY in this exact format:
    {{
    "hallucination_score": <integer number of questionable or unsupported claims>,
    "questionable_claims": [
        "claim 1 text",
        "claim 2 text"
    ]
    }}

    ORIGINAL ABSTRACT:
    \"\"\"{article.abstract}\"\"\"


    SUMMARY:
    \"\"\"{summary}\"\"\""""

    resp = await LLM.ainvoke([HumanMessage(content=prompt)])
    raw = resp.content.strip()

    try:
        data = json.loads(raw)
        score = int(data.get("hallucination_score", 0))
        claims = [str(c) for c in data.get("questionable_claims", [])]
        return score, claims
    except Exception:
        return 0, []


async def generate_trend_article(title: str, summaries: List[SummaryResult]) -> str:
    """
    Generate an article in plain English
    """
    # bullet_points = []
    # for s in summaries:
    #     bullet_points.append(
    #         f"- PMID {s.pmid}: {s.title}\n  Summary: {s.summary}"
    #     )
    # bullet_block = "\n".join(bullet_points)

    article_summaries = "\n".join(s.summary for s in summaries)

    prompt = f"""
    You are writing an educational article for the general public.

    Write an article titled: "{title}".

    Use only the information from the study summaries below. Do NOT invent facts.

    GOALS:
    - Explain in plain English what patterns you see across these studies.
    - Highlight similarities and differences in:
    - Who was studied (populations, locations).
    - Risk factors and causes.
    - How Covid-19 was diagnosed or measured.
    - Disease progression and outcomes.
    - Prevention strategies and treatments studied.
    - Comment on trends across the year (for example: early vs later studies),
    but only if you can infer that from the publication dates or summaries.
    - Avoid speculation unless the summaries clearly mention it.
    - Use a friendly, accessible tone.

    Length: about 800–1200 words.

    STUDY SUMMARIES:
    {article_summaries}
    """

    resp = await LLM.ainvoke([HumanMessage(content=prompt)])
    return resp.content.strip()


async def verify_trend_article(
    trend_article_text: str,
    summaries: List[SummaryResult],
) -> List[str]:
    """
    Accuracy guard:
    - Ask the LLM to find statements in the trend article that are NOT supported
      by any of the individual summaries.
    - Return a list of unsupported claims.
    """
    # bullet_points = []
    # for s in summaries:
    #     bullet_points.append(
    #         f"- PMID {s.pmid}: {s.title}\n  Summary: {s.summary}"
    #     )
    # bullet_block = "\n".join(bullet_points)

    article_summaries = "\n".join(s.summary for s in summaries)

    prompt = f"""
    You are an accuracy checker.

    You are given:
    1. A long-form article about 'Trends in Covid Research in 2020'.
    2. A set of study summaries that were used to create that article.

    Your job:
    - Identify any specific factual claims in the article that are NOT clearly supported by ANY of the summaries.
    - A "claim" could be a statement about:
    - who was affected,
    - where something happened,
    - risk factors,
    - diagnostic tools,
    - treatments,
    - outcomes,
    - or trends over time.

    Important:
    - If a claim is even loosely supported by more than one summary, consider it supported.
    - Only flag statements that truly appear speculative or unsupported.

    Return JSON ONLY in this exact format:
    {{
    "unsupported_claims": [
        "claim 1 text",
        "claim 2 text"
    ]
    }}

    ARTICLE:
    \"\"\"{trend_article_text}\"\"\"


    SUMMARIES:
    {article_summaries}
    """

    resp = await LLM.ainvoke([HumanMessage(content=prompt)])
    raw = resp.content.strip()

    try:
        data = json.loads(raw)
        return [str(c) for c in data.get("unsupported_claims", [])]
    except Exception:
        return []
