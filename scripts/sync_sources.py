"""
Source Synchronization
----------------------
What: Fetches the latest portfolio data from all external sources.
Why: Creates a clean raw-data snapshot before processing/RAG.
Sources: Cloudinary, GitHub, LeetCode, and Google Apps Script.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# PROJECT PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# SOURCE IMPORTS
# =============================================================================

from app.sources.github import GitHubSource
from app.sources.leetcode import LeetCodeSource
from app.sources.google import GoogleSource
from app.sources.cloudinary import CloudinarySource


# =============================================================================
# DIRECTORIES
# =============================================================================

RAW_DIR = PROJECT_ROOT / "data" / "raw"

GITHUB_DIR = RAW_DIR / "github"
LEETCODE_DIR = RAW_DIR / "leetcode"
GOOGLE_DIR = RAW_DIR / "google"
CLOUDINARY_DIR = RAW_DIR / "cloudinary"


# =============================================================================
# HELPERS
# =============================================================================

def create_directories():
    """Create required raw-data directories."""

    directories = [
        GITHUB_DIR,
        LEETCODE_DIR,
        GOOGLE_DIR,
        CLOUDINARY_DIR,
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


def save_json(
    path: Path,
    data,
):
    """Save Python data as formatted JSON."""

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )


def utc_now():
    """Return current UTC timestamp."""

    return datetime.now(
        timezone.utc
    ).isoformat()


# =============================================================================
# GITHUB
# =============================================================================

def sync_github():
    """Fetch and save GitHub data."""

    print("\n" + "=" * 70)
    print("GITHUB")
    print("=" * 70)

    try:

        github = GitHubSource()

        profile = github.get_profile()
        repositories = github.get_repositories()
        events = github.get_recent_events()

        save_json(
            GITHUB_DIR / "profile.json",
            profile,
        )

        save_json(
            GITHUB_DIR / "repositories.json",
            repositories,
        )

        save_json(
            GITHUB_DIR / "events.json",
            events,
        )

        print("✓ Profile fetched")
        print(
            f"✓ Repositories fetched: "
            f"{len(repositories)}"
        )

        print(
            f"✓ Events fetched: "
            f"{len(events)}"
        )

        return {
            "status": "success",
            "profile": True,
            "repositories": len(repositories),
            "events": len(events),
        }

    except Exception as error:

        print(
            f"✗ GitHub sync failed: {error}"
        )

        return {
            "status": "failed",
            "error": str(error),
        }


# =============================================================================
# LEETCODE
# =============================================================================

def sync_leetcode():
    """Fetch and save LeetCode data."""

    print("\n" + "=" * 70)
    print("LEETCODE")
    print("=" * 70)

    try:

        leetcode = LeetCodeSource()

        profile = leetcode.get_profile()

        save_json(
            LEETCODE_DIR / "profile.json",
            profile,
        )

        username = profile.get(
            "username",
            "unknown",
        )

        submit_stats = profile.get(
            "submitStats",
            {},
        )

        save_json(
            LEETCODE_DIR / "submit_stats.json",
            submit_stats,
        )

        print(
            f"✓ Profile fetched: "
            f"{username}"
        )

        print("✓ Submission statistics saved")

        return {
            "status": "success",
            "username": username,
            "stats": True,
        }

    except Exception as error:

        print(
            f"✗ LeetCode sync failed: {error}"
        )

        return {
            "status": "failed",
            "error": str(error),
        }


# =============================================================================
# GOOGLE
# =============================================================================

def sync_google():
    """Fetch and save Google Apps Script data."""

    print("\n" + "=" * 70)
    print("GOOGLE")
    print("=" * 70)

    try:

        google = GoogleSource()

        data = google.get_all()

        save_json(
            GOOGLE_DIR / "data.json",
            data,
        )

        print("✓ Google data fetched")
        print("✓ Google data saved")

        return {
            "status": "success",
        }

    except Exception as error:

        print(
            f"✗ Google sync failed: {error}"
        )

        return {
            "status": "failed",
            "error": str(error),
        }


# =============================================================================
# CLOUDINARY
# =============================================================================

def sync_cloudinary():
    """Fetch and save Cloudinary document metadata."""

    print("\n" + "=" * 70)
    print("CLOUDINARY")
    print("=" * 70)

    try:

        cloudinary_source = CloudinarySource()

        data = cloudinary_source.get_all()

        save_json(
            CLOUDINARY_DIR / "documents.json",
            data,
        )

        documents = data.get(
            "documents",
            [],
        )

        print(
            f"✓ Documents found: "
            f"{len(documents)}"
        )

        print(
            "✓ Cloudinary metadata saved"
        )

        return {
            "status": "success",
            "documents": len(documents),
        }

    except Exception as error:

        print(
            f"✗ Cloudinary sync failed: {error}"
        )

        return {
            "status": "failed",
            "error": str(error),
        }


# =============================================================================
# MAIN SYNC
# =============================================================================

def main():

    print("=" * 70)
    print("PERSONAL AI PORTFOLIO CHATBOT")
    print("SOURCE DATA SYNCHRONIZATION")
    print("=" * 70)

    print(
        f"\nProject directory:\n"
        f"  {PROJECT_ROOT}"
    )

    print(
        f"\nRaw data directory:\n"
        f"  {RAW_DIR}"
    )

    started_at = utc_now()

    create_directories()

    print("\nStarting synchronization...")

    results = {}

    results["github"] = sync_github()

    results["leetcode"] = sync_leetcode()

    results["google"] = sync_google()

    results["cloudinary"] = sync_cloudinary()

    finished_at = utc_now()

    # -------------------------------------------------------------------------
    # SYNC REPORT
    # -------------------------------------------------------------------------

    report = {
        "sync_started_at": started_at,
        "sync_finished_at": finished_at,
        "sources": results,
    }

    save_json(
        RAW_DIR / "sync_report.json",
        report,
    )

    # -------------------------------------------------------------------------
    # FINAL STATUS
    # -------------------------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("FINAL SYNC STATUS")
    print("=" * 70)

    successful = 0
    failed = 0

    for source, result in results.items():

        status = result.get(
            "status"
        )

        if status == "success":

            print(
                f"✓ {source.capitalize():<15} OK"
            )

            successful += 1

        else:

            print(
                f"✗ {source.capitalize():<15} FAILED"
            )

            failed += 1

    print("-" * 70)

    print(
        f"Passed: {successful}/4"
    )

    print(
        f"Failed: {failed}/4"
    )

    print("=" * 70)

    print(
        "\nRaw data saved to:"
    )

    print(
        f"  {RAW_DIR}"
    )

    print(
        "\nSync report:"
    )

    print(
        f"  {RAW_DIR / 'sync_report.json'}"
    )

    if failed == 0:

        print(
            "\n✓ ALL SOURCES SYNCHRONIZED SUCCESSFULLY"
        )

        print(
            "\nNext step:"
        )

        print(
            "  Verify the raw JSON data before"
            " building the processing/database layer."
        )

        return 0

    print(
        "\n! SOME SOURCES FAILED"
    )

    print(
        "Check the errors above before continuing."
    )

    return 1


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(main())