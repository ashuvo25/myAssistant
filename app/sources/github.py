"""
GitHub Data Source
------------------
What: Fetches GitHub profile, repositories, and recent activity.
Why: Provides live portfolio activity for questions like
     "What did I do today?"
Uses: GitHub REST API.
"""

import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


load_dotenv()


class GitHubSource:
    """Fetch live GitHub data for the portfolio chatbot."""

    BASE_URL = "https://api.github.com"

    def __init__(self):
        self.username = os.getenv("GITHUB_USERNAME")
        self.token = os.getenv("GITHUB_TOKEN")

        if not self.username:
            raise ValueError("GITHUB_USERNAME is missing from .env")

        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, endpoint: str, params: dict | None = None) -> Any:
        """Send a GET request to GitHub."""
        response = requests.get(
            f"{self.BASE_URL}{endpoint}",
            headers=self.headers,
            params=params,
            timeout=15,
        )

        response.raise_for_status()
        return response.json()

    def get_profile(self) -> Dict[str, Any]:
        """Return GitHub profile information."""
        return self._get(f"/users/{self.username}")

    def get_repositories(
        self,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return the user's repositories."""
        return self._get(
            f"/users/{self.username}/repos",
            params={
                "per_page": limit,
                "sort": "updated",
            },
        )

    def get_recent_events(
        self,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return recent public GitHub activity."""
        events = self._get(
            f"/users/{self.username}/events/public"
        )

        return events[:limit]

    def get_all(self) -> Dict[str, Any]:
        """Return the main GitHub data used by the chatbot."""
        return {
            "source": "github",
            "username": self.username,
            "profile": self.get_profile(),
            "repositories": self.get_repositories(),
            "recent_events": self.get_recent_events(),
        }


if __name__ == "__main__":

    github = GitHubSource()
    data = github.get_all()

    print("\nGitHub fetch successful")
    print(f"Username: {data['username']}")
    print(
        f"Repositories: "
        f"{len(data['repositories'])}"
    )
    print(
        f"Recent events: "
        f"{len(data['recent_events'])}"
    )