
"""
Portfolio Source Manager
------------------------

Responsible for retrieving information from:

    - ChromaDB
    - GitHub
    - LeetCode
    - Google

This module does NOT generate the final answer.

The SourceManager is intentionally conservative about the amount
of data returned to the LLM/context processor.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from query_router import route_query
from retriever import PortfolioRetriever


# =============================================================================
# CONFIGURATION
# =============================================================================

# Maximum data returned by each source.
MAX_GITHUB_EVENTS = 10
MAX_GITHUB_REPOSITORIES = 8

MAX_CHROMA_RESULTS = 5

MAX_FORMAT_CHARS = 12000


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

GITHUB_DIR = RAW_DATA_DIR / "github"
LEETCODE_DIR = RAW_DATA_DIR / "leetcode"
GOOGLE_DIR = RAW_DATA_DIR / "google"


# =============================================================================
# GENERAL HELPERS
# =============================================================================

def clean_text(text: Any) -> str:
    """Convert text into a compact readable string."""

    if text is None:
        return ""

    text = str(text)

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def truncate(
    text: str,
    max_chars: int,
) -> str:
    """Safely limit text size."""

    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    return (
        text[:max_chars]
        + "\n...[truncated]"
    )


# =============================================================================
# DATE HELPERS
# =============================================================================

def parse_timestamp(
    date_string: str,
):
    """Parse an ISO timestamp safely."""

    if not date_string:
        return None

    try:

        return datetime.fromisoformat(
            date_string.replace(
                "Z",
                "+00:00",
            )
        )

    except Exception:

        return None


def is_today(
    date_string: str,
) -> bool:
    """
    Check whether timestamp belongs to today in UTC.
    """

    timestamp = parse_timestamp(
        date_string
    )

    if timestamp is None:
        return False

    today = datetime.now(
        timezone.utc
    ).date()

    return timestamp.date() == today


def is_recent(
    date_string: str,
    days: int = 7,
) -> bool:
    """
    Check whether timestamp is within the
    specified number of days.
    """

    timestamp = parse_timestamp(
        date_string
    )

    if timestamp is None:
        return False

    now = datetime.now(
        timezone.utc
    )

    # Make naive timestamps UTC-aware.
    if timestamp.tzinfo is None:

        timestamp = timestamp.replace(
            tzinfo=timezone.utc
        )

    age = now - timestamp

    return (
        0
        <= age.total_seconds()
        <= days * 24 * 60 * 60
    )


# =============================================================================
# QUERY HELPERS
# =============================================================================

def query_mentions_today(
    query: str,
) -> bool:

    query = query.lower()

    return any(
        word in query
        for word in [
            "today",
            "this day",
            "so far",
        ]
    )


def query_mentions_recent(
    query: str,
) -> bool:

    query = query.lower()

    return any(
        word in query
        for word in [
            "recent",
            "recently",
            "latest",
            "this week",
        ]
    )


def query_is_activity(
    query: str,
) -> bool:

    query = query.lower()

    patterns = [
        "How many LeetCode problems have I solved?"
    ]

    return any(
        pattern in query
        for pattern in patterns
    )


# =============================================================================
# SOURCE MANAGER
# =============================================================================

class SourceManager:

    def __init__(self):

        print("=" * 70)
        print("PORTFOLIO SOURCE MANAGER")
        print("=" * 70)

        # ---------------------------------------------------------------------
        # ChromaDB
        # ---------------------------------------------------------------------

        try:

            self.retriever = PortfolioRetriever(
                top_k=MAX_CHROMA_RESULTS
            )

            print(
                "[OK] ChromaDB retriever ready"
            )

        except Exception as error:

            self.retriever = None

            print(
                "[WARNING] ChromaDB retriever unavailable"
            )

            print(
                f"  {error}"
            )

        # ---------------------------------------------------------------------
        # Live data
        # ---------------------------------------------------------------------

        print(
            "\n-> Checking live source data..."
        )

        self.github_available = (
            GITHUB_DIR.exists()
        )

        self.leetcode_available = (
            LEETCODE_DIR.exists()
        )

        self.google_available = (
            GOOGLE_DIR.exists()
        )

        print(
            f"  GitHub   : "
            f"{'ONLINE' if self.github_available else 'OFFLINE'}"
        )

        print(
            f"  LeetCode : "
            f"{'ONLINE' if self.leetcode_available else 'OFFLINE'}"
        )

        print(
            f"  Google   : "
            f"{'ONLINE' if self.google_available else 'OFFLINE'}"
        )

    # =========================================================================
    # JSON
    # =========================================================================

    @staticmethod
    def load_json(
        path: Path,
    ) -> Any:

        if not path.exists():
            return None

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as file:

                return json.load(file)

        except Exception as error:

            print(
                f"⚠ Failed to read "
                f"{path.name}: {error}"
            )

            return None

    # =========================================================================
    # GITHUB
    # =========================================================================

    def get_github_data(
        self,
        query: str,
    ) -> dict:
        """
        Return only GitHub information relevant
        to the user's query.

        Important:
        We filter events BEFORE passing them
        to the context processor.
        """

        result = {
            "source": "github",
            "query": query,
            "data": {},
        }

        if not self.github_available:

            result["error"] = (
                "GitHub data directory "
                "is unavailable."
            )

            return result

        # ---------------------------------------------------------------------
        # Profile
        # ---------------------------------------------------------------------

        profile = self.load_json(
            GITHUB_DIR / "profile.json"
        )

        if not isinstance(
            profile,
            dict,
        ):

            profile = {}

        compact_profile = {
            "login": profile.get(
                "login",
                "",
            ),
            "name": profile.get(
                "name",
                "",
            ),
            "public_repos": profile.get(
                "public_repos",
                "",
            ),
            "followers": profile.get(
                "followers",
                "",
            ),
        }

        # ---------------------------------------------------------------------
        # Repositories
        # ---------------------------------------------------------------------

        repositories = self.load_json(
            GITHUB_DIR / "repositories.json"
        )

        compact_repositories = []

        if isinstance(
            repositories,
            list,
        ):

            for repo in repositories:

                if not isinstance(
                    repo,
                    dict,
                ):
                    continue

                compact_repositories.append(
                    {
                        "name": repo.get(
                            "full_name",
                            repo.get(
                                "name",
                                "",
                            ),
                        ),
                        "language": repo.get(
                            "language",
                            "N/A",
                        ),
                        "description": truncate(
                            clean_text(
                                repo.get(
                                    "description",
                                    "",
                                )
                            ),
                            500,
                        ),
                    }
                )

                if len(
                    compact_repositories
                ) >= MAX_GITHUB_REPOSITORIES:

                    break

        # ---------------------------------------------------------------------
        # Events
        # ---------------------------------------------------------------------

        events = self.load_json(
            GITHUB_DIR / "events.json"
        )

        compact_events = []

        if isinstance(
            events,
            list,
        ):

            # Newest first.
            events = sorted(
                events,
                key=lambda event: event.get(
                    "created_at",
                    "",
                ),
                reverse=True,
            )

            # ---------------------------------------------------------------
            # Apply date filter BEFORE returning data.
            # ---------------------------------------------------------------

            if query_mentions_today(query):

                events = [
                    event
                    for event in events
                    if is_today(
                        event.get(
                            "created_at",
                            "",
                        )
                    )
                ]

            elif query_mentions_recent(query):

                events = [
                    event
                    for event in events
                    if is_recent(
                        event.get(
                            "created_at",
                            "",
                        ),
                        days=7,
                    )
                ]

            # ---------------------------------------------------------------
            # Convert events into compact objects.
            # ---------------------------------------------------------------

            for event in events:

                if not isinstance(
                    event,
                    dict,
                ):
                    continue

                payload = event.get(
                    "payload",
                    {},
                )

                if not isinstance(
                    payload,
                    dict,
                ):

                    payload = {}

                repo = event.get(
                    "repo",
                    {},
                )

                if not isinstance(
                    repo,
                    dict,
                ):

                    repo = {}

                compact_event = {
                    "type": event.get(
                        "type",
                        "Unknown",
                    ),
                    "repository": repo.get(
                        "name",
                        "Unknown repository",
                    ),
                    "created_at": event.get(
                        "created_at",
                        "",
                    ),
                }

                # Branch / reference.
                if payload.get("ref"):

                    compact_event[
                        "branch"
                    ] = payload.get(
                        "ref"
                    )

                # Push event commit information.
                if event.get("type") == "PushEvent":

                    commits = payload.get(
                        "commits",
                        [],
                    )

                    if isinstance(
                        commits,
                        list,
                    ):

                        compact_commits = []

                        for commit in commits[:5]:

                            if not isinstance(
                                commit,
                                dict,
                            ):
                                continue

                            compact_commits.append(
                                {
                                    "message": truncate(
                                        clean_text(
                                            commit.get(
                                                "message",
                                                "",
                                            )
                                        ),
                                        300,
                                    ),
                                    "sha": commit.get(
                                        "sha",
                                        "",
                                    )[:8],
                                }
                            )

                        if compact_commits:

                            compact_event[
                                "commits"
                            ] = compact_commits

                compact_events.append(
                    compact_event
                )

                if len(
                    compact_events
                ) >= MAX_GITHUB_EVENTS:

                    break

        # ---------------------------------------------------------------------
        # Final GitHub result
        # ---------------------------------------------------------------------

        result["data"] = {
            "profile": compact_profile,
            "repositories": compact_repositories,
            "events": compact_events,
        }

        return result

    # =========================================================================
    # LEETCODE
    # =========================================================================

    def get_leetcode_data(
        self,
        query: str,
    ) -> dict:

        result = {
            "source": "leetcode",
            "query": query,
            "data": {},
        }

        if not self.leetcode_available:

            result["error"] = (
                "LeetCode data directory "
                "is unavailable."
            )

            return result

        profile_data = self.load_json(
            LEETCODE_DIR / "profile.json"
        )

        submit_stats = self.load_json(
            LEETCODE_DIR / "submit_stats.json"
        )

        # ---------------------------------------------------------------------
        # Compact profile
        # ---------------------------------------------------------------------

        compact_profile = {}

        if isinstance(
            profile_data,
            dict,
        ):

            profile = profile_data.get(
                "profile",
                profile_data,
            )

            if isinstance(
                profile,
                dict,
            ):

                if profile.get(
                    "realName"
                ):

                    compact_profile[
                        "name"
                    ] = profile.get(
                        "realName"
                    )

                if profile.get(
                    "ranking"
                ):

                    compact_profile[
                        "ranking"
                    ] = profile.get(
                        "ranking"
                    )

        # ---------------------------------------------------------------------
        # Compact statistics
        # ---------------------------------------------------------------------

        compact_stats = {}

        if isinstance(
            submit_stats,
            dict,
        ):

            accepted = submit_stats.get(
                "acSubmissionNum",
                [],
            )

            total = submit_stats.get(
                "totalSubmissionNum",
                [],
            )

            compact_stats[
                "accepted"
            ] = accepted

            compact_stats[
                "total"
            ] = total

        username = ""

        if isinstance(
            profile_data,
            dict,
        ):

            username = profile_data.get(
                "username",
                "",
            )

            if not username:

                nested = profile_data.get(
                    "profile",
                    {},
                )

                if isinstance(
                    nested,
                    dict,
                ):

                    username = nested.get(
                        "username",
                        "",
                    )

        result["data"] = {
            "username": username,
            "profile": compact_profile,
            "submit_stats": compact_stats,
        }

        return result

    # =========================================================================
    # GOOGLE
    # =========================================================================

    def get_google_data(
        self,
        query: str,
    ) -> dict:

        result = {
            "source": "google",
            "query": query,
            "data": {},
        }

        if not self.google_available:

            result["error"] = (
                "Google data directory "
                "is unavailable."
            )

            return result

        data = self.load_json(
            GOOGLE_DIR / "data.json"
        )

        if data is None:

            result["data"] = {}

            return result

        # Keep Google structure but prevent
        # unnecessarily huge text fields.

        if isinstance(
            data,
            dict,
        ):

            compact_data = {}

            for key, value in data.items():

                if isinstance(
                    value,
                    str,
                ):

                    compact_data[key] = truncate(
                        value,
                        1500,
                    )

                elif isinstance(
                    value,
                    list,
                ):

                    compact_data[key] = value[
                        :20
                    ]

                else:

                    compact_data[key] = value

            result["data"] = compact_data

        else:

            result["data"] = truncate(
                str(data),
                5000,
            )

        return result

    # =========================================================================
    # CHROMADB
    # =========================================================================

    def get_chroma_data(
        self,
        query: str,
    ) -> dict:

        result = {
            "source": "chroma",
            "query": query,
            "data": [],
        }

        if self.retriever is None:

            result["error"] = (
                "ChromaDB retriever "
                "is unavailable."
            )

            return result

        try:

            retrieved = self.retriever.retrieve(
                query=query,
                top_k=MAX_CHROMA_RESULTS,
            )

            compact_results = []

            for item in retrieved[
                :MAX_CHROMA_RESULTS
            ]:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                metadata = item.get(
                    "metadata",
                    {},
                )

                if not isinstance(
                    metadata,
                    dict,
                ):

                    metadata = {}

                compact_results.append(
                    {
                        "text": truncate(
                            clean_text(
                                item.get(
                                    "text",
                                    "",
                                )
                            ),
                            1200,
                        ),
                        "metadata": {
                            "document": metadata.get(
                                "document",
                                "Unknown",
                            ),
                            "page": metadata.get(
                                "page",
                                "Unknown",
                            ),
                        },
                    }
                )

            result["data"] = (
                compact_results
            )

        except Exception as error:

            result["error"] = str(error)

        return result

    # =========================================================================
    # CONVERSATION
    # =========================================================================

    def get_conversation_data(
        self,
        query: str,
    ) -> dict:

        return {
            "source": "conversation",
            "query": query,
            "data": {
                "message": (
                    "This is a casual "
                    "conversational query."
                )
            },
        }

    # =========================================================================
    # UNKNOWN
    # =========================================================================

    def get_unknown_data(
        self,
        query: str,
    ) -> dict:

        return {
            "source": "unknown",
            "query": query,
            "data": {},
        }

    # =========================================================================
    # EXECUTE ROUTE
    # =========================================================================

    def execute_route(
        self,
        query: str,
    ) -> dict:

        routing = route_query(
            query
        )

        route = routing.get(
            "route",
            "unknown",
        )

        sources = routing.get(
            "sources",
            [],
        )

        response = {
            "query": query,
            "route": route,
            "sources": sources,
            "reason": routing.get(
                "reason",
                "",
            ),
            "results": [],
        }

        # ---------------------------------------------------------------------
        # Conversation
        # ---------------------------------------------------------------------

        if route == "conversation":

            response["results"].append(
                self.get_conversation_data(
                    query
                )
            )

            return response

        # ---------------------------------------------------------------------
        # Unknown
        # ---------------------------------------------------------------------

        if route == "unknown":

            response["results"].append(
                self.get_unknown_data(
                    query
                )
            )

            return response

        # ---------------------------------------------------------------------
        # Execute routed sources
        # ---------------------------------------------------------------------

        for source in sources:

            if source == "github":

                result = self.get_github_data(
                    query
                )

            elif source == "leetcode":

                result = self.get_leetcode_data(
                    query
                )

            elif source == "google":

                result = self.get_google_data(
                    query
                )

            elif source == "chroma":

                result = self.get_chroma_data(
                    query
                )

            elif source == "conversation":

                result = self.get_conversation_data(
                    query
                )

            else:

                result = {
                    "source": source,
                    "query": query,
                    "error": (
                        f"Unknown source: {source}"
                    ),
                }

            response["results"].append(
                result
            )

        return response


# =============================================================================
# COMPATIBILITY FUNCTION
# =============================================================================

def fetch_sources(
    question: str,
    route: dict,
) -> dict:
    """
    Compatibility wrapper used by chatbot.py.

    Returns the complete routed source response.
    """

    manager = SourceManager()

    return manager.execute_route(
        question
    )


# =============================================================================
# LLM FORMATTER
# =============================================================================

def format_for_llm(
    response: dict,
) -> str:
    """
    Convert source manager output into
    compact LLM-ready text.

    This is an additional safety layer.
    """

    sections = []

    query = response.get(
        "query",
        "",
    )

    route = response.get(
        "route",
        "unknown",
    )

    sections.append(
        f"USER QUESTION:\n{query}"
    )

    sections.append(
        f"ROUTE:\n{route}"
    )

    for result in response.get(
        "results",
        [],
    ):

        source = result.get(
            "source",
            "unknown",
        )

        sections.append(
            f"\nSOURCE: {source}"
        )

        if result.get("error"):

            sections.append(
                f"ERROR: "
                f"{result['error']}"
            )

            continue

        data = result.get(
            "data",
            {},
        )

        # ---------------------------------------------------------------------
        # GitHub
        # ---------------------------------------------------------------------

        if source == "github":

            profile = data.get(
                "profile",
                {},
            )

            sections.append(
                "GitHub Profile:\n"
                + json.dumps(
                    profile,
                    ensure_ascii=False,
                )
            )

            events = data.get(
                "events",
                [],
            )

            if events:

                sections.append(
                    "GitHub Activity:\n"
                    + json.dumps(
                        events,
                        ensure_ascii=False,
                    )
                )

            repositories = data.get(
                "repositories",
                [],
            )

            if repositories:

                sections.append(
                    "Repositories:\n"
                    + json.dumps(
                        repositories,
                        ensure_ascii=False,
                    )
                )

        # ---------------------------------------------------------------------
        # Chroma
        # ---------------------------------------------------------------------

        elif source == "chroma":

            for index, item in enumerate(
                data[:MAX_CHROMA_RESULTS],
                start=1,
            ):

                metadata = item.get(
                    "metadata",
                    {},
                )

                text = truncate(
                    clean_text(
                        item.get(
                            "text",
                            "",
                        )
                    ),
                    1200,
                )

                sections.append(
                    f"[Document {index}]\n"
                    f"Document: "
                    f"{metadata.get('document', '')}\n"
                    f"Page: "
                    f"{metadata.get('page', '')}\n"
                    f"Content:\n"
                    f"{text}"
                )

        # ---------------------------------------------------------------------
        # Everything else
        # ---------------------------------------------------------------------

        else:

            try:

                sections.append(
                    json.dumps(
                        data,
                        ensure_ascii=False,
                    )
                )

            except Exception:

                sections.append(
                    str(data)
                )

    final_text = "\n\n".join(
        sections
    )

    return truncate(
        final_text,
        MAX_FORMAT_CHARS,
    )


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":

    manager = SourceManager()

    tests = [
        "Tell me about Shuvo",
        "What did I do today?",
        "What did I push to GitHub today?",
        "How many LeetCode problems have I solved?",
    ]

    for query in tests:

        print(
            "\n"
            + "=" * 70
        )

        print(
            f"QUERY: {query}"
        )

        print(
            "=" * 70
        )

        response = manager.execute_route(
            query
        )

        formatted = format_for_llm(
            response
        )

        print(
            formatted
        )

        print(
            f"\nContext size: "
            f"{len(formatted)} characters"
        )

