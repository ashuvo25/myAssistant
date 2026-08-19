"""
Portfolio RAG Retriever
-----------------------
What: Retrieves the most relevant document chunks from ChromaDB.
Why: Converts a user question into an embedding and finds relevant
     portfolio/research content before sending it to Qwen.

Input:
    User query

Output:
    Top-K relevant chunks with metadata and similarity information
"""

import gc
import re
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
import chromadb.utils.embedding_functions as ef


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CHROMA_DIR = (
    PROJECT_ROOT
    / "data"
    / "chroma"
)

COLLECTION_NAME = "portfolio_documents"

MODEL_NAME = "all-MiniLM-L6-v2"

DEFAULT_TOP_K = 5

MAX_DISTANCE = 1.8

RESEARCH_QUERY_TERMS = (
    "research",
    "paper",
    "papers",
    "publication",
    "publications",
    "published",
)


try:
    torch.set_num_threads(1)
except Exception:
    pass


def is_research_query(query: str) -> bool:
    """Return whether a query should search publication chunks first."""

    lowered = query.lower()
    return any(
        re.search(rf"\b{re.escape(term)}\b", lowered)
        for term in RESEARCH_QUERY_TERMS
    )


# =============================================================================
# RETRIEVER
# =============================================================================

class PortfolioRetriever:

    def __init__(
        self,
        top_k: int = DEFAULT_TOP_K,
    ):

        self.top_k = top_k

        print(
            f"-> Loading ONNX embedding model: "
            f"{MODEL_NAME}"
        )

        gc.collect()

        self.embedding_fn = ef.ONNXMiniLM_L6_V2()

        gc.collect()

        print(
            "[OK] ONNX Embedding model loaded"
        )

        # ---------------------------------------------------------------------
        # Connect to persistent ChromaDB
        # ---------------------------------------------------------------------

        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        self.collection = (
            self.client.get_collection(
                name=COLLECTION_NAME
            )
        )

        print(
            f"[OK] ChromaDB collection loaded: "
            f"{COLLECTION_NAME}"
        )

        print(
            f"[OK] Stored vectors: "
            f"{self.collection.count()}"
        )

        print(
            "[OK] ChromaDB retriever ready"
        )

    # =========================================================================
    # RETRIEVE
    # =========================================================================

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """
        Retrieve the most relevant chunks for a query using ONNX embeddings.
        """

        if not query.strip():
            return []

        if top_k is None:
            top_k = self.top_k

        # ---------------------------------------------------------------------
        # Convert query into embedding via ONNX
        # ---------------------------------------------------------------------

        query_embedding = self.embedding_fn([query])

        # ---------------------------------------------------------------------
        # Stage 1: Search the category that matches the user's intent.
        # Publication questions must not be restricted to resume/project
        # chunks, because publication PDFs intentionally have low priority.
        # ---------------------------------------------------------------------

        try:
            preferred_filter = (
                {"category": "publications"}
                if is_research_query(query)
                else {"priority": "high"}
            )

            high_results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                where=preferred_filter,
                include=[
                    "documents",
                    "metadatas",
                    "distances",
                ],
            )
            high_docs = high_results.get("documents", [[]])[0]
        except Exception:
            high_docs = []
            high_results = None

        # ---------------------------------------------------------------------
        # Stage 2: Use high-priority results if found, else search all chunks
        # ---------------------------------------------------------------------

        if high_docs and high_results:
            results = high_results
        else:
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                include=[
                    "documents",
                    "metadatas",
                    "distances",
                ],
            )

        # ---------------------------------------------------------------------
        # Convert Chroma result into clean structure
        # ---------------------------------------------------------------------

        retrieved = []

        documents = results.get(
            "documents",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        for index, text in enumerate(
            documents
        ):

            metadata = metadatas[index]

            distance = distances[index]

            retrieved.append(
                {
                    "rank": index + 1,

                    "text": text,

                    "distance": distance,

                    "metadata": metadata,
                }
            )

        # Filter out low-relevance chunks (distance > threshold)
        retrieved = [
            r for r in retrieved
            if r["distance"] <= MAX_DISTANCE
        ]

        # Re-number ranks after filtering
        for i, r in enumerate(retrieved):
            r["rank"] = i + 1

        return retrieved

    # =========================================================================
    # CONTEXT BUILDER
    # =========================================================================

    def build_context(
        self,
        query: str,
        top_k: int | None = None,
    ):
        """
        Build a clean context string that can later
        be passed directly to Qwen.
        """

        results = self.retrieve(
            query=query,
            top_k=top_k,
        )

        if not results:

            return ""

        context_parts = []

        for result in results:

            metadata = result[
                "metadata"
            ]

            document = metadata.get(
                "document",
                "Unknown document",
            )

            page = metadata.get(
                "page",
                "Unknown",
            )

            context_parts.append(
                f"""
[Source {result['rank']}]
Document: {document}
Page: {page}

{result['text']}
""".strip()
            )

        return "\n\n".join(
            context_parts
        )


# =============================================================================
# DISPLAY RESULTS
# =============================================================================

def print_results(
    query: str,
    results,
):
    """Display retrieval results."""

    print("\n")
    print("=" * 70)
    print("RETRIEVAL RESULTS")
    print("=" * 70)

    print(
        f"\nQuery:\n{query}"
    )

    if not results:

        print(
            "\n[ERROR] No results found."
        )

        return

    for result in results:

        metadata = result[
            "metadata"
        ]

        print(
            "\n" + "-" * 70
        )

        print(
            f"Rank     : "
            f"{result['rank']}"
        )

        print(
            f"Distance : "
            f"{result['distance']:.4f}"
        )

        print(
            f"Document : "
            f"{metadata.get('document')}"
        )

        print(
            f"Category : "
            f"{metadata.get('category')}"
        )

        print(
            f"Page     : "
            f"{metadata.get('page')}"
        )

        print(
            f"Chunk    : "
            f"{metadata.get('chunk_index')}"
        )

        print(
            "\nText:"
        )

        print(
            result["text"][:700]
        )

    print(
        "\n" + "=" * 70
    )


# =============================================================================
# INTERACTIVE TEST MODE
# =============================================================================

def main():

    print("=" * 70)
    print("PORTFOLIO RAG RETRIEVER")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Initialize retriever
    # -------------------------------------------------------------------------

    try:

        retriever = PortfolioRetriever(
            top_k=5
        )

    except Exception as error:

        print(
            f"\n[ERROR] Failed to initialize retriever:"
        )

        print(
            f"  {error}"
        )

        print(
            "\nMake sure create_embeddings.py "
            "has been executed successfully."
        )

        return 1

    # -------------------------------------------------------------------------
    # Test queries
    # -------------------------------------------------------------------------

    test_queries = [

        "What research papers have I worked on?",

        "What is my mosquito detection research about?",

        "What AI projects have I built?",

        "What technologies do I use?",

    ]

    print(
        "\n-> Running test queries..."
    )

    for query in test_queries:

        results = retriever.retrieve(
            query,
            top_k=5,
        )

        print_results(
            query,
            results,
        )

    # -------------------------------------------------------------------------
    # Interactive mode
    # -------------------------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("INTERACTIVE RETRIEVAL")
    print("=" * 70)

    print(
        "\nType a question to test retrieval."
    )

    print(
        "Type 'exit' to stop."
    )

    while True:

        try:

            query = input(
                "\nQuestion: "
            ).strip()

        except KeyboardInterrupt:

            print(
                "\n\nExiting..."
            )

            break

        if query.lower() in {
            "exit",
            "quit",
        }:

            break

        if not query:

            continue

        results = retriever.retrieve(
            query,
            top_k=5,
        )

        print_results(
            query,
            results,
        )

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )
