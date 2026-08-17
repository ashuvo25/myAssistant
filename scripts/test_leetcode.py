import requests
import json

USERNAME = "shuvo_o"

URL = "https://leetcode.com/graphql/"

QUERY = """
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

payload = {
    "query": QUERY,
    "variables": {
        "username": USERNAME
    }
}

headers = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com/",
    "Origin": "https://leetcode.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    ),
}

print("=" * 70)
print("LEETCODE GRAPHQL TEST")
print("=" * 70)

print(f"Username: {USERNAME}")
print(f"Endpoint: {URL}")

try:
    response = requests.post(
        URL,
        json=payload,
        headers=headers,
        timeout=20,
    )

    print(f"\nHTTP Status: {response.status_code}")

    print("\nResponse:")

    try:
        data = response.json()
        print(json.dumps(data, indent=2))

    except Exception:
        print(response.text[:2000])

except requests.RequestException as e:
    print(f"\nRequest failed: {e}")