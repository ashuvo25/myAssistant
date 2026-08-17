"""
PDF Text Extraction
-------------------
What: Extracts text from downloaded portfolio PDFs.
Why: Converts PDFs into structured page-level text for later RAG processing.
Uses: PyMuPDF (fitz).
"""

import json
import re
from pathlib import Path

import fitz  # PyMuPDF


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DOCUMENTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "documents"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "extracted"
)


# =============================================================================
# TEXT CLEANING
# =============================================================================

def clean_text(text: str) -> str:
    """
    Perform conservative text cleaning.

    We preserve the actual document content while
    removing unnecessary whitespace.
    """

    if not text:
        return ""

    # Normalize line endings.
    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    # Remove excessive spaces.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


# =============================================================================
# EXTRACT ONE PDF
# =============================================================================

def extract_pdf(
    pdf_path: Path,
) -> dict:
    """
    Extract page-level text from one PDF.
    """

    document = fitz.open(
        pdf_path
    )

    pages = []

    total_characters = 0

    for page_number, page in enumerate(
        document,
        start=1,
    ):

        raw_text = page.get_text(
            "text"
        )

        text = clean_text(
            raw_text
        )

        # Skip completely empty pages.
        if not text:
            continue

        character_count = len(text)

        total_characters += character_count

        pages.append(
            {
                "page": page_number,
                "text": text,
                "characters": character_count,
            }
        )

    metadata = document.metadata

    result = {
        "source": "cloudinary",

        "filename": pdf_path.name,

        "file_path": str(
            pdf_path.relative_to(
                PROJECT_ROOT
            )
        ),

        "page_count": len(document),

        "pages_with_text": len(pages),

        "total_characters": total_characters,

        "metadata": {
            "title": metadata.get(
                "title"
            ),
            "author": metadata.get(
                "author"
            ),
            "subject": metadata.get(
                "subject"
            ),
            "keywords": metadata.get(
                "keywords"
            ),
        },

        "pages": pages,
    }

    document.close()

    return result


# =============================================================================
# SAVE JSON
# =============================================================================

def save_extracted_text(
    result: dict,
    pdf_path: Path,
):
    """Save extracted PDF text as JSON."""

    relative_path = pdf_path.relative_to(
        DOCUMENTS_DIR
    )

    output_folder = (
        OUTPUT_DIR
        / relative_path.parent
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_folder
        / f"{pdf_path.stem}.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_file


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 70)
    print("PDF TEXT EXTRACTION")
    print("=" * 70)

    if not DOCUMENTS_DIR.exists():

        print(
            "\n✗ Documents directory does not exist:"
        )

        print(
            f"  {DOCUMENTS_DIR}"
        )

        print(
            "\nRun download_documents.py first."
        )

        return 1

    pdf_files = list(
        DOCUMENTS_DIR.rglob(
            "*.pdf"
        )
    )

    if not pdf_files:

        print(
            "\n✗ No PDF files found."
        )

        return 1

    print(
        f"\nFound {len(pdf_files)} PDF(s)."
    )

    successful = 0
    failed = 0

    total_pages = 0
    total_characters = 0

    for index, pdf_path in enumerate(
        pdf_files,
        start=1,
    ):

        print("\n" + "-" * 70)

        print(
            f"[{index}/{len(pdf_files)}] "
            f"{pdf_path.name}"
        )

        try:

            result = extract_pdf(
                pdf_path
            )

            output_file = save_extracted_text(
                result,
                pdf_path,
            )

            total_pages += result[
                "pages_with_text"
            ]

            total_characters += result[
                "total_characters"
            ]

            print(
                f"✓ Pages: "
                f"{result['page_count']}"
            )

            print(
                f"✓ Pages with text: "
                f"{result['pages_with_text']}"
            )

            print(
                f"✓ Characters: "
                f"{result['total_characters']:,}"
            )

            print(
                f"✓ Saved: "
                f"{output_file.relative_to(PROJECT_ROOT)}"
            )

            successful += 1

        except Exception as error:

            print(
                f"✗ Extraction failed: {error}"
            )

            failed += 1

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("\n")

    print("=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)

    print(
        f"✓ Successful PDFs : {successful}"
    )

    print(
        f"✗ Failed PDFs     : {failed}"
    )

    print(
        f"📄 Pages extracted : {total_pages}"
    )

    print(
        f"📝 Characters       : "
        f"{total_characters:,}"
    )

    print(
        "\nOutput directory:"
    )

    print(
        f"  {OUTPUT_DIR}"
    )

    print("=" * 70)

    if failed > 0:
        return 1

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )