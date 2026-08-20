"""Build authoritative, query-specific context from the cleaned resume PDF."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEANED_RESUME_DIR = PROJECT_ROOT / "data" / "cleaned" / "resume"

SECTION_HEADINGS = (
    "PROFESSIONAL SUMMARY",
    "EXPERIENCE",
    "TECHNICAL SKILLS",
    "PROJECTS",
    "PUBLICATIONS",
    "EDUCATION",
    "ACHIEVEMENTS",
)

SECTION_KEYWORDS = {
    "PROFILE": (
        "name",
        "contact",
        "email",
        "phone",
        "location",
        "live",
        "github",
        "linkedin",
        "portfolio",
        "codeforces",
        "leetcode",
        "google scholar",
    ),
    "PROFESSIONAL SUMMARY": (
        "about",
        "who is",
        "professional summary",
        "specialize",
        "specialization",
        "ai engineer",
        "researcher",
        "what does",
    ),
    "EXPERIENCE": (
        "experience",
        "employment",
        "work history",
        "undergraduate researcher",
        "worked at",
        "research experience",
    ),
    "TECHNICAL SKILLS": (
        "skill",
        "skills",
        "tech stack",
        "technology",
        "technologies",
        "programming",
        "language",
        "framework",
        "database",
        "model",
        "tools",
        "deployment",
        "pytorch",
        "tensorflow",
        "rag",
        "llm",
        "computer vision",
        "nlp",
    ),
    "PROJECTS": (
        "project",
        "projects",
        "built",
        "developed",
        "agronest",
        "vat assistant",
        "uiu assistant",
        "victor von doom",
    ),
    "PUBLICATIONS": (
        "paper",
        "papers",
        "publication",
        "publications",
        "published",
        "under review",
        "vistext",
        "homograph",
        "polite on the surface",
    ),
    "EDUCATION": (
        "education",
        "university",
        "college",
        "cgpa",
        "gpa",
        "degree",
        "studying",
        "study",
        "student",
        "b.sc",
        "bsc",
        "computer science",
        "hsc",
        "higher secondary",
    ),
    "ACHIEVEMENTS": (
        "achievement",
        "achievements",
        "award",
        "awards",
        "runner-up",
        "reviewer",
        "reviewing",
        "certification",
        "certificate",
        "anthropic",
        "colm",
        "emnlp",
        "eccv",
    ),
}


def _contains_phrase(query: str, phrase: str) -> bool:
    return bool(re.search(rf"\b{re.escape(phrase)}\b", query, flags=re.IGNORECASE))


def split_resume_sections(text: str) -> dict[str, str]:
    """Split extracted resume text without allowing chunks to cross sections."""

    heading_pattern = "|".join(re.escape(heading) for heading in SECTION_HEADINGS)
    matches = list(
        re.finditer(
            rf"^(?P<heading>{heading_pattern})\s*$",
            text,
            flags=re.MULTILINE,
        )
    )

    if not matches:
        return {"PROFILE": text.strip()} if text.strip() else {}

    sections: dict[str, str] = {}
    profile = text[: matches[0].start()].strip()
    if profile:
        sections["PROFILE"] = profile

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        if body:
            sections[match.group("heading")] = body

    return sections


def load_resume_sections(resume_dir: Path = CLEANED_RESUME_DIR) -> tuple[dict[str, str], str]:
    """Load and section the newest cleaned resume JSON file."""

    candidates = sorted(resume_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return {}, ""

    source_path = candidates[0]
    document = json.loads(source_path.read_text(encoding="utf-8"))
    pages = document.get("pages", [])
    text = "\n".join(
        str(page.get("text", ""))
        for page in pages
        if isinstance(page, dict) and page.get("text")
    )
    filename = str(document.get("filename", source_path.stem))
    return split_resume_sections(text), filename


def select_resume_sections(query: str, available: Iterable[str]) -> list[str]:
    """Select only the resume sections relevant to a user question."""

    available_set = set(available)
    selected = [
        section
        for section, keywords in SECTION_KEYWORDS.items()
        if section in available_set and any(_contains_phrase(query, keyword) for keyword in keywords)
    ]

    if selected:
        asks_for_count = any(
            _contains_phrase(query, phrase)
            for phrase in ("how many", "count", "number of", "total")
        )
        if (
            asks_for_count
            and "PUBLICATIONS" in selected
            and "PROFESSIONAL SUMMARY" in available_set
            and "PROFESSIONAL SUMMARY" not in selected
        ):
            selected.insert(0, "PROFESSIONAL SUMMARY")
        return selected

    return [
        section
        for section in ("PROFILE", "PROFESSIONAL SUMMARY", "EDUCATION")
        if section in available_set
    ]


def format_education(body: str) -> str:
    """Make institution-to-qualification relationships explicit."""

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    records: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        is_institution = bool(
            re.search(r"\b(university|college|school|institute)\b", line, flags=re.IGNORECASE)
        )
        if is_institution and current:
            records.append(current)
            current = []
        current.append(line)

    if current:
        records.append(current)

    output = [
        "EDUCATION",
        "Each numbered item is a separate education record. Never transfer a degree, CGPA, date, or location between records.",
    ]

    for index, record in enumerate(records, start=1):
        output.append(f"Education record {index}:")
        output.append(f"- Institution: {record[0]}")
        for detail in record[1:]:
            output.append(f"- Detail: {detail}")

    return "\n".join(output)


def publication_consistency_note(sections: dict[str, str]) -> str:
    """Compare the summary's paper total with named publication records."""

    summary = sections.get("PROFESSIONAL SUMMARY", "")
    publications = sections.get("PUBLICATIONS", "")
    count_match = re.search(
        r"Author of\s+(\d+)\s+published\s+papers?\s+and\s+(\d+)\s+under review",
        summary,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not count_match or not publications:
        return ""

    published_count = int(count_match.group(1))
    review_count = int(count_match.group(2))
    claimed_total = published_count + review_count
    named_total = len(
        re.findall(r"\b(?:Under Review|Published)\b", publications, flags=re.IGNORECASE)
    )

    if claimed_total == named_total:
        return (
            "VERIFIED PUBLICATION COUNT: "
            f"The summary claims {claimed_total} papers and the Publications section names {named_total}. "
            "The counts are consistent."
        )

    return (
        "VERIFIED PUBLICATION COUNT DISCREPANCY: "
        f"The summary claims {published_count} published plus {review_count} under review "
        f"({claimed_total} total), but the Publications section names only {named_total} papers. "
        "These counts are NOT consistent. State this discrepancy clearly; do not claim they match."
    )


def get_authoritative_resume_context(query: str) -> tuple[str, str]:
    """Return exact relevant resume sections and their source filename."""

    sections, filename = load_resume_sections()
    if not sections:
        return "", ""

    selected = select_resume_sections(query, sections)
    output = [
        "AUTHORITATIVE RESUME FACTS",
        "Use these exact relationships when answering. Do not merge facts from different records.",
    ]

    if "PROFESSIONAL SUMMARY" in selected and "PUBLICATIONS" in selected:
        consistency_note = publication_consistency_note(sections)
        if consistency_note:
            output.append(consistency_note)

    for section in selected:
        body = sections[section]
        if section == "EDUCATION":
            output.append(format_education(body))
        else:
            output.append(f"{section}\n{body}")

    return "\n\n".join(output), filename
