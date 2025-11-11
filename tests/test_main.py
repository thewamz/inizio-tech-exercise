import os

from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from api.main import app


class MainTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Ensure we don't hit real OpenAI
        os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

        transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_health_endpoint(self):
        response = await self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch("api.main.verify_trend_article")
    @patch("api.main.generate_trend_article")
    @patch("api.main.load_pubmed_summaries")
    async def test_write_article_endpoint(
        self, mock_load_pubmed_summaries, mock_generate_trend_article, mock_verify_trend_article
    ):
        mock_load_pubmed_summaries.return_value = ["summary1", "summary2"]
        mock_generate_trend_article.return_value = "Generated article body"
        mock_verify_trend_article.return_value = ["unsupported claim 1"]

        payload = {"title": "COVID-19 Research"}

        response = await self.client.post("/write-article", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "COVID-19 Research")
        self.assertEqual(data["body"], "Generated article body")
        self.assertEqual(data["unsupported_claims"], ["unsupported claim 1"])

        mock_load_pubmed_summaries.assert_called_once()
        mock_generate_trend_article.assert_called_once_with("COVID-19 Research", ["summary1", "summary2"])
        mock_verify_trend_article.assert_called_once_with("Generated article body", ["summary1", "summary2"])