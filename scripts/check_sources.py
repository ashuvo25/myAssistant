"""
Personal AI Portfolio Chatbot
================================

Source Connectivity & Data Fetch Test

Run:
    python scripts/check_sources.py

Checks:
    1. Cloudinary
    2. GitHub
    3. LeetCode
    4. Google Apps Script

This script DOES NOT:
    - create embeddings
    - use ChromaDB
    - run the LLM
    - modify external data

Keep all credentials inside .env.
Never commit .env to GitHub.
"""

import os
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

import cloudinary
import cloudinary.api


# =============================================================================
# PROJECT / ENVIRONMENT
# =============================================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"

load_dotenv(ENV_FILE)


# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

# -----------------------------------------------------------------------------
# Cloudinary
# -----------------------------------------------------------------------------

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

CLOUDINARY_FOLDER = os.getenv(
    "CLOUDINARY_FOLDER",
    "portfolio-ai"
)

# Current folders visible in your Cloudinary account
CLOUDINARY_SUBFOLDERS = os.getenv(
    "CLOUDINARY_SUBFOLDERS",
    "projects,publications,resume"
)


# -----------------------------------------------------------------------------
# GitHub
# -----------------------------------------------------------------------------

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# -----------------------------------------------------------------------------
# LeetCode
# -----------------------------------------------------------------------------

LEETCODE_USERNAME = os.getenv("LEETCODE_USERNAME")


# -----------------------------------------------------------------------------
# Google Apps Script
# -----------------------------------------------------------------------------

GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")


# -----------------------------------------------------------------------------
# Request settings
# -----------------------------------------------------------------------------

REQUEST_TIMEOUT = 15


# =============================================================================
# TERMINAL COLORS
# =============================================================================

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def success(message):
    print(f"{GREEN}✓ {message}{RESET}")


def failure(message):
    print(f"{RED}✗ {message}{RESET}")


def warning(message):
    print(f"{YELLOW}! {message}{RESET}")


def info(message):
    print(f"{CYAN}→ {message}{RESET}")


# =============================================================================
# RESULT TRACKING
# =============================================================================

results = {}


def record(name, status):
    results[name] = status


# =============================================================================
# 1. CLOUDINARY
# =============================================================================

def check_cloudinary():

    print("\n" + "=" * 70)
    print("1. CLOUDINARY")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Check credentials
    # -------------------------------------------------------------------------

    if not all([
        CLOUDINARY_CLOUD_NAME,
        CLOUDINARY_API_KEY,
        CLOUDINARY_API_SECRET,
    ]):
        failure("Cloudinary credentials are missing.")
        record("Cloudinary", False)
        return

    try:

        # ---------------------------------------------------------------------
        # Configure Cloudinary
        # ---------------------------------------------------------------------

        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True,
        )

        success("Cloudinary credentials loaded.")

        print(
            f"Root folder: {CLOUDINARY_FOLDER}"
        )

        # ---------------------------------------------------------------------
        # Parse subfolders from .env
        # ---------------------------------------------------------------------

        subfolders = [
            folder.strip()
            for folder in CLOUDINARY_SUBFOLDERS.split(",")
            if folder.strip()
        ]

        print("\nFolders to check:")

        for folder in subfolders:
            print(
                f"  • {CLOUDINARY_FOLDER}/{folder}"
            )

        # ---------------------------------------------------------------------
        # Check root folder itself
        # ---------------------------------------------------------------------

        try:

            root_response = cloudinary.api.resources_by_asset_folder(
                CLOUDINARY_FOLDER,
                max_results=100,
            )

            root_resources = root_response.get(
                "resources",
                []
            )

            if root_resources:

                success(
                    f"Found {len(root_resources)} asset(s) "
                    f"directly inside {CLOUDINARY_FOLDER}"
                )

            else:

                info(
                    f"No assets directly inside "
                    f"{CLOUDINARY_FOLDER} "
                    f"(this is expected for your current structure)."
                )

        except Exception as exc:

            warning(
                f"Could not inspect root folder: "
                f"{type(exc).__name__}: {exc}"
            )

        # ---------------------------------------------------------------------
        # Check every subfolder
        # ---------------------------------------------------------------------

        total_assets = 0
        successful_folders = 0

        print("\n" + "-" * 70)
        print("CLOUDINARY ASSETS")
        print("-" * 70)

        for subfolder in subfolders:

            folder_path = (
                f"{CLOUDINARY_FOLDER}/{subfolder}"
            )

            print(f"\n[{folder_path}]")

            try:

                response = cloudinary.api.resources_by_asset_folder(
                    folder_path,
                    max_results=500,
                )

                resources = response.get(
                    "resources",
                    []
                )

                if not resources:

                    warning(
                        f"No assets found in {folder_path}"
                    )

                    continue

                successful_folders += 1
                total_assets += len(resources)

                success(
                    f"Found {len(resources)} asset(s)"
                )

                for resource in resources:

                    public_id = resource.get(
                        "public_id",
                        "unknown"
                    )

                    resource_type = resource.get(
                        "resource_type",
                        "unknown"
                    )

                    file_format = resource.get(
                        "format",
                        "unknown"
                    )

                    secure_url = resource.get(
                        "secure_url",
                        ""
                    )

                    print(
                        f"  ✓ {public_id}"
                    )

                    print(
                        f"    type   : {resource_type}"
                    )

                    print(
                        f"    format : {file_format}"
                    )

                    if secure_url:

                        print(
                            f"    url    : {secure_url}"
                        )

            except Exception as exc:

                failure(
                    f"Failed to read {folder_path}: "
                    f"{type(exc).__name__}: {exc}"
                )

        # ---------------------------------------------------------------------
        # Cloudinary final status
        # ---------------------------------------------------------------------

        print("\n" + "-" * 70)

        if total_assets > 0:

            success(
                f"Cloudinary data fetch successful."
            )

            success(
                f"Total assets found: {total_assets}"
            )

            success(
                f"Folders containing assets: "
                f"{successful_folders}/{len(subfolders)}"
            )

            record("Cloudinary", True)

        else:

            failure(
                "Cloudinary connected successfully, "
                "but no assets were found in the configured subfolders."
            )

            record("Cloudinary", False)

    except Exception as exc:

        failure(
            f"Cloudinary connection failed: "
            f"{type(exc).__name__}: {exc}"
        )

        record("Cloudinary", False)


# =============================================================================
# 2. GITHUB
# =============================================================================

def check_github():

    print("\n" + "=" * 70)
    print("2. GITHUB")
    print("=" * 70)

    if not GITHUB_USERNAME:

        failure(
            "GITHUB_USERNAME is missing from .env"
        )

        record("GitHub", False)
        return

    try:

        info(
            f"Checking GitHub user: "
            f"{GITHUB_USERNAME}"
        )

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if GITHUB_TOKEN:

            headers["Authorization"] = (
                f"Bearer {GITHUB_TOKEN}"
            )

        # ---------------------------------------------------------------------
        # Profile
        # ---------------------------------------------------------------------

        profile_url = (
            f"https://api.github.com/users/"
            f"{GITHUB_USERNAME}"
        )

        response = requests.get(
            profile_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:

            failure(
                f"GitHub profile returned "
                f"HTTP {response.status_code}"
            )

            record("GitHub", False)
            return

        data = response.json()

        success(
            "GitHub API connection successful."
        )

        print(
            f"  Username      : {data.get('login')}"
        )

        print(
            f"  Name          : {data.get('name')}"
        )

        print(
            f"  Public repos  : {data.get('public_repos')}"
        )

        print(
            f"  Followers     : {data.get('followers')}"
        )

        # ---------------------------------------------------------------------
        # Repositories
        # ---------------------------------------------------------------------

        repos_url = (
            f"https://api.github.com/users/"
            f"{GITHUB_USERNAME}/repos"
        )

        repos_response = requests.get(
            repos_url,
            headers=headers,
            params={
                "per_page": 5,
                "sort": "updated",
            },
            timeout=REQUEST_TIMEOUT,
        )

        if repos_response.status_code == 200:

            repos = repos_response.json()

            success(
                f"Repository fetch successful: "
                f"{len(repos)} returned."
            )

            if repos:

                print(
                    "\n  Recently updated repositories:"
                )

                for repo in repos:

                    name = repo.get(
                        "name",
                        "unknown"
                    )

                    language = repo.get(
                        "language"
                    ) or "N/A"

                    print(
                        f"    • {name} "
                        f"({language})"
                    )

        else:

            warning(
                f"Repository request returned "
                f"HTTP {repos_response.status_code}"
            )

        # ---------------------------------------------------------------------
        # Public activity
        # ---------------------------------------------------------------------

        events_url = (
            f"https://api.github.com/users/"
            f"{GITHUB_USERNAME}/events/public"
        )

        events_response = requests.get(
            events_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if events_response.status_code == 200:

            events = events_response.json()

            success(
                f"Public activity fetch successful: "
                f"{len(events)} event(s)"
            )

            if events:

                print(
                    "\n  Recent activity:"
                )

                for event in events[:5]:

                    event_type = event.get(
                        "type",
                        "Unknown"
                    )

                    created_at = event.get(
                        "created_at",
                        ""
                    )

                    repo = event.get(
                        "repo",
                        {}
                    )

                    repo_name = repo.get(
                        "name",
                        "Unknown"
                    )

                    print(
                        f"    • {event_type} | "
                        f"{repo_name} | "
                        f"{created_at}"
                    )

        else:

            warning(
                f"Activity request returned "
                f"HTTP {events_response.status_code}"
            )

        # ---------------------------------------------------------------------
        # API rate limit
        # ---------------------------------------------------------------------

        rate_url = (
            "https://api.github.com/rate_limit"
        )

        rate_response = requests.get(
            rate_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if rate_response.status_code == 200:

            rate_data = rate_response.json().get(
                "rate",
                {}
            )

            print("\n  API rate limit:")

            print(
                f"    Remaining : "
                f"{rate_data.get('remaining')}"
            )

            print(
                f"    Limit     : "
                f"{rate_data.get('limit')}"
            )

        record("GitHub", True)

    except requests.RequestException as exc:

        failure(
            f"GitHub request failed: {exc}"
        )

        record("GitHub", False)

    except Exception as exc:

        failure(
            f"GitHub check failed: "
            f"{type(exc).__name__}: {exc}"
        )

        record("GitHub", False)


# =============================================================================
# 3. LEETCODE
# =============================================================================

def check_leetcode():

    print("\n" + "=" * 70)
    print("3. LEETCODE")
    print("=" * 70)

    if not LEETCODE_USERNAME:

        failure(
            "LEETCODE_USERNAME is missing from .env"
        )

        record("LeetCode", False)
        return

    profile_url = (
        f"https://leetcode.com/u/"
        f"{LEETCODE_USERNAME}/"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:

        info(
            f"Checking LeetCode profile: "
            f"{LEETCODE_USERNAME}"
        )

        response = requests.get(
            profile_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:

            success(
                "LeetCode profile is reachable."
            )

            print(
                f"  Profile: {profile_url}"
            )

            print(
                f"  HTTP status: "
                f"{response.status_code}"
            )

            info(
                "Profile access works. "
                "Activity extraction will be tested separately."
            )

            record("LeetCode", True)

        elif response.status_code == 403:

            warning(
                "LeetCode returned HTTP 403."
            )

            warning(
                "The profile may be blocking automated requests."
            )

            warning(
                "This does NOT necessarily mean "
                "the username is invalid."
            )

            record("LeetCode", False)

        elif response.status_code == 404:

            failure(
                "LeetCode profile was not found."
            )

            warning(
                "Check LEETCODE_USERNAME."
            )

            record("LeetCode", False)

        else:

            warning(
                f"LeetCode returned "
                f"HTTP {response.status_code}"
            )

            record("LeetCode", False)

    except requests.RequestException as exc:

        failure(
            f"LeetCode request failed: {exc}"
        )

        record("LeetCode", False)

    except Exception as exc:

        failure(
            f"LeetCode check failed: "
            f"{type(exc).__name__}: {exc}"
        )

        record("LeetCode", False)


# =============================================================================
# 4. GOOGLE APPS SCRIPT
# =============================================================================

def check_google_script():

    print("\n" + "=" * 70)
    print("4. GOOGLE APPS SCRIPT")
    print("=" * 70)

    if not GOOGLE_SCRIPT_URL:

        failure(
            "GOOGLE_SCRIPT_URL is missing from .env"
        )

        record("Google Apps Script", False)
        return

    try:

        info(
            "Checking Google Apps Script endpoint..."
        )

        response = requests.get(
            GOOGLE_SCRIPT_URL,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:

            failure(
                f"Google Apps Script returned "
                f"HTTP {response.status_code}"
            )

            record(
                "Google Apps Script",
                False
            )

            return

        success(
            "Google Apps Script endpoint is reachable."
        )

        print(
            f"  HTTP status: "
            f"{response.status_code}"
        )

        print(
            f"  Response type: "
            f"{response.headers.get('content-type')}"
        )

        body = response.text.strip()

        if body:

            preview = (
                body[:300]
                .replace("\n", " ")
            )

            print(
                f"  Response preview: "
                f"{preview}"
            )

        record(
            "Google Apps Script",
            True
        )

    except requests.RequestException as exc:

        failure(
            f"Google Apps Script request failed: "
            f"{exc}"
        )

        record(
            "Google Apps Script",
            False
        )

    except Exception as exc:

        failure(
            f"Google Apps Script check failed: "
            f"{type(exc).__name__}: {exc}"
        )

        record(
            "Google Apps Script",
            False
        )


# =============================================================================
# FINAL SUMMARY
# =============================================================================

def print_summary():

    print("\n\n")

    print("=" * 70)
    print("FINAL SOURCE STATUS")
    print("=" * 70)

    for name, status in results.items():

        if status:

            print(
                f"{GREEN}✓ "
                f"{name:<25} OK"
                f"{RESET}"
            )

        else:

            print(
                f"{RED}✗ "
                f"{name:<25} FAILED"
                f"{RESET}"
            )

    successful = sum(
        results.values()
    )

    total = len(results)

    print("-" * 70)

    print(
        f"Passed: {successful}/{total}"
    )

    if successful == total:

        print(
            f"{GREEN}{BOLD}"
            "All configured source connections "
            "are working."
            f"{RESET}"
        )

    else:

        print(
            f"{YELLOW}"
            "Some sources need attention."
            f"{RESET}"
        )

    print("=" * 70)

    print("\nNext steps:")

    print(
        "  1. Verify Cloudinary PDF URLs."
    )

    print(
        "  2. Verify GitHub activity data."
    )

    print(
        "  3. Solve LeetCode activity retrieval."
    )

    print(
        "  4. Verify Google Sheet/Docs data."
    )

    print(
        "  5. Build activity database."
    )

    print(
        "  6. Then build embeddings + ChromaDB."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("\n" + "=" * 70)

    print(
        "PERSONAL AI PORTFOLIO CHATBOT"
    )

    print(
        "SOURCE CONNECTIVITY TEST"
    )

    print("=" * 70)

    print(
        f"\nEnvironment file:"
    )

    print(
        f"  {ENV_FILE}"
    )

    if not ENV_FILE.exists():

        warning(
            ".env file was not found."
        )

        print(
            "Create .env in the project root."
        )

    print(
        f"\nTest started: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # Run all checks
    check_cloudinary()
    check_github()
    check_leetcode()
    check_google_script()

    # Final report
    print_summary()


if __name__ == "__main__":
    main()