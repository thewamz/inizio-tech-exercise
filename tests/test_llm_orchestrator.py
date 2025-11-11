import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch, AsyncMock

from api.models import PubMedArticle, SummaryResult
from api import llm_orchestrator


class TestLLMOrchestrator(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Ensure we don't hit real OpenAI
        os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

    @patch("api.llm_orchestrator.LLM")
    async def test_generate_lay_summary(self, mock_llm):
        article = PubMedArticle(
            pmid="123456",
            title="Sample Covid Study",
            abstract="This study investigates Covid-19 in a small population.",
            pub_date="2020-01-01",
            journal="Test Journal",
        )

        mock_llm.ainvoke = AsyncMock()
        mock_llm.ainvoke.return_value = type("R", (), {"content": "Fake lay summary."})

        summary = await llm_orchestrator.generate_lay_summary(article)
        self.assertEqual(summary, "Fake lay summary.")
        mock_llm.ainvoke.assert_awaited()

    @patch("api.llm_orchestrator.LLM")
    async def test_check_hallucinations_valid_json(self, mock_llm):
        article = PubMedArticle(
            pmid="123456",
            title="Sample Covid Study",
            abstract="The abstract describes Covid-19 in adults.",
            pub_date=None,
            journal=None,
        )
        summary = "This is a test summary."

        fake_json = """
        {
          "hallucination_score": 2,
          "questionable_claims": [
            "Claim 1",
            "Claim 2"
          ]
        }
        """

        mock_llm.ainvoke = AsyncMock()
        mock_llm.ainvoke.return_value = type("R", (), {"content": fake_json})

        score, claims = await llm_orchestrator.check_hallucinations(article, summary)
        self.assertEqual(score, 2)
        self.assertEqual(claims, ["Claim 1", "Claim 2"])

    @patch("api.llm_orchestrator.LLM")
    async def test_check_hallucinations_bad_json(self, mock_llm):
        article = PubMedArticle(
            pmid="123456",
            title="Sample Covid Study",
            abstract="The abstract describes Covid-19 in adults.",
            pub_date=None,
            journal=None,
        )
        summary = "This is a test summary."

        mock_llm.ainvoke = AsyncMock()
        mock_llm.ainvoke.return_value = type("R", (), {"content": "not-json"})

        score, claims = await llm_orchestrator.check_hallucinations(article, summary)
        self.assertEqual(score, 0)
        self.assertEqual(claims, [])

    @patch("api.llm_orchestrator.LLM")
    async def test_generate_trend_article(self, mock_llm):
        summaries = [
            SummaryResult(
                pmid="1",
                title="Study 1",
                summary="Summary 1",
                hallucination_score=0,
                questionable_claims=[],
            ),
            SummaryResult(
                pmid="2",
                title="Study 2",
                summary="Summary 2",
                hallucination_score=1,
                questionable_claims=["Something off"],
            ),
        ]

        mock_llm.ainvoke = AsyncMock()
        mock_llm.ainvoke.return_value = type("R", (), {"content": "Fake trends article."})

        text = await llm_orchestrator.generate_trend_article("trendy article", summaries)
        self.assertIn("fake trends article", text.lower())

    @patch("api.llm_orchestrator.LLM")
    async def test_verify_trend_article(self, mock_llm):
        summaries = [
            SummaryResult(
                pmid="1",
                title="Study 1",
                summary="Summary 1",
                hallucination_score=0,
                questionable_claims=[],
            )
        ]
        article_text = "Trends in Covid Research in 2020"

        fake_json = """
        {
          "unsupported_claims": [
            "This claim is unsupported.",
            "This one too."
          ]
        }
        """

        mock_llm.ainvoke = AsyncMock()
        mock_llm.ainvoke.return_value = type("R", (), {"content": fake_json})

        unsupported = await llm_orchestrator.verify_trend_article(article_text, summaries)
        self.assertEqual(
            unsupported,
            ["This claim is unsupported.", "This one too."],
        )