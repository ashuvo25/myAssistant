"""Regression tests for portfolio research-paper retrieval."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from context_processor import process_google  # noqa: E402
from query_router import route_query  # noqa: E402
from retriever import is_research_query  # noqa: E402


class ResearchRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        google_path = PROJECT_ROOT / "data" / "raw" / "google" / "data.json"
        self.google_data = json.loads(google_path.read_text(encoding="utf-8"))

    def test_research_question_routes_to_google_and_chroma(self) -> None:
        result = route_query("What research papers has he worked on?")
        self.assertEqual(result["route"], "hybrid")
        self.assertIn("google", result["sources"])
        self.assertIn("chroma", result["sources"])

    def test_research_context_contains_every_current_paper(self) -> None:
        context = process_google(
            self.google_data,
            "What research papers has he worked on?",
        )

        research_items = self.google_data["research_updates"]
        for item in research_items:
            self.assertIn(item["title"], context)

        self.assertNotIn("Featured AI Projects", context)
        self.assertNotIn("...[truncated]", context)

    def test_publication_queries_prefer_publication_chunks(self) -> None:
        self.assertTrue(is_research_query("Tell me about his publications"))
        self.assertTrue(is_research_query("Which papers has Shuvo published?"))
        self.assertFalse(is_research_query("What software projects has he built?"))


if __name__ == "__main__":
    unittest.main()
