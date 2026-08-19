"""Validate synchronized portfolio data before it is committed."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.routes.health import health_check  # noqa: E402


RAW_DATA = PROJECT_ROOT / "data" / "raw"
DATA_FILES = (
    RAW_DATA / "github" / "profile.json",
    RAW_DATA / "github" / "repositories.json",
    RAW_DATA / "github" / "events.json",
    RAW_DATA / "leetcode" / "profile.json",
    RAW_DATA / "leetcode" / "submit_stats.json",
    RAW_DATA / "google" / "data.json",
    RAW_DATA / "cloudinary" / "documents.json",
    RAW_DATA / "sync_report.json",
)
EXPECTED_SOURCES = {"github", "leetcode", "google", "cloudinary"}


def load_json(path: Path) -> object:
    if not path.is_file():
        raise FileNotFoundError(f"Required data file is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    documents = {path: load_json(path) for path in DATA_FILES}
    report = documents[RAW_DATA / "sync_report.json"]

    if not isinstance(report, dict):
        raise ValueError("The synchronization report must be a JSON object.")

    sources = report.get("sources", {})
    if not isinstance(sources, dict):
        raise ValueError("The synchronization report has an invalid sources field.")

    missing = EXPECTED_SOURCES.difference(sources)
    failed: dict[str, object] = {}
    for name, result in sources.items():
        if not isinstance(result, dict):
            failed[name] = "invalid result"
        elif result.get("status") != "success":
            failed[name] = result.get("error", "unknown error")

    if missing:
        raise ValueError(f"Missing synchronization results: {sorted(missing)}")
    if failed:
        raise ValueError(f"Failed synchronization sources: {failed}")

    health = health_check()
    if health.get("status") != "healthy":
        raise ValueError(f"Backend health verification failed: {health}")

    print(f"Validated {len(DATA_FILES)} JSON files")
    print("Sync report: 4/4 sources successful")
    print(f"Backend health: {health['status']} (v{health['version']})")


if __name__ == "__main__":
    main()
