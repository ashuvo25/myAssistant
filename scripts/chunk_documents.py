"""
Recursive Document Chunking
---------------------------
What: Splits cleaned PDF text into retrieval-friendly chunks.
Why: Preserves natural text boundaries while keeping chunks manageable.
Method: Recursive chunking with ~600-token chunks and ~80-token overlap.
Input:  data/cleaned/
Output: data/chunks/chunks.json
"""

import json
from pathlib import Path

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CLEANED_DIR = (
    PROJECT_ROOT / "data" / "cleaned"
)

OUTPUT_DIR = (
    PROJECT_ROOT / "data" / "chunks"
)

OUTPUT_FILE = (
    OUTPUT_DIR / "chunks.json"
)


# =============================================================================
# TOKENIZER
# =============================================================================

# GPT tokenizer is used only for measuring chunk size.
# The final LLM can still be Qwen.
ENCODER = tiktoken.get_encoding(
    "cl100k_base"
)


def token_length(text: str) -> int:
    """Return approximate token count."""

    return len(
        ENCODER.encode(text)
    )


# =============================================================================
# CHUNKER
# =============================================================================

# Focused chunking optimized for small LLM (Qwen 0.5B) attention:
# 250 tokens ≈ 1000 characters (fits 1 targeted section per chunk)
# 40 tokens  ≈ 160 characters overlap

CHUNK_SIZE = 250
CHUNK_OVERLAP = 40

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,

    separators=[
        "\n\n",
        "\n",
        ". ",
        "? ",
        "! ",
        "; ",
        ", ",
        " ",
        "",
    ],

    length_function=token_length,

    keep_separator=True,
)


# =============================================================================
# LOAD DOCUMENT
# =============================================================================

def load_document(path: Path) -> dict:
    """Load one cleaned document."""

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# =============================================================================
# CHUNK ONE DOCUMENT
# =============================================================================

def chunk_document(
    document: dict,
    source_file: Path,
):
    """
    Create chunks while preserving page information.
    """

    chunks = []

    filename = document.get(
        "filename",
        source_file.stem,
    )

    analysis = document.get(
        "analysis",
        {},
    )

    category = (
        source_file
        .relative_to(CLEANED_DIR)
        .parts[0]
        if len(
            source_file.relative_to(
                CLEANED_DIR
            ).parts
        ) > 1
        else "unknown"
    )

    pages = document.get(
        "pages",
        [],
    )

    for page_data in pages:

        page_number = page_data.get(
            "page"
        )

        text = page_data.get(
            "text",
            "",
        ).strip()

        if not text:
            continue

        page_chunks = splitter.split_text(
            text
        )

        for chunk_index, chunk_text in enumerate(
            page_chunks
        ):

            chunk_text = chunk_text.strip()

            if not chunk_text:
                continue

            # Prepend clear document context header to prevent LLM confusion
            if category == "resume" and "Asaduzzaman Shuvo" not in chunk_text[:50]:
                chunk_text = f"[Md. Asaduzzaman Shuvo - Resume]\n{chunk_text}"
            elif category == "projects" and "Project Portfolio" not in chunk_text[:50]:
                chunk_text = f"[Project Portfolio]\n{chunk_text}"

            chunk_id = (
                f"{source_file.stem}"
                f"_p{page_number}"
                f"_c{chunk_index + 1}"
            )

            chunks.append(
                {
                    "chunk_id": chunk_id,

                    "text": chunk_text,

                    "metadata": {
                        "source": "cloudinary",

                        "document": filename,

                        "category": category,

                        "page": page_number,

                        "chunk_index": (
                            chunk_index + 1
                        ),

                        "token_count": (
                            token_length(
                                chunk_text
                            )
                        ),

                        "character_count": (
                            len(chunk_text)
                        ),

                        "source_file": str(
                            source_file.relative_to(
                                PROJECT_ROOT
                            )
                        ),
                    },
                }
            )

    return chunks


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 70)
    print("RECURSIVE DOCUMENT CHUNKING")
    print("=" * 70)

    if not CLEANED_DIR.exists():

        print(
            "\n✗ Cleaned directory not found:"
        )

        print(
            f"  {CLEANED_DIR}"
        )

        print(
            "\nRun clean_and_analyze.py first."
        )

        return 1

    input_files = list(
        CLEANED_DIR.rglob(
            "*.json"
        )
    )

    if not input_files:

        print(
            "\n✗ No cleaned documents found."
        )

        return 1

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_chunks = []

    print(
        f"\nFound {len(input_files)} document(s)."
    )

    # -------------------------------------------------------------------------
    # Process documents
    # -------------------------------------------------------------------------

    for index, source_file in enumerate(
        input_files,
        start=1,
    ):

        print("\n" + "-" * 70)

        print(
            f"[{index}/{len(input_files)}] "
            f"{source_file.name}"
        )

        try:

            document = load_document(
                source_file
            )

            document_chunks = chunk_document(
                document,
                source_file,
            )

            all_chunks.extend(
                document_chunks
            )

            print(
                f"  [OK] Chunks created: {len(document_chunks)}"
            )

        except Exception as error:

            print(
                f"  [ERROR] Failed: {error}"
            )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    token_counts = [
        chunk["metadata"]["token_count"]
        for chunk in all_chunks
    ]

    if token_counts:

        average_tokens = (
            sum(token_counts)
            / len(token_counts)
        )

        smallest = min(
            token_counts
        )

        largest = max(
            token_counts
        )

    else:

        average_tokens = 0
        smallest = 0
        largest = 0

    # -------------------------------------------------------------------------
    # Final dataset
    # -------------------------------------------------------------------------

    result = {
        "configuration": {
            "method": "recursive",

            "target_tokens": 600,

            "overlap_tokens": 80,

            "character_chunk_size": CHUNK_SIZE,

            "character_overlap": CHUNK_OVERLAP,

            "tokenizer": "cl100k_base",

            "note": (
                "Token values are approximate because "
                "Qwen's tokenizer is not used here."
            ),
        },

        "statistics": {
            "documents": len(
                input_files
            ),

            "total_chunks": len(
                all_chunks
            ),

            "average_tokens": round(
                average_tokens,
                2,
            ),

            "smallest_chunk_tokens": (
                smallest
            ),

            "largest_chunk_tokens": (
                largest
            ),
        },

        "chunks": all_chunks,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    print("\n")

    print("=" * 70)
    print("CHUNKING COMPLETE")
    print("=" * 70)

    print(
        f"Documents          : "
        f"{len(input_files)}"
    )

    print(
        f"Total chunks       : "
        f"{len(all_chunks)}"
    )

    print(
        f"Average tokens     : "
        f"{average_tokens:.2f}"
    )

    print(
        f"Smallest chunk     : "
        f"{smallest} tokens"
    )

    print(
        f"Largest chunk      : "
        f"{largest} tokens"
    )

    print(
        f"\nSaved to:"
    )

    print(
        f"  {OUTPUT_FILE}"
    )

    print("=" * 70)

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )