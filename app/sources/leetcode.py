"""
LeetCode Data Source
--------------------
What: Fetches LeetCode profile and solving statistics.
Why: Provides live coding activity for portfolio questions.
Uses: LeetCode GraphQL endpoint.
"""

import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv


load_dotenv()


class LeetCodeSource:
    """Fetch LeetCode data for the portfolio chatbot."""

    GRAPHQL_URL = "https://leetcode.com/graphql/"

    def __init__(self):
        self.username = os.getenv("LEETCODE_USERNAME")

        if not self.username:
            raise ValueError(
                "LEETCODE_USERNAME is missing from .env"
            )

        self.headers = {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/",
            "Origin": "https://leetcode.com",
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            ),
        }

    def _query(
        self,
        query: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a LeetCode GraphQL query."""

        response = requests.post(
            self.GRAPHQL_URL,
            json={
                "query": query,
                "variables": variables,
            },
            headers=self.headers,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            raise RuntimeError(
                f"LeetCode GraphQL error: "
                f"{data['errors']}"
            )

        return data.get("data", {})

    def get_profile(self) -> Dict[str, Any]:
        """Return basic LeetCode profile information."""

        query = """
        query getUserProfile($username: String!) {
            matchedUser(username: $username) {
                username

                profile {
                    realName
                    aboutMe
                    userAvatar
                    ranking
                }

                submitStats: submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                        submissions
                    }

                    totalSubmissionNum {
                        difficulty
                        count
                        submissions
                    }
                }
            }
        }
        """

        data = self._query(
            query=query,
            variables={
                "username": self.username
            },
        )

        user = data.get("matchedUser")

        if not user:
            raise ValueError(
                f"LeetCode user '{self.username}' "
                f"was not found."
            )

        return user

    def get_stats(self) -> Dict[str, Any]:
        """Return LeetCode solving statistics."""

        profile = self.get_profile()

        return profile.get(
            "submitStats",
            {}
        )

    def get_all(self) -> Dict[str, Any]:
        """Return the main LeetCode data."""
        profile = self.get_profile()

        return {
            "source": "leetcode",
            "username": self.username,
            "profile": profile.get(
                "profile",
                {}
            ),
            "submit_stats": profile.get(
                "submitStats",
                {}
            ),
        }


if __name__ == "__main__":

    leetcode = LeetCodeSource()
    data = leetcode.get_all()

    print("\nLeetCode fetch successful")
    print(
        f"Username: "
        f"{data['username']}"
    )

    print(
        "Profile data: "
        f"{bool(data['profile'])}"
    )

    print(
        "Statistics: "
        f"{bool(data['submit_stats'])}"
    )