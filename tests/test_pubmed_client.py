from __future__ import annotations

import json
import importlib
import shutil
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch, AsyncMock, MagicMock

from api.models import PubMedArticle, PipelineConfig
from api import pubmed_client


class MockResponse:
    def __init__(self, response_dict: dict | None, response_text: str | None = None):
        self.repsonse_dict = response_dict
        self.repsonse_text = response_text

    def raise_for_status(self):
        return None

    @property
    def text(self):
        return self.repsonse_text

    def json(self):
        return self.repsonse_dict


class TestPubMedClient(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use a temporary DATA_DIR to avoid touching real filesystem
        self.tmp_dir = Path("tmp_test_pubmed_client")
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        async_client_patcher = patch("api.pubmed_client.httpx.AsyncClient")
        self.mock_async_client = async_client_patcher.start()
        self.addCleanup(async_client_patcher.stop)

        self.mock_client = MagicMock()
        self.mock_async_client.return_value.__aenter__.return_value = self.mock_client
        self.mock_async_client.return_value.__aexit__.return_value = AsyncMock()

        os_getenv_patcher = patch("os.getenv", return_value=str(self.tmp_dir))
        self.mock_os_getenv = os_getenv_patcher.start()
        self.addCleanup(os_getenv_patcher.stop)

        # Reload the module so DATA_DIR is re‑evaluated with the mocked getenv
        importlib.reload(pubmed_client)

        self.config = PipelineConfig()

    async def asyncTearDown(self):
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    async def test_pubmed_search_ids(self):
        mock_response = MockResponse(
            response_dict={"esearchresult": {"idlist": ["100", "200", "300"]}}
        )
        self.mock_client.get = AsyncMock(return_value=mock_response)

        ids = await pubmed_client._pubmed_search_ids(self.config)

        self.assertEqual(ids, ["100", "200", "300"])

        self.mock_client.get.assert_awaited()

        self.assertIn("esearch.fcgi", self.mock_client.get.call_args[0][0])

        called_params = self.mock_client.get.call_args.kwargs.get("params", {})
        self.assertEqual(called_params["retmax"], 30)
        self.assertIn("2020[pdat]", called_params["term"])

    async def test_pubmed_fetch_summaries(self):
        pmids = ["100", "200"]
        response_dict = {
            "result": {
                "100": {"title": "T100", "pubdate": "2020-01-01", "fulljournalname": "J100"},
                "200": {"title": "T200", "pubdate": "2020-02-01", "fulljournalname": "J200"},
            },
        }
        mock_response = MockResponse(response_dict)
        self.mock_client.get = AsyncMock(return_value=mock_response)

        result = await pubmed_client._pubmed_fetch_summaries(pmids)

        self.assertIn("100", result)
        self.assertIn("200", result)
        self.assertEqual(result["100"]["title"], "T100")

    async def test_pubmed_fetch_summaries_empty_pmids(self):
        result = await pubmed_client._pubmed_fetch_summaries([])

        self.assertIsNone(result)

    async def test_pubmed_fetch_abstracts_parses_xml(self):
        pmids = ["100", "200"]

        response_text = """
        <PubmedArticleSet>
            <PubmedArticle>
            <MedlineCitation>
                <PMID>100</PMID>
                <Article>
                <Abstract>
                    <AbstractText>Abstract 100 text.</AbstractText>
                </Abstract>
                </Article>
            </MedlineCitation>
            </PubmedArticle>
            <PubmedArticle>
            <MedlineCitation>
                <PMID>200</PMID>
                <Article>
                <Abstract>
                    <AbstractText>Abstract 200 text.</AbstractText>
                </Abstract>
                </Article>
            </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_response = MockResponse(response_dict=None, response_text=response_text)

        self.mock_client.get = AsyncMock(return_value=mock_response)

        abstracts = await pubmed_client._pubmed_fetch_abstracts(pmids)

        self.assertEqual(abstracts["100"], "Abstract 100 text.")
        self.assertEqual(abstracts["200"], "Abstract 200 text.")

    async def test_pubmed_fetch_abstracts_empty_pmids(self):
        result = await pubmed_client._pubmed_fetch_abstracts([])

        self.assertIsNone(result)

    @patch("api.pubmed_client._pubmed_fetch_summaries", new_callable=AsyncMock)
    @patch("api.pubmed_client._pubmed_fetch_abstracts", new_callable=AsyncMock)
    async def test_fetch_details_concurrent(self, mock_fetch_abstracts, mock_fetch_summaries):
        mock_fetch_summaries.return_value = {"100": {"title": "T100"}}
        mock_fetch_abstracts.return_value = {"100": "Abstract 100"}

        summaries, abstracts = await pubmed_client._fetch_details(["100"])

        self.assertEqual(summaries["100"]["title"], "T100")
        self.assertEqual(abstracts["100"], "Abstract 100")

        mock_fetch_summaries.assert_awaited()
        mock_fetch_abstracts.assert_awaited()

    async def test_fetch_details_empty_pmids(self):
        summaries, abstracts = await pubmed_client._fetch_details([])

        self.assertIsNone(summaries)
        self.assertIsNone(abstracts)

    @patch("api.pubmed_client._fetch_details", new_callable=AsyncMock)
    @patch("api.pubmed_client._pubmed_search_ids", new_callable=AsyncMock)
    async def test_fetch_pubmed_articles_happy_path(self, mock_pubmed_search_ids, mock_fetch_details):
        mock_pubmed_search_ids.return_value = ["100", "200"]
        mock_fetch_details.return_value = (
            {
                "100": {"title": "Title 100", "pubdate": "2020-01-01", "fulljournalname": "J100"},
                "200": {"title": "Title 200", "pubdate": "2020-02-01", "fulljournalname": "J200"},
            },
            {
                "100": "Abstract 100 text.",
                "200": "Abstract 200 text.",
            },
        )

        # with patch.dict("os.environ", {"DATA_DIR": str(self.tmp_dir)}):
        articles = await pubmed_client.fetch_pubmed_articles(self.config)

        self.assertEqual(len(articles), 2)
        self.assertEqual({a.pmid for a in articles}, {"100", "200"})

        cache_path = self.tmp_dir / f"pubmed_articles_{self.config.year}.json"
        self.assertTrue(cache_path.exists())

        data = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["pmid"], "100")

    @patch("api.pubmed_client._fetch_details", new_callable=AsyncMock)
    @patch("api.pubmed_client._pubmed_search_ids", new_callable=AsyncMock)
    async def test_fetch_pubmed_articles_filters_empty_abstracts(self, mock_pubmed_search_ids, mock_fetch_details):
        mock_pubmed_search_ids.return_value = ["100", "200", "300"]
        mock_fetch_details.return_value = (
            {
                "100": {"title": "T100"},
                "200": {"title": "T200"},
                "300": {"title": "T300"},
            },
            {
                "100": "Abstract 100 text.",
                "200": "",            # empty -> should be filtered out
                "300": None,          # None -> coerced to "" then filtered
            },
        )

        articles = await pubmed_client.fetch_pubmed_articles(self.config)
        pmids = [a.pmid for a in articles]
        self.assertEqual(pmids, ["100"])  # only the one with non-empty abstract

        cache_path = self.tmp_dir / f"pubmed_articles_{self.config.year}.json"
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["pmid"], "100")

    @patch("api.pubmed_client._fetch_details", new_callable=AsyncMock)
    @patch("api.pubmed_client._pubmed_search_ids", new_callable=AsyncMock)
    async def test_fetch_pubmed_articles_handles_none_dicts(self, mock_pubmed_search_ids, mock_fetch_details):
        """If helper returns (None, None), code should treat as empty dicts and still write file."""
        mock_pubmed_search_ids.return_value = ["100"]
        mock_fetch_details.return_value = (None, None)  # simulate no data returned

        # Because abstracts dict is None -> treated as {} -> resulting abstract default "" -> filtered out
        articles = await pubmed_client.fetch_pubmed_articles(self.config)
        self.assertEqual(articles, [])

        cache_path = self.tmp_dir / f"pubmed_articles_{self.config.year}.json"
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertEqual(data, [])
