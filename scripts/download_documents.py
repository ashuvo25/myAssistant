"""
Cloudinary PDF Downloader
-------------------------
What: Downloads portfolio PDFs from Cloudinary.
Why: Creates local copies for text extraction and RAG processing.
Input: data/raw/cloudinary/documents.json
Output: data/documents/
"""

import json
import sys
from pathlib import Path

import requests


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cloudinary"
    / "documents.json"
)

DOCUMENTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "documents"
)


# =============================================================================
# HELPERS
# =============================================================================

def load_cloudinary_data():
    """Load Cloudinary document metadata."""

    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Cloudinary metadata not found:\n{RAW_FILE}\n\n"
            "Run sync_sources.py first."
        )

    with open(
        RAW_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def safe_filename(name: str) -> str:
    """Create a safe filename for Windows/Linux."""

    invalid_chars = '<>:"/\\|?*'

    for char in invalid_chars:
        name = name.replace(char, "_")

    return name.strip()


def download_file(
    url: str,
    output_path: Path,
):
    """Download a file from Cloudinary."""

    response = requests.get(
        url,
        stream=True,
        timeout=60,
    )

    response.raise_for_status()

    with open(
        output_path,
        "wb",
    ) as file:

        for chunk in response.iter_content(
            chunk_size=8192
        ):

            if chunk:
                file.write(chunk)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 70)
    print("CLOUDINARY PDF DOWNLOADER")
    print("=" * 70)

    DOCUMENTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = load_cloudinary_data()

    documents = data.get(
        "documents",
        [],
    )

    if not documents:

        print(
            "\n! No Cloudinary documents found."
        )

        return 1

    print(
        f"\nFound {len(documents)} Cloudinary document(s)."
    )

    downloaded = 0
    skipped = 0
    failed = 0

    for index, document in enumerate(
        documents,
        start=1,
    ):

        url = document.get("url")

        public_id = document.get(
            "public_id",
            f"document_{index}",
        )

        category = document.get(
            "category",
            "other",
        )

        file_format = document.get(
            "format",
            "pdf",
        )

        # Only process PDFs.
        if file_format.lower() != "pdf":

            print(
                f"\n[{index}] SKIP"
                f"\n  Public ID: {public_id}"
                f"\n  Format: {file_format}"
            )

            skipped += 1
            continue

        if not url:

            print(
                f"\n[{index}] FAILED"
                f"\n  No download URL found."
            )

            failed += 1
            continue

        # ---------------------------------------------------------------------
        # Create category directory
        # ---------------------------------------------------------------------

        category_dir = (
            DOCUMENTS_DIR / safe_filename(category)
        )

        category_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ---------------------------------------------------------------------
        # Create filename
        # ---------------------------------------------------------------------

        filename = safe_filename(
            public_id.split("/")[-1]
        )

        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        output_path = (
            category_dir / filename
        )

        print(
            f"\n[{index}] Downloading"
        )

        print(
            f"  Category : {category}"
        )

        print(
            f"  File     : {filename}"
        )

        print(
            f"  URL      : {url}"
        )

        # ---------------------------------------------------------------------
        # Skip if already downloaded
        # ---------------------------------------------------------------------

        if output_path.exists():

            print(
                "  ✓ Already exists — skipped"
            )

            skipped += 1
            continue

        # ---------------------------------------------------------------------
        # Download
        # ---------------------------------------------------------------------

        try:

            download_file(
                url=url,
                output_path=output_path,
            )

            file_size = (
                output_path.stat().st_size
            )

            print(
                f"  ✓ Downloaded"
                f" ({file_size:,} bytes)"
            )

            downloaded += 1

        except Exception as error:

            print(
                f"  ✗ Download failed: {error}"
            )

            # Remove incomplete file.
            if output_path.exists():
                output_path.unlink()

            failed += 1

    # =========================================================================
    # FINAL STATUS
    # =========================================================================

    print("\n")
    print("=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)

    print(
        f"✓ Downloaded : {downloaded}"
    )

    print(
        f"→ Skipped    : {skipped}"
    )

    print(
        f"✗ Failed     : {failed}"
    )

    print("-" * 70)

    print(
        f"Documents directory:\n"
        f"  {DOCUMENTS_DIR}"
    )

    print("=" * 70)

    if failed > 0:
        return 1

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(main())