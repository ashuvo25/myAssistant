"""
Portfolio Query Router
----------------------

Routes user questions to the appropriate information sources.

Sources:
    - chroma    -> static portfolio / resume / projects / publications
    - github    -> GitHub repositories and activity
    - leetcode  -> LeetCode statistics
    - google    -> Google Sheets / Docs data
    - conversation -> casual conversation
"""

import re
from typing import Dict, List


# =============================================================================
# SOURCE DETECTION
# =============================================================================

def contains_any(text: str, keywords: List[str]) -> bool:
    text = text.lower()

    return any(
        keyword.lower() in text
        for keyword in keywords
    )


# =============================================================================
# QUERY ROUTER
# =============================================================================

def route_query(query: str) -> Dict:
    """
    Decide which sources should answer the user's question.
    """

    original_query = query.strip()
    q = original_query.lower()

    # -------------------------------------------------------------------------
    # EMPTY QUERY
    # -------------------------------------------------------------------------

    if not original_query:
        return {
            "route": "unknown",
            "sources": [],
            "reason": "Empty query."
        }

    # -------------------------------------------------------------------------
    # CASUAL CONVERSATION
    # -------------------------------------------------------------------------

    conversation_patterns = [
        "hi",
        "hello",
        "hey",
        "how are you",
        "good morning",
        "good evening",
        "good afternoon",
        "thanks",
        "thank you",
        "bye",
        "goodbye",
    ]

    # Only treat very short greetings as conversation.
    if (
        len(q.split()) <= 6
        and contains_any(q, conversation_patterns)
        and not contains_any(
            q,
            [
                "shuvo",
                "shuvo's",
                "shuvo is",
            ],
        )
    ):
        return {
            "route": "conversation",
            "sources": ["conversation"],
            "reason": "Casual conversational query."
        }

    # -------------------------------------------------------------------------
    # LIVE ACTIVITY WORDS
    # -------------------------------------------------------------------------

    activity_words = [
        "today",
        "so far",
        "this morning",
        "this afternoon",
        "this evening",
        "yesterday",
        "recent",
        "recently",
        "latest",
        "this week",
        "activity",
        "activities",
        "what did i do",
        "what have i done",
        "what did he do",
        "what has he done",
        "what did shuvo do",
        "what has shuvo done",
        "work update",
        "work updates",
        "recent work",
        "recent work updates",
    ]

    is_activity_query = contains_any(
        q,
        activity_words
    )

    # -------------------------------------------------------------------------
    # GITHUB
    # -------------------------------------------------------------------------

    github_keywords = [
        "github",
        "git hub",
        "repository",
        "repositories",
        "repo",
        "repos",
        "commit",
        "commits",
        "push",
        "pushed",
        "pull request",
        "pull requests",
        "branch",
        "github activity",
        "github update",
    ]

    github_requested = contains_any(
        q,
        github_keywords
    )

    # -------------------------------------------------------------------------
    # LEETCODE
    # -------------------------------------------------------------------------

    leetcode_keywords = [
        "leetcode",
        "leet code",
        "coding problem",
        "coding problems",
        "solved problems",
        "problems solved",
        "competitive programming",
    ]

    leetcode_requested = contains_any(
        q,
        leetcode_keywords
    )

    # -------------------------------------------------------------------------
    # GOOGLE
    # -------------------------------------------------------------------------

    google_keywords = [
        "google",
        "google sheet",
        "google sheets",
        "google doc",
        "google docs",
        "work update",
        "work updates",
        "research update",
        "research updates",
        "daily update",
        "daily updates",
        "what did i do today",
        "what have i done today",
        "what did he do today",
        "what has he done today",
        "what did shuvo do today",
        "what has shuvo done today",
    ]

    google_requested = contains_any(
        q,
        google_keywords
    )

    # -------------------------------------------------------------------------
    # STATIC PORTFOLIO / CHROMADB
    # -------------------------------------------------------------------------

    portfolio_keywords = [
        "shuvo",
        "who is shuvo",
        "tell me about shuvo",
        "about shuvo",
        "his background",
        "his education",
        "his experience",
        "his skills",
        "his projects",
        "his publications",
        "his papers",
        "his research",
        "research paper",
        "research papers",
        "publication",
        "publications",
        "project",
        "projects",
        "resume",
        "cv",
        "education",
        "experience",
        "skills",
        "technology",
        "technologies",
        "what does shuvo do",
        "what does he do",
        "what does shuvo actually do",
    ]

    portfolio_requested = contains_any(
        q,
        portfolio_keywords
    )

    # =========================================================================
    # COMBINED LIVE SOURCES
    # =========================================================================

    sources = []

    if github_requested:
        sources.append("github")

    if leetcode_requested:
        sources.append("leetcode")

    if google_requested:
        sources.append("google")

    # -------------------------------------------------------------------------
    # GENERAL "TODAY / RECENT ACTIVITY"
    #
    # These questions need multiple live sources.
    # -------------------------------------------------------------------------

    if is_activity_query and not sources:

        sources = [
            "github",
            "leetcode",
            "google",
        ]

    # -------------------------------------------------------------------------
    # STATIC PORTFOLIO INFORMATION
    # -------------------------------------------------------------------------

    if portfolio_requested:

        if "chroma" not in sources:
            sources.append("chroma")

        # Project and research queries benefit from
        # Google Sheets data too (the projects array
        # and work_updates contain structured info).
        project_research_words = [
            "project",
            "projects",
            "built",
            "developed",
            "research",
            "paper",
            "papers",
            "publication",
            "publications",
        ]

        if (
            contains_any(q, project_research_words)
            and "google" not in sources
        ):
            sources.append("google")

    # -------------------------------------------------------------------------
    # GENERAL QUESTIONS ABOUT SHUVO
    #
    # If the query doesn't explicitly mention a live source but asks about
    # Shuvo, use ChromaDB.
    # -------------------------------------------------------------------------

    shuvo_reference = contains_any(
        q,
        [
            "shuvo",
            "shubo",
            "he",
            "his",
        ]
    )

    if shuvo_reference and not sources:

        sources.append("chroma")

    # -------------------------------------------------------------------------
    # DEFAULT
    # -------------------------------------------------------------------------

    if not sources:

        sources = ["chroma"]

    # =========================================================================
    # ROUTE NAME
    # =========================================================================

    if len(sources) > 1:

        route = "hybrid"

        reason = (
            "Query requires information from multiple "
            "portfolio/live data sources."
        )

    elif sources[0] == "chroma":

        route = "portfolio"

        reason = (
            "Query requests static portfolio information "
            "stored in the ChromaDB knowledge base."
        )

    elif sources[0] == "github":

        route = "github"

        reason = (
            "Query requests GitHub repositories or activity."
        )

    elif sources[0] == "leetcode":

        route = "leetcode"

        reason = (
            "Query requests LeetCode statistics or activity."
        )

    elif sources[0] == "google":

        route = "google"

        reason = (
            "Query requests information stored in Google "
            "Sheets/Docs."
        )

    else:

        route = "unknown"

        reason = "Unable to determine the appropriate source."

    return {
        "query": original_query,
        "route": route,
        "sources": sources,
        "reason": reason,
    }


# =============================================================================
# TEST
# =============================================================================

TEST_QUERIES = [
    "What did I push to GitHub today?",
    "What did I do today?",
    "How many LeetCode problems have I solved?",
    "What are my recent work updates?",
    "What did I do on GitHub and LeetCode today?",
    "What research papers have I worked on?",
    "Tell me about Shuvo",
    "What does Shuvo actually do?",
    "Hi, do you know Shuvo?",
]


def main():

    print("=" * 70)
    print("QUERY ROUTER TEST")
    print("=" * 70)

    for query in TEST_QUERIES:

        result = route_query(query)

        print("\n" + "-" * 70)

        print(f"Query   : {query}")
        print(f"Route   : {result['route']}")
        print(f"Sources : {', '.join(result['sources'])}")
        print(f"Reason  : {result['reason']}")

    print("\n" + "=" * 70)
    print("QUERY ROUTER TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()