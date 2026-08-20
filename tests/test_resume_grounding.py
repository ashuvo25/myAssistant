"""Accuracy tests for resume-derived portfolio answers."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from chunk_documents import chunk_document  # noqa: E402
from resume_grounding import (  # noqa: E402
    get_authoritative_resume_context,
    load_resume_sections,
)
from query_router import route_query  # noqa: E402


ACCURACY_CASES = (
    ("What is his full name?", ("Md. Asaduzzaman Shuvo",)),
    ("What is his email and phone number?", ("iqbalmdshuvo@gmail.com", "+8801580341959")),
    ("What does Shuvo specialize in?", ("low-resource NLP", "multimodal AI", "computer vision")),
    ("Where did he work as an undergraduate researcher?", ("United International University", "Jan 2023", "June 2026")),
    ("What is his CGPA and university?", ("United International University (UIU)", "CGPA: 3.60/4.00")),
    ("Which college did he attend?", ("Govt. K.C. College", "Higher Secondary Certificate (HSC)")),
    ("What degree is he studying?", ("B.Sc. in Computer Science & Engineering", "2022", "2026")),
    ("What programming languages does he know?", ("Python", "C++", "Java", "JavaScript", "SQL", "Bash")),
    ("What AI and ML skills does he have?", ("PyTorch", "TensorFlow", "Hugging Face")),
    ("What projects has he built?", ("Victor Von Doom", "NBR VAT Assistant", "AGRONEST", "UIU Assistant")),
    ("What papers has he worked on?", ("When a Name Is Not a Name", "Polite on the Surface", "VisText-Mosquito")),
    ("What awards has he received?", ("1st Runner-Up", "2nd Runner-Up", "3rd Runner-Up")),
    ("Where is he an academic reviewer?", ("COLM", "EMNLP", "ECCV")),
    ("What certification does he have?", ("AI Fluency for Students", "Anthropic")),
)


class ResumeGroundingTests(unittest.TestCase):
    def test_every_resume_section_is_available(self) -> None:
        sections, filename = load_resume_sections()
        self.assertTrue(filename.lower().endswith(".pdf"))
        for heading in (
            "PROFILE",
            "PROFESSIONAL SUMMARY",
            "EXPERIENCE",
            "TECHNICAL SKILLS",
            "PROJECTS",
            "PUBLICATIONS",
            "EDUCATION",
            "ACHIEVEMENTS",
        ):
            self.assertIn(heading, sections)

    def test_authoritative_context_covers_resume_accuracy_cases(self) -> None:
        for question, expected_facts in ACCURACY_CASES:
            with self.subTest(question=question):
                context, _ = get_authoritative_resume_context(question)
                for expected in expected_facts:
                    self.assertIn(expected, context)

    def test_education_records_are_not_merged(self) -> None:
        context, _ = get_authoritative_resume_context(
            "What is his CGPA and where is he studying?"
        )
        university_record = context.index("Education record 1:")
        college_record = context.index("Education record 2:")
        self.assertLess(university_record, context.index("CGPA: 3.60/4.00"))
        self.assertLess(context.index("CGPA: 3.60/4.00"), college_record)
        self.assertLess(college_record, context.index("Higher Secondary Certificate (HSC)"))

    def test_resume_publication_count_exposes_source_discrepancy(self) -> None:
        context, _ = get_authoritative_resume_context(
            "According to his resume, how many papers does he have?"
        )
        self.assertRegex(context, r"Author of 2 published\s+papers and 3 under review")
        self.assertIn("5 total", context)
        self.assertIn("names only 3 papers", context)
        self.assertIn("NOT consistent", context)
        self.assertIn("When a Name Is Not a Name", context)
        self.assertIn("Polite on the Surface", context)
        self.assertIn("VisText-Mosquito", context)

    def test_resume_chunks_never_cross_section_boundaries(self) -> None:
        resume_path = next((PROJECT_ROOT / "data" / "cleaned" / "resume").glob("*.json"))
        document = json.loads(resume_path.read_text(encoding="utf-8"))
        chunks = chunk_document(document, resume_path)

        education_chunks = [
            chunk["text"]
            for chunk in chunks
            if "Resume | EDUCATION" in chunk["text"]
        ]
        self.assertTrue(education_chunks)
        education_text = "\n".join(education_chunks)
        self.assertIn("United International University (UIU)", education_text)
        self.assertIn("CGPA: 3.60/4.00", education_text)
        self.assertIn("Govt. K.C. College", education_text)
        self.assertIn("Higher Secondary Certificate (HSC)", education_text)
        self.assertNotIn("ACHIEVEMENTS", education_text)

    def test_explicit_resume_questions_do_not_mix_live_google_data(self) -> None:
        for question in (
            "According to his resume, what papers has he worked on?",
            "According to his resume, list his awards.",
            "According to his CV, list all projects.",
        ):
            with self.subTest(question=question):
                result = route_query(question)
                self.assertEqual(result["sources"], ["chroma"])
                self.assertEqual(result["route"], "portfolio")


if __name__ == "__main__":
    unittest.main()
