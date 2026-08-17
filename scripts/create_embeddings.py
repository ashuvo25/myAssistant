"""
Embedding + ChromaDB
--------------------
What: Converts document chunks into vector embeddings and stores them.
Why: Enables semantic retrieval for the portfolio RAG chatbot.
Input:  data/chunks/chunks.json
Output: data/chroma/
Model: BAAI/bge-m3
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CHUNKS_FILE = (
    PROJECT_ROOT
    / "data"
    / "chunks"
    / "chunks.json"
)

CHROMA_DIR = (
    PROJECT_ROOT
    / "data"
    / "chroma"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL_NAME = "all-MiniLM-L6-v2"

COLLECTION_NAME = "portfolio_documents"

BATCH_SIZE = 16


# =============================================================================
# LOAD CHUNKS
# =============================================================================

def load_chunks():

    if not CHUNKS_FILE.exists():

        raise FileNotFoundError(
            f"Chunks file not found:\n{CHUNKS_FILE}\n\n"
            "Run chunk_documents.py first."
        )

    with open(
        CHUNKS_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    chunks = data.get(
        "chunks",
        []
    )

    if not chunks:

        raise ValueError(
            "No chunks found in chunks.json."
        )

    return chunks


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 70)
    print("EMBEDDING + CHROMADB INDEXING")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Load chunks
    # -------------------------------------------------------------------------

    chunks = load_chunks()

    print(
        f"\n[OK] Loaded chunks: {len(chunks)}"
    )

    # -------------------------------------------------------------------------
    # Load embedding model
    # -------------------------------------------------------------------------

    print(
        f"\n-> Loading embedding model:"
    )

    print(
        f"  {MODEL_NAME}"
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    print(
        "[OK] Embedding model loaded"
    )

    # -------------------------------------------------------------------------
    # Initialize ChromaDB
    # -------------------------------------------------------------------------

    CHROMA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    # -------------------------------------------------------------------------
    # Create / reset collection
    # -------------------------------------------------------------------------

    try:

        client.delete_collection(
            COLLECTION_NAME
        )

        print(
            f"\n[OK] Existing collection "
            f"'{COLLECTION_NAME}' removed"
        )

    except Exception:

        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,

        metadata={
            "description": (
                "Portfolio documents "
                "for personal AI chatbot"
            ),

            "embedding_model": MODEL_NAME,
        },
    )

    print(
        f"[OK] ChromaDB collection created:"
        f" {COLLECTION_NAME}"
    )

    # -------------------------------------------------------------------------
    # Prepare data with priority metadata
    # -------------------------------------------------------------------------

    # Documents in the publications folder are research paper bodies.
    # They contain methodology, references, equations — NOT portfolio info.
    # We tag them "low" priority so the retriever prefers resume/project
    # chunks that actually describe Shuvo's work.

    HIGH_PRIORITY_CATEGORIES = {
        "resume",
        "projects",
    }

    ids = []

    texts = []

    metadatas = []

    priority_counts = {
        "high": 0,
        "low": 0,
    }

    for chunk in chunks:

        chunk_id = chunk[
            "chunk_id"
        ]

        text = chunk[
            "text"
        ]

        metadata = chunk.get(
            "metadata",
            {},
        )

        ids.append(
            chunk_id
        )

        texts.append(
            text
        )

        # Chroma metadata values must be
        # simple scalar types.
        clean_metadata = {}

        for key, value in metadata.items():

            if value is None:
                continue

            if isinstance(
                value,
                (str, int, float, bool),
            ):

                clean_metadata[key] = value

            else:

                clean_metadata[key] = str(
                    value
                )

        # Assign priority based on category.
        category = clean_metadata.get(
            "category",
            "",
        ).lower()

        if category in HIGH_PRIORITY_CATEGORIES:
            clean_metadata["priority"] = "high"
            priority_counts["high"] += 1
        else:
            clean_metadata["priority"] = "low"
            priority_counts["low"] += 1

        metadatas.append(
            clean_metadata
        )

    print(
        f"\n[OK] Priority tagging:"
    )
    print(
        f"  High (resume/projects): "
        f"{priority_counts['high']}"
    )
    print(
        f"  Low  (publications):    "
        f"{priority_counts['low']}"
    )

    # -------------------------------------------------------------------------
    # Generate embeddings + store
    # -------------------------------------------------------------------------

    total = len(texts)

    print(
        f"\n-> Creating embeddings for "
        f"{total} chunks..."
    )

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):

        end = min(
            start + BATCH_SIZE,
            total,
        )

        batch_texts = texts[
            start:end
        ]

        batch_ids = ids[
            start:end
        ]

        batch_metadata = metadatas[
            start:end
        ]

        # Generate embeddings.
        embeddings = model.encode(
            batch_texts,

            batch_size=BATCH_SIZE,

            show_progress_bar=False,

            normalize_embeddings=True,
        )

        embeddings = embeddings.tolist()

        # Store in ChromaDB.
        collection.add(

            ids=batch_ids,

            documents=batch_texts,

            embeddings=embeddings,

            metadatas=batch_metadata,
        )

        print(
            f"  [OK] {end}/{total} chunks indexed"
        )

    # -------------------------------------------------------------------------
    # Verify
    # -------------------------------------------------------------------------

    count = collection.count()

    print("\n")

    print("=" * 70)
    print("EMBEDDING + CHROMADB COMPLETE")
    print("=" * 70)

    print(
        f"Embedding model : {MODEL_NAME}"
    )

    print(
        f"Input chunks    : {total}"
    )

    print(
        f"Stored vectors  : {count}"
    )

    print(
        f"ChromaDB path   : {CHROMA_DIR}"
    )

    # -------------------------------------------------------------------------
    # Test retrieval
    # -------------------------------------------------------------------------

    test_query = (
        "What research projects and "
        "papers have I worked on?"
    )

    print(
        "\n-> Testing semantic retrieval..."
    )

    query_embedding = model.encode(
        [test_query],
        normalize_embeddings=True,
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,

        n_results=3,
    )

    print(
        f"\nQuery: {test_query}"
    )

    for index, document in enumerate(
        results["documents"][0],
        start=1,
    ):

        metadata = results[
            "metadatas"
        ][0][index - 1]

        distance = results[
            "distances"
        ][0][index - 1]

        print(
            f"\n[{index}]"
        )

        print(
            f"Document: "
            f"{metadata.get('document')}"
        )

        print(
            f"Page: "
            f"{metadata.get('page')}"
        )

        print(
            f"Distance: "
            f"{distance:.4f}"
        )

        safe_text = document[:300].encode("ascii", "replace").decode("ascii")
        print(
            f"Text: "
            f"{safe_text}..."
        )

    print("\n" + "=" * 70)

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )