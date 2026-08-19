"""
Portfolio Context Processor
---------------------------

Converts raw source data into compact, relevant LLM context.

Flow:
    User Query
        ↓
    Query Router
        ↓
    Source Manager
        ↓
    Context Processor
        ↓
    Relevant Context
        ↓
    Qwen

This file does NOT generate the final answer.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List


# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_CHROMA_RESULTS = 4
MAX_CHROMA_CHARS = 2500

MAX_GITHUB_EVENTS = 10
MAX_GITHUB_REPOSITORIES = 6
MAX_GITHUB_CHARS = 1500

MAX_LEETCODE_CHARS = 1000

MAX_GOOGLE_CHARS = 2500
MAX_RESEARCH_ITEMS = 12

MAX_TOTAL_CONTEXT_CHARS = 4000


# =============================================================================
# GENERAL HELPERS
# =============================================================================

def clean_text(text: Any) -> str:
    """Convert a value into clean readable text."""

    if text is None:
        return ""

    text = str(text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def json_text(data: Any) -> str:
    """Convert JSON data into readable text."""

    try:
        return json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    except Exception:
        return str(data)


def truncate(text: str, max_chars: int) -> str:
    """Limit text to the specified number of characters."""

    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n...[truncated]"


# =============================================================================
# DATE HELPERS
# =============================================================================

def parse_timestamp(date_string: str):
    """Safely parse an ISO timestamp."""

    if not date_string:
        return None

    try:
        return datetime.fromisoformat(
            date_string.replace("Z", "+00:00")
        )

    except (ValueError, TypeError):
        return None


def is_today(date_string: str) -> bool:
    """
    Check whether an ISO timestamp belongs to today.

    Uses UTC because GitHub timestamps are returned in UTC.
    """

    timestamp = parse_timestamp(date_string)

    if timestamp is None:
        return False

    today = datetime.now(timezone.utc).date()

    return timestamp.date() == today


def is_recent(date_string: str) -> bool:
    """Check whether a timestamp is within the last 7 days."""

    timestamp = parse_timestamp(date_string)

    if timestamp is None:
        return False

    now = datetime.now(timezone.utc)

    # Avoid accidentally treating future timestamps as recent.
    if timestamp > now:
        return False

    age = now - timestamp

    return age.total_seconds() <= 7 * 24 * 60 * 60


# =============================================================================
# QUERY INTENT
# =============================================================================

def query_mentions_today(query: str) -> bool:
    """Return True when the query asks specifically about today."""

    query = query.lower()

    return any(
        phrase in query
        for phrase in [
            "today",
            "this day",
            "so far",
        ]
    )


def query_mentions_recent(query: str) -> bool:
    """Return True when the query asks about recent activity."""

    query = query.lower()

    return any(
        phrase in query
        for phrase in [
            "recent",
            "recently",
            "latest",
            "this week",
        ]
    )


def query_is_activity(query: str) -> bool:
    """Return True when the query asks about activity/work."""

    query = query.lower()

    patterns = [
"How many LeetCode problems have I solved?"
    ]

    return any(
        pattern in query
        for pattern in patterns
    )


# =============================================================================
# GITHUB PROCESSOR
# =============================================================================

def process_github(
    data: Any,
    query: str,
) -> str:
    """Extract useful GitHub information."""

    output: List[str] = []

    output.append("GITHUB DATA")

    if not isinstance(data, dict):
        output.append(clean_text(data))

        return truncate(
            "\n".join(output),
            MAX_GITHUB_CHARS,
        )

    # -------------------------------------------------------------------------
    # Profile
    # -------------------------------------------------------------------------

    profile = data.get("profile")

    if isinstance(profile, dict) and profile:

        output.append("\nGitHub Profile:")

        login = profile.get("login", "")
        name = profile.get("name", "")
        public_repos = profile.get("public_repos", "")
        followers = profile.get("followers", "")

        if login:
            output.append(f"Username: {login}")

        if name:
            output.append(f"Name: {name}")

        if public_repos != "":
            output.append(
                f"Public repositories: {public_repos}"
            )

        if followers != "":
            output.append(
                f"Followers: {followers}"
            )

    # -------------------------------------------------------------------------
    # Repositories
    # -------------------------------------------------------------------------

    repositories = data.get("repositories")

    if isinstance(repositories, list) and repositories:

        output.append("\nRepositories:")

        for repo in repositories[:MAX_GITHUB_REPOSITORIES]:

            if not isinstance(repo, dict):
                continue

            name = repo.get(
                "full_name",
                repo.get("name", ""),
            )

            language = repo.get(
                "language",
                "N/A",
            )

            description = clean_text(
                repo.get("description", "")
            )

            if not name:
                continue

            output.append(
                f"- {name} | Language: {language}"
            )

            if description:
                output.append(
                    f"  Description: {description}"
                )

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    events = data.get("events")

    if isinstance(events, list):

        events = [
            event
            for event in events
            if isinstance(event, dict)
        ]

        events.sort(
            key=lambda event: event.get(
                "created_at",
                "",
            ),
            reverse=True,
        )

        # Filter based on the question.
        if query_mentions_today(query):

            today_events = [
                event
                for event in events
                if is_today(
                    event.get(
                        "created_at",
                        "",
                    )
                )
            ]

            if today_events:
                events = today_events
            else:
                output.append("\nNote: No GitHub events logged specifically for today. Showing recent activity:")

        elif query_mentions_recent(query):

            events = [
                event
                for event in events
                if is_recent(
                    event.get(
                        "created_at",
                        "",
                    )
                )
            ]

        events = events[:MAX_GITHUB_EVENTS]

        if events:

            output.append("\nGitHub Activity:")

            for event in events:

                event_type = event.get(
                    "type",
                    "Unknown",
                )

                created_at = event.get(
                    "created_at",
                    "",
                )

                repo = event.get(
                    "repo",
                    {},
                )

                if not isinstance(repo, dict):
                    repo = {}

                repo_name = repo.get(
                    "name",
                    "Unknown repository",
                )

                payload = event.get(
                    "payload",
                    {},
                )

                if not isinstance(payload, dict):
                    payload = {}

                ref = payload.get(
                    "ref",
                    "",
                )

                line = (
                    f"- {event_type} "
                    f"| {repo_name} "
                    f"| {created_at}"
                )

                if ref:
                    line += (
                        f" | Branch: {ref}"
                    )

                output.append(line)

        elif query_mentions_today(query) or query_mentions_recent(query):

            output.append(
                "\nNo matching GitHub activity "
                "found for the requested period."
            )

    return truncate(
        "\n".join(output),
        MAX_GITHUB_CHARS,
    )


# =============================================================================
# LEETCODE PROCESSOR
# =============================================================================


def process_leetcode(
    data: dict,
    query: str,
) -> str:
    """
    Extract useful LeetCode statistics.

    Supports the current submit_stats.json structure:

        {
            "accepted": [...],
            "total": [...]
        }

    Also supports the older structure:

        {
            "acSubmissionNum": [...],
            "totalSubmissionNum": [...]
        }
    """

    output = []

    output.append("LEETCODE DATA")

    # =========================================================================
    # PROFILE
    # =========================================================================

    profile_data = data.get("profile")

    profile = {}

    if isinstance(profile_data, dict):

        nested_profile = profile_data.get("profile")

        if isinstance(nested_profile, dict):
            profile = nested_profile
        else:
            profile = profile_data

    # -------------------------------------------------------------------------
    # Username
    # -------------------------------------------------------------------------

    username = data.get("username", "")

    if not username and isinstance(profile_data, dict):

        username = profile_data.get(
            "username",
            "",
        )

    if username:

        output.append(
            f"Username: {username}"
        )

    # -------------------------------------------------------------------------
    # Name
    # -------------------------------------------------------------------------

    name = (
        profile.get("realName")
        or profile.get("name")
        or ""
    )

    if name:

        output.append(
            f"Name: {name}"
        )

    # -------------------------------------------------------------------------
    # Ranking
    # -------------------------------------------------------------------------

    ranking = profile.get("ranking")

    if ranking:

        output.append(
            f"Ranking: {ranking}"
        )

    # =========================================================================
    # SUBMISSION STATISTICS
    # =========================================================================

    stats = data.get(
        "submit_stats",
        {},
    )

    if not isinstance(stats, dict):

        stats = {}

    # -------------------------------------------------------------------------
    # Current format
    # -------------------------------------------------------------------------

    accepted = stats.get(
        "accepted",
        [],
    )

    total = stats.get(
        "total",
        [],
    )

    # -------------------------------------------------------------------------
    # Backward compatibility with old format
    # -------------------------------------------------------------------------

    if not accepted:

        accepted = stats.get(
            "acSubmissionNum",
            [],
        )

    if not total:

        total = stats.get(
            "totalSubmissionNum",
            [],
        )

    # =========================================================================
    # ACCEPTED / SOLVED
    # =========================================================================

    if isinstance(accepted, list) and accepted:

        output.append(
            "\nAccepted Problems:"
        )

        for item in accepted:

            if not isinstance(item, dict):
                continue

            difficulty = item.get(
                "difficulty",
                "",
            )

            count = item.get(
                "count",
                0,
            )

            submissions = item.get(
                "submissions",
                0,
            )

            if difficulty == "All":

                output.append(
                    f"- Total: {count} solved "
                    f"({submissions} submissions)"
                )

            else:

                output.append(
                    f"- {difficulty}: "
                    f"{count} solved "
                    f"({submissions} submissions)"
                )

    # =========================================================================
    # TOTAL SUBMISSIONS
    # =========================================================================

    if isinstance(total, list) and total:

        output.append(
            "\nTotal Submission Statistics:"
        )

        for item in total:

            if not isinstance(item, dict):
                continue

            difficulty = item.get(
                "difficulty",
                "",
            )

            count = item.get(
                "count",
                0,
            )

            submissions = item.get(
                "submissions",
                0,
            )

            if difficulty == "All":

                output.append(
                    f"- Total: {count} problems "
                    f"({submissions} submissions)"
                )

            else:

                output.append(
                    f"- {difficulty}: "
                    f"{count} problems "
                    f"({submissions} submissions)"
                )

    # =========================================================================
    # FALLBACK
    # =========================================================================

    if not accepted and not total:

        output.append(
            "\nNo LeetCode submission statistics "
            "were found."
        )

    return truncate(
        "\n".join(output),
        MAX_LEETCODE_CHARS,
    )



# =============================================================================
# GOOGLE PROCESSOR
# =============================================================================

def process_google(
    data: Any,
    query: str,
) -> str:
    """Process Google Sheets/Docs data."""

    output: List[str] = []

    output.append("GOOGLE DATA")

    if not isinstance(data, dict):

        output.append(
            clean_text(data)
        )

        return truncate(
            "\n".join(output),
            MAX_GOOGLE_CHARS,
        )

    # Research questions need the structured publication records first.
    # Otherwise long project descriptions can consume the entire context
    # budget before the research_updates section is reached.
    research_query = any(
        re.search(rf"\b{re.escape(term)}\b", query.lower())
        for term in (
            "research",
            "paper",
            "papers",
            "publication",
            "publications",
            "published",
        )
    )
    research_items = data.get("research_updates", [])

    if research_query and isinstance(research_items, list) and research_items:
        valid_items = [item for item in research_items if isinstance(item, dict)]
        output.append(f"\nResearch Papers ({len(valid_items)} total):")

        for item in valid_items[:MAX_RESEARCH_ITEMS]:
            title = clean_text(item.get("title", ""))
            if not title:
                continue

            details = []
            for label, key in (
                ("Role", "role"),
                ("Status", "status"),
                ("Venue", "venue"),
                ("Domain", "domain"),
            ):
                value = clean_text(item.get(key, ""))
                if value:
                    details.append(f"{label}: {value}")

            line = f"- {title}"
            if details:
                line += f" ({'; '.join(details)})"
            output.append(line)

            objective = clean_text(item.get("objective", ""))
            if objective and objective.casefold() != title.casefold():
                output.append(f"  Focus: {truncate(objective, 220)}")

            link = clean_text(item.get("link", ""))
            if link and link.lower() != "no links":
                output.append(f"  Link: {link}")

        if len(valid_items) > MAX_RESEARCH_ITEMS:
            output.append(
                f"- Showing {MAX_RESEARCH_ITEMS} of {len(valid_items)} papers."
            )

        return truncate("\n".join(output), MAX_GOOGLE_CHARS)

    # -------------------------------------------------------------------------
    # Featured Projects
    # -------------------------------------------------------------------------

    projects = data.get("projects", [])
    if isinstance(projects, list) and projects:
        output.append("\nFeatured AI Projects:")
        for proj in projects:
            if not isinstance(proj, dict):
                continue
            title = clean_text(proj.get("title", ""))
            description = clean_text(proj.get("description", proj.get("disctiption", "")))
            tools = clean_text(proj.get("tool_language", ""))
            url = clean_text(proj.get("url", ""))
            line = f"- {title}"
            if description:
                line += f": {description}"
            if tools:
                line += f" [Tech: {tools}]"
            if url:
                line += f" [Link: {url}]"
            output.append(line)

    # -------------------------------------------------------------------------
    # Work updates — convert to human-readable sentences
    # -------------------------------------------------------------------------

    work_keys = [
        "work_updates",
        "workUpdates",
        "updates",
        "work_update",
    ]

    work_items = None

    for key in work_keys:

        if key in data and data[key]:
            work_items = data[key]
            break

    if isinstance(work_items, list) and work_items:

        paper_updates = []
        project_updates = []

        for item in work_items:
            if not isinstance(item, dict):
                continue
            utype = clean_text(item.get("type", "")).lower()
            title_text = clean_text(item.get("title", "")).lower()
            if "paper" in utype or "paper" in title_text or "accepted" in title_text:
                paper_updates.append(item)
            else:
                project_updates.append(item)

        if paper_updates:
            output.append("\nResearch Papers & Acceptances:")
            for item in paper_updates:
                date = clean_text(item.get("date", ""))
                title = clean_text(item.get("title", ""))
                description = clean_text(item.get("description", item.get("disctiption", "")))
                link = clean_text(item.get("link", ""))
                line = "- "
                if date:
                    line += f"[{date}] "
                if title:
                    line += title
                if description:
                    line += f": {description}"
                if link and link != "no links":
                    line += f" (Link: {link})"
                output.append(line)

        if project_updates:
            output.append("\nProject Updates & Awards:")
            for item in project_updates:
                date = clean_text(item.get("date", ""))
                title = clean_text(item.get("title", ""))
                description = clean_text(item.get("description", item.get("disctiption", "")))
                link = clean_text(item.get("link", ""))
                line = "- "
                if date:
                    line += f"[{date}] "
                if title:
                    line += title
                if description:
                    line += f": {description}"
                if link and link != "no links":
                    line += f" (Link: {link})"
                output.append(line)

    # -------------------------------------------------------------------------
    # Research updates — convert to human-readable sentences
    # -------------------------------------------------------------------------

    research_keys = [
        "research_updates",
        "researchUpdates",
        "research_update",
    ]

    research_items = None

    for key in research_keys:

        if key in data and data[key]:
            research_items = data[key]
            break

    if isinstance(research_items, list) and research_items:

        output.append("\nResearch Updates:")

        for item in research_items:

            if not isinstance(item, dict):
                continue

            date = clean_text(
                item.get("date", "")
            )

            title = clean_text(
                item.get("title", "")
            )

            description = clean_text(
                item.get(
                    "description",
                    item.get(
                        "disctiption",
                        "",
                    ),
                )
            )

            if not title and not description:
                continue

            line = "- "

            if date:
                line += f"On {date}: "

            if title:
                line += title

            if description:
                line += f". {description}"

            output.append(line)

    # -------------------------------------------------------------------------
    # Projects
    # -------------------------------------------------------------------------

    if "projects" in data:

        projects = data["projects"]

        if isinstance(projects, list) and projects:

            output.append("\nProjects:")

            for project in projects:

                if not isinstance(project, dict):
                    continue

                title = clean_text(
                    project.get("title", "")
                )

                description = project.get(
                    "description",
                    project.get(
                        "disctiption",
                        "",
                    ),
                )

                description = clean_text(
                    description
                )

                if title:
                    output.append(
                        f"- {title}: {description}"
                    )

    # -------------------------------------------------------------------------
    # Social / stats (human-readable)
    # -------------------------------------------------------------------------

    known_keys = set(
        work_keys
        + research_keys
        + ["projects", "source"]
    )

    if "social" in data:

        social = data["social"]

        if isinstance(social, list):

            output.append("\nSocial & Stats:")

            for item in social:

                if not isinstance(item, dict):
                    continue

                for sk, sv in item.items():

                    sk_clean = clean_text(sk)
                    sv_clean = clean_text(sv)

                    if sk_clean and sv_clean:
                        output.append(
                            f"- {sk_clean}: {sv_clean}"
                        )

        known_keys.add("social")

    for key, value in data.items():

        if key in known_keys:
            continue

        # Skip empty-key garbage columns.
        if not key.strip():
            continue

        if value in (
            None,
            "",
            [],
            {},
        ):
            continue

        output.append(
            f"\n{key}:"
        )

        if isinstance(value, (list, dict)):
            output.append(
                json_text(value)
            )
        else:
            output.append(
                clean_text(value)
            )

    return truncate(
        "\n".join(output),
        MAX_GOOGLE_CHARS,
    )


# =============================================================================
# CHROMADB PROCESSOR
# =============================================================================

def process_chroma(
    data: Any,
    query: str,
) -> str:
    """Process semantic retrieval results."""

    output: List[str] = []

    output.append(
        "PORTFOLIO KNOWLEDGE BASE"
    )

    if not data:

        output.append(
            "No relevant documents were found."
        )

        return "\n".join(output)

    if not isinstance(data, list):

        output.append(
            clean_text(data)
        )

        return truncate(
            "\n".join(output),
            MAX_CHROMA_CHARS,
        )

    for index, item in enumerate(
        data[:MAX_CHROMA_RESULTS],
        start=1,
    ):

        if not isinstance(item, dict):
            continue

        metadata = item.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            metadata = {}

        document = metadata.get(
            "document",
            "Unknown",
        )

        page = metadata.get(
            "page",
            "Unknown",
        )

        distance = item.get(
            "distance"
        )

        text = clean_text(
            item.get(
                "text",
                "",
            )
        )

        output.append(
            f"Source {index} (from {document}):\n{text}"
        )

    return truncate(
        "\n\n".join(output),
        MAX_CHROMA_CHARS,
    )


# =============================================================================
# SOURCE RESULT PROCESSOR
# =============================================================================

def process_source_result(
    source_result: dict,
    query: str,
) -> str:
    """Process one source result."""

    if not isinstance(source_result, dict):
        return ""

    source = source_result.get(
        "source",
        "unknown",
    )

    # -------------------------------------------------------------------------
    # Error handling
    # -------------------------------------------------------------------------

    if source_result.get("error"):

        return (
            f"{str(source).upper()} ERROR:\n"
            f"{source_result['error']}"
        )

    data = source_result.get(
        "data"
    )

    # -------------------------------------------------------------------------
    # Source-specific processors
    # -------------------------------------------------------------------------

    if source == "github":

        return process_github(
            data,
            query,
        )

    if source == "leetcode":

        return process_leetcode(
            data,
            query,
        )

    if source == "google":

        return process_google(
            data,
            query,
        )

    if source in (
        "chroma",
        "chromadb",
        "portfolio",
    ):

        return process_chroma(
            data,
            query,
        )

    if source == "conversation":

        return (
            "CONVERSATION:\n"
            "This is a conversational query."
        )

    # -------------------------------------------------------------------------
    # Unknown source
    # -------------------------------------------------------------------------

    return (
        f"{str(source).upper()}:\n"
        f"{json_text(data)}"
    )


# =============================================================================
# BUILD CONTEXT
# =============================================================================

def build_context(
    source_response: dict,
) -> str:
    """
    Build the final compact context for Qwen.

    Expected input:
        SourceManager.execute_route(...)
    """

    if not isinstance(source_response, dict):
        return ""

    query = source_response.get(
        "query",
        "",
    )

    route = source_response.get(
        "route",
        "unknown",
    )

    results = source_response.get(
        "results",
        [],
    )

    if not isinstance(results, list):
        results = []

    sections: List[str] = []

    # -------------------------------------------------------------------------
    # Source contexts
    # -------------------------------------------------------------------------

    # Sort results so structured live sources (google, github, leetcode) come before chroma
    def source_priority(res: dict) -> int:
        s = res.get("source", "")
        if s == "google":
            return 1
        if s in ("github", "leetcode"):
            return 2
        return 3

    sorted_results = sorted(results, key=source_priority)

    for result in sorted_results:

        processed = process_source_result(
            result,
            query,
        )

        if processed:
            sections.append(
                processed
            )

    # -------------------------------------------------------------------------
    # Route-based context hint
    # -------------------------------------------------------------------------

    route_hints = {
        "portfolio": "The following is Shuvo's portfolio information:",
        "google": "The following are Shuvo's recent work updates and achievements:",
        "github": "The following is Shuvo's GitHub activity:",
        "leetcode": "The following are Shuvo's LeetCode statistics:",
        "hybrid": "The following is Shuvo's portfolio and recent activity information:",
    }

    hint = route_hints.get(route, "")

    # -------------------------------------------------------------------------
    # Final context
    # -------------------------------------------------------------------------

    final_context = "\n\n".join(
        sections
    )

    if hint:
        final_context = hint + "\n\n" + final_context

    return truncate(
        final_context,
        MAX_TOTAL_CONTEXT_CHARS,
    )


# =============================================================================
# CHATBOT COMPATIBILITY FUNCTION
# =============================================================================

def process_context(
    source_response: dict = None,
    question: str = "",
    route: dict = None,
    sources: dict = None,
) -> str:
    """
    Main compatibility interface used by chatbot.py.

    Supports:

        process_context(source_response)

    OR:

        process_context(
            question=question,
            route=route,
            sources=sources,
        )

    OR:

        process_context(
            question,
            sources,
        )
    """

    # =========================================================================
    # CASE 1
    # Full SourceManager response supplied directly
    # =========================================================================

    if isinstance(source_response, dict):

        # Already in SourceManager format.
        if "results" in source_response:

            return build_context(
                source_response
            )

        # Otherwise construct a response from it.
        source_response = {
            "query": source_response.get(
                "query",
                question,
            ),
            "route": source_response.get(
                "route",
                "unknown",
            ),
            "sources": source_response.get(
                "sources",
                [],
            ),
            "results": source_response.get(
                "results",
                [],
            ),
        }

        return build_context(
            source_response
        )

    # =========================================================================
    # CASE 2
    # Question + route + source dictionary
    # =========================================================================

    resolved_route = "unknown"
    resolved_sources: List[str] = []

    if isinstance(route, dict):

        resolved_route = route.get(
            "route",
            "unknown",
        )

        route_sources = route.get(
            "sources",
            [],
        )

        if isinstance(route_sources, list):
            resolved_sources = route_sources

    source_response = {
        "query": question,
        "route": resolved_route,
        "sources": resolved_sources,
        "results": [],
    }

    # =========================================================================
    # Convert source dictionary into standard results
    # =========================================================================

    if isinstance(sources, dict):

        for source_name, data in sources.items():

            # Already structured source result.
            if isinstance(data, dict) and (
                "source" in data
                or "data" in data
                or "error" in data
            ):

                result = data.copy()

                if "source" not in result:
                    result["source"] = source_name

                if "data" not in result and "error" not in result:
                    result["data"] = data

            else:

                result = {
                    "source": source_name,
                    "query": question,
                    "data": data,
                }

            source_response["results"].append(
                result
            )

    return build_context(
        source_response
    )


# =============================================================================
# TEST
# =============================================================================

def main():
    """
    Run basic integration tests using SourceManager.
    """

    try:
        from source_manager import SourceManager
    except ImportError:

        print(
            "ERROR: Could not import SourceManager."
        )

        print(
            "Run this file from the project directory "
            "where source_manager.py is importable."
        )

        return

    print("=" * 70)
    print("CONTEXT PROCESSOR TEST")
    print("=" * 70)

    manager = SourceManager()

    test_queries = [

        "What did I push to GitHub today?",

        "How many LeetCode problems have I solved?",

        "What are my recent work updates?",

        "What did I do today?",

        "What research papers have I worked on?",

        "Hi, do you know Shuvo?",
    ]

    for query in test_queries:

        print(
            "\n"
            + "=" * 70
        )

        print(
            f"QUERY: {query}"
        )

        try:

            source_response = (
                manager.execute_route(
                    query
                )
            )

            context = process_context(
                source_response
            )

            print(
                "\n--- PROCESSED CONTEXT ---"
            )

            print(context)

        except Exception as exc:

            print(
                "\nERROR:"
            )

            print(
                repr(exc)
            )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "CONTEXT PROCESSOR TEST COMPLETE"
    )

    print(
        "=" * 70
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()
