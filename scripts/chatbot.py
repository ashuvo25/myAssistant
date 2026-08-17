"""
Personal AI Portfolio Chatbot
-----------------------------

Complete pipeline:

User
 ↓
Query Router
 ↓
Source Manager
 ↓
GitHub / LeetCode / Google / ChromaDB
 ↓
Context Processor
 ↓
GPT-4o-mini
 ↓
Answer
"""

from source_manager import SourceManager
from context_processor import process_context
from llm_client import generate_answer


# =============================================================================
# DISPLAY
# =============================================================================

def print_header():

    print("=" * 70)
    print("PERSONAL AI PORTFOLIO CHATBOT")
    print("=" * 70)

    print()
    print("Ask anything about Shuvo.")
    print("Type 'exit' to stop.")
    print()


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    # -------------------------------------------------------------------------
    # Create source manager ONCE.
    #
    # Previously this was being recreated for every question, which caused
    # BGE-M3 and ChromaDB to reload repeatedly.
    # -------------------------------------------------------------------------

    try:

        source_manager = SourceManager()

    except Exception as error:

        print()
        print("ERROR INITIALIZING SOURCE MANAGER:")
        print(error)
        return

    print()

    # =========================================================================
    # CHAT LOOP
    # =========================================================================

    while True:

        try:

            question = input(
                "Question: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError,
        ):

            print("\nGoodbye!")
            break

        if not question:

            continue

        if question.lower() in {
            "exit",
            "quit",
        }:

            print("\nGoodbye!")
            break

        print()
        print("-" * 70)

        try:

            # ================================================================
            # STEP 1 — ROUTE + FETCH
            # ================================================================

            source_response = (
                source_manager.execute_route(
                    question
                )
            )

            print(
                f"Route   : "
                f"{source_response.get('route')}"
            )

            print(
                f"Sources : "
                f"{', '.join(source_response.get('sources', []))}"
            )

            print(
                f"Reason  : "
                f"{source_response.get('reason', '')}"
            )

            # ================================================================
            # STEP 2 — PROCESS CONTEXT
            # ================================================================

            context = process_context(
                source_response
            )

            # ================================================================
            # DEBUG
            # ================================================================

            print()
            print(
                f"Context size: {len(context)} characters"
            )

            # ================================================================
            # STEP 3 — QWEN
            # ================================================================

            answer = generate_answer(
                question=question,
                context=context,
            )

            # ================================================================
            # STEP 4 — ANSWER
            # ================================================================

            print()
            print("Answer:")
            print(answer)

        except Exception as error:

            print()
            print("ERROR:")
            print(error)

        print()
        print("-" * 70)
        print()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    main()