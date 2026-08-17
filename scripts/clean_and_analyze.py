"""
PDF Cleaning & Analysis
-----------------------
What: Cleans extracted PDF text and analyzes document quality.
Why: Prepares reliable, page-aware text before chunking.
Input: data/extracted/
Output: data/cleaned/
"""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from statistics import mean


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXTRACTED_DIR = (
    PROJECT_ROOT / "data" / "extracted"
)

CLEANED_DIR = (
    PROJECT_ROOT / "data" / "cleaned"
)


# =============================================================================
# TEXT CLEANING
# =============================================================================

def normalize_unicode(text: str) -> str:
    """Normalize Unicode characters without removing useful content."""

    return unicodedata.normalize(
        "NFKC",
        text,
    )


def clean_text(text: str) -> str:
    """Perform conservative PDF text cleaning."""

    if not text:
        return ""

    text = normalize_unicode(text)

    # Remove control characters and font symbol artifacts.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Clean corrupt PDF symbol glyphs.
    for char in ["ƒ", "ï", "§", "€", "Ð", "‡", "•", "\x02"]:
        text = text.replace(char, "|")

    # Normalize line endings.
    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    # Remove trailing whitespace.
    text = re.sub(
        r"[ \t]+$",
        "",
        text,
        flags=re.MULTILINE,
    )

    # Collapse multiple spaces/tabs.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Reduce excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


# =============================================================================
# LINE / WORD ANALYSIS
# =============================================================================

def word_count(text: str) -> int:
    """Count whitespace-separated words."""

    if not text:
        return 0

    return len(
        re.findall(
            r"\S+",
            text,
        )
    )


def detect_possible_headings(text: str):
    """
    Detect simple heading-like lines.

    This is intentionally conservative.
    It does not claim that every detected line is
    definitely a heading.
    """

    headings = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        words = line.split()

        if len(words) > 12:
            continue

        # Markdown-style headings.
        if line.startswith("#"):
            headings.append(line)
            continue

        # Common academic section numbering:
        # 1 Introduction
        # 2.1 Methodology
        if re.match(
            r"^\d+(\.\d+)*\.?\s+\S+",
            line,
        ):
            headings.append(line)
            continue

        # Short uppercase headings.
        letters = re.sub(
            r"[^A-Za-z]",
            "",
            line,
        )

        if (
            letters
            and letters.upper() == letters
            and len(letters) >= 4
        ):
            headings.append(line)

    return headings


# =============================================================================
# REPEATED LINE ANALYSIS
# =============================================================================

def find_repeated_lines(
    pages,
    min_occurrences: int = 3,
):
    """
    Find lines repeated across multiple pages.

    Useful for identifying possible headers/footers.
    We report them rather than automatically deleting them.
    """

    counter = Counter()

    for page in pages:

        lines = set(
            line.strip()
            for line in page["text"].splitlines()
            if line.strip()
        )

        for line in lines:

            if len(line) < 3:
                continue

            counter[line] += 1

    repeated = []

    for line, count in counter.items():

        if count >= min_occurrences:

            repeated.append({
                "text": line,
                "occurrences": count,
            })

    repeated.sort(
        key=lambda x: x["occurrences"],
        reverse=True,
    )

    return repeated


# =============================================================================
# PAGE ANALYSIS
# =============================================================================

def analyze_pages(pages):
    """Analyze page-level text quality."""

    page_analysis = []

    for page in pages:

        text = page.get(
            "text",
            "",
        )

        words = word_count(
            text
        )

        characters = len(
            text
        )

        page_analysis.append({
            "page": page.get("page"),
            "characters": characters,
            "words": words,
            "empty": not bool(text.strip()),
            "very_short": words < 10,
        })

    return page_analysis


# =============================================================================
# DOCUMENT PROCESSING
# =============================================================================

def process_document(
    input_file: Path,
):
    """Clean and analyze one extracted document."""

    with open(
        input_file,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    cleaned_pages = []

    for page in data.get(
        "pages",
        [],
    ):

        cleaned = clean_text(
            page.get(
                "text",
                "",
            )
        )

        if not cleaned:
            continue

        cleaned_pages.append({
            "page": page.get("page"),
            "text": cleaned,
            "characters": len(cleaned),
            "words": word_count(cleaned),
        })

    # -------------------------------------------------------------------------
    # Full document text
    # -------------------------------------------------------------------------

    full_text = "\n\n".join(
        page["text"]
        for page in cleaned_pages
    )

    total_words = word_count(
        full_text
    )

    total_characters = len(
        full_text
    )

    # -------------------------------------------------------------------------
    # Page analysis
    # -------------------------------------------------------------------------

    page_analysis = analyze_pages(
        cleaned_pages
    )

    words_per_page = [
        page["words"]
        for page in cleaned_pages
        if page["words"] > 0
    ]

    average_words_per_page = (
        mean(words_per_page)
        if words_per_page
        else 0
    )

    # -------------------------------------------------------------------------
    # Heading detection
    # -------------------------------------------------------------------------

    headings = detect_possible_headings(
        full_text
    )

    # -------------------------------------------------------------------------
    # Repeated lines
    # -------------------------------------------------------------------------

    repeated_lines = find_repeated_lines(
        cleaned_pages
    )

    # -------------------------------------------------------------------------
    # Quality warnings
    # -------------------------------------------------------------------------

    warnings = []

    original_page_count = data.get(
        "page_count",
        len(cleaned_pages),
    )

    pages_with_text = len(
        cleaned_pages
    )

    if pages_with_text < original_page_count:

        warnings.append({
            "type": "empty_pages",
            "message": (
                "Some PDF pages contained "
                "no extractable text."
            ),
        })

    if total_characters == 0:

        warnings.append({
            "type": "no_text",
            "message": (
                "No text was extracted "
                "from this document."
            ),
        })

    if total_words < 50:

        warnings.append({
            "type": "very_little_text",
            "message": (
                "The document contains "
                "very little extractable text."
            ),
        })

    if repeated_lines:

        warnings.append({
            "type": "repeated_lines",
            "message": (
                "Repeated lines were detected. "
                "Some may be headers or footers."
            ),
        })

    # -------------------------------------------------------------------------
    # Result
    # -------------------------------------------------------------------------

    result = {
        "source": "cloudinary",

        "filename": data.get(
            "filename",
            input_file.stem,
        ),

        "original_file_path": data.get(
            "file_path"
        ),

        "metadata": data.get(
            "metadata",
            {},
        ),

        "analysis": {
            "original_page_count": original_page_count,

            "pages_with_text": pages_with_text,

            "total_characters": total_characters,

            "total_words": total_words,

            "average_words_per_page": round(
                average_words_per_page,
                2,
            ),

            "heading_count": len(
                headings
            ),

            "possible_headings": headings,

            "repeated_lines": repeated_lines,

            "warnings": warnings,
        },

        "pages": cleaned_pages,
    }

    return result


# =============================================================================
# SAVE RESULT
# =============================================================================

def save_result(
    result,
    input_file: Path,
):
    """Save cleaned document."""

    relative_path = (
        input_file.relative_to(
            EXTRACTED_DIR
        )
    )

    output_dir = (
        CLEANED_DIR
        / relative_path.parent
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / input_file.name
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
    print("PDF CLEANING & ANALYSIS")
    print("=" * 70)

    if not EXTRACTED_DIR.exists():

        print(
            "\n✗ Extracted directory not found:"
        )

        print(
            f"  {EXTRACTED_DIR}"
        )

        print(
            "\nRun extract_pdf_text.py first."
        )

        return 1

    input_files = list(
        EXTRACTED_DIR.rglob(
            "*.json"
        )
    )

    if not input_files:

        print(
            "\n✗ No extracted JSON files found."
        )

        return 1

    CLEANED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"\nFound {len(input_files)} document(s)."
    )

    successful = 0
    failed = 0

    for index, input_file in enumerate(
        input_files,
        start=1,
    ):

        print("\n" + "-" * 70)

        print(
            f"[{index}/{len(input_files)}] "
            f"{input_file.name}"
        )

        try:

            result = process_document(
                input_file
            )

            output_file = save_result(
                result,
                input_file,
            )

            analysis = result[
                "analysis"
            ]

            print(
                f"  [OK] Pages: {analysis['original_page_count']} | Words: {analysis['total_words']:,} | Chars: {analysis['total_characters']:,}"
            )

            print(
                f"  [OK] Headings: {analysis['heading_count']}"
            )

            print(
                f"  [OK] Saved: {output_file}"
            )

            successful += 1

        except Exception as error:

            print(
                f"  [ERROR] Processing failed: {error}"
            )

            failed += 1

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("\n")

    print("=" * 70)
    print("CLEANING SUMMARY")
    print("=" * 70)

    print(
        f"[OK] Successful : {successful}"
    )

    print(
        f"[ERROR] Failed     : {failed}"
    )

    print(
        "\n[OK] Cleaning and analysis completed."
    )

    print(
        f"✗ Failed     : {failed}"
    )

    print(
        "\nOutput:"
    )

    print(
        f"  {CLEANED_DIR}"
    )

    print("=" * 70)

    if failed:
        return 1

    print(
        "\n✓ Cleaning and analysis completed."
    )

    print(
        "\nNext step:"
    )

    print(
        "  Inspect the cleaned JSON before chunking."
    )

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )