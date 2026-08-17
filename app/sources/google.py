"""
Google Data Source
------------------
What: Fetches public Google Sheets and Google Docs data.
Why: Provides live portfolio information for the chatbot.
Uses: Public Google export endpoints.
"""

import csv
import io
import os
import re
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


load_dotenv()


class GoogleSource:
    """Fetch public Google Sheets and Google Docs data."""

    SHEET_URL = (
        "https://docs.google.com/spreadsheets/d/{}/export"
    )

    DOC_URL = (
        "https://docs.google.com/document/d/{}/export"
    )

    def __init__(self):

        self.sheets = {
            "projects": os.getenv(
                "GOOGLE_PROJECTS_SHEET_ID"
            ),

            "social": os.getenv(
                "GOOGLE_SOCIAL_SHEET_ID"
            ),

            "work_updates": os.getenv(
                "GOOGLE_WORK_UPDATES_SHEET_ID"
            ),

            "research_updates": os.getenv(
                "GOOGLE_RESEARCH_UPDATES_SHEET_ID"
            ),
        }

        self.my_update_doc_id = os.getenv(
            "GOOGLE_MY_UPDATE_DOC_ID"
        )

        missing_sheets = [
            name
            for name, sheet_id in self.sheets.items()
            if not sheet_id
        ]

        if missing_sheets:
            raise ValueError(
                "Missing Google Sheet IDs: "
                + ", ".join(missing_sheets)
            )

        if not self.my_update_doc_id:
            raise ValueError(
                "GOOGLE_MY_UPDATE_DOC_ID "
                "is missing from .env"
            )

    # ========================================================================
    # GOOGLE SHEETS
    # ========================================================================

    def fetch_sheet(
        self,
        sheet_id: str,
        gid: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch a public Google Sheet as CSV
        and convert rows into dictionaries.
        """

        url = self.SHEET_URL.format(
            sheet_id
        )

        params = {
            "format": "csv",
        }

        if gid:
            params["gid"] = gid

        response = requests.get(
            url,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        text = response.text

        if not text.strip():
            return []

        reader = csv.DictReader(
            io.StringIO(text)
        )

        rows = []

        for row in reader:

            clean_row = {}

            for key, value in row.items():

                if key is None:
                    continue

                clean_key = str(key).strip()

                if isinstance(value, str):
                    value = value.strip()

                clean_row[clean_key] = value

            rows.append(clean_row)

        return rows

    # ========================================================================
    # GOOGLE DOCS
    # ========================================================================

    def fetch_document(
        self,
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Fetch a public Google Doc as HTML
        and extract readable text.
        """

        url = self.DOC_URL.format(
            document_id
        )

        params = {
            "format": "html",
        }

        response = requests.get(
            url,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        html = response.text

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        # Remove unnecessary HTML elements.
        for element in soup(
            ["script", "style", "noscript"]
        ):
            element.decompose()

        text = soup.get_text(
            separator="\n"
        )

        # Clean excessive whitespace.
        lines = []

        for line in text.splitlines():

            line = re.sub(
                r"\s+",
                " ",
                line
            ).strip()

            if line:
                lines.append(line)

        clean_text = "\n".join(lines)

        return {
            "document_id": document_id,
            "text": clean_text,
        }

    # ========================================================================
    # INDIVIDUAL SOURCES
    # ========================================================================

    def get_projects(self):
        """Fetch projects, CP, research and awards."""

        return self.fetch_sheet(
            self.sheets["projects"]
        )

    def get_social(self):
        """Fetch social links and statistics."""

        return self.fetch_sheet(
            self.sheets["social"]
        )

    def get_work_updates(self):
        """Fetch work updates."""

        return self.fetch_sheet(
            self.sheets["work_updates"]
        )

    def get_research_updates(self):
        """Fetch research updates."""

        return self.fetch_sheet(
            self.sheets["research_updates"]
        )

    def get_my_update(self):
        """Fetch the personal Google Doc."""

        return self.fetch_document(
            self.my_update_doc_id
        )

    # ========================================================================
    # ALL GOOGLE DATA
    # ========================================================================

    def get_all(self):
        """Fetch all Google sources."""

        return {
            "source": "google",

            "projects": self.get_projects(),

            "social": self.get_social(),

            "work_updates": self.get_work_updates(),

            "research_updates": (
                self.get_research_updates()
            ),

            "my_update": self.get_my_update(),
        }


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":

    google = GoogleSource()

    data = google.get_all()

    print("\n" + "=" * 70)
    print("GOOGLE SOURCES FETCH TEST")
    print("=" * 70)

    # ------------------------------------------------------------------------
    # Sheets
    # ------------------------------------------------------------------------

    for name in [
        "projects",
        "social",
        "work_updates",
        "research_updates",
    ]:

        rows = data[name]

        print(
            f"\n✓ {name}: "
            f"{len(rows)} rows"
        )

        if rows:

            print(
                "  Columns:"
            )

            print(
                f"  {list(rows[0].keys())}"
            )

            print(
                "  First row:"
            )

            print(
                f"  {rows[0]}"
            )

    # ------------------------------------------------------------------------
    # Google Doc
    # ------------------------------------------------------------------------

    document = data["my_update"]

    print(
        "\n✓ my_update document fetched"
    )

    print(
        f"  Document ID: "
        f"{document['document_id']}"
    )

    print(
        f"  Characters: "
        f"{len(document['text'])}"
    )

    print(
        "\n  Preview:"
    )

    print(
        document["text"][:500]
    )

    print("\n" + "=" * 70)
    print("GOOGLE FETCH COMPLETE")
    print("=" * 70)