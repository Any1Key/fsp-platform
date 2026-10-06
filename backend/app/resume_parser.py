"""Bounded, deterministic extraction for candidate-owned PDF resumes.

This module deliberately produces declared evidence with provenance and
confidence. It does not infer a verified category or grade a candidate.
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from pypdf import PdfReader

PARSER_VERSION = "deterministic-2026-10-07"
MAX_EXTRACTED_CHARS = 120_000

SKILL_DICTIONARY = (
    "Python", "FastAPI", "Django", "Java", "Kotlin", "JavaScript", "TypeScript",
    "React", "Vue", "Node.js", "C#", ".NET", "Go", "C++", "SQL", "PostgreSQL",
    "MySQL", "Redis", "Docker", "Kubernetes", "Git", "Linux", "AWS", "Figma",
)
SOFT_SKILL_DICTIONARY = (
    "communication", "leadership", "mentoring", "teamwork", "problem solving",
    "аналитическое мышление", "коммуникация", "лидерство", "наставничество",
    "командная работа",
)
GRADE_ALIASES = {
    "junior": "Junior", "джуниор": "Junior", "джун": "Junior",
    "middle": "Middle", "мидл": "Middle",
    "senior": "Senior", "сениор": "Senior", "сеньор": "Senior",
}
SECTION_NAMES = {
    "skills": {"skills", "технологии", "навыки", "стек"},
    "experience": {"experience", "work experience", "опыт", "опыт работы", "работа"},
    "soft_skills": {"soft skills", "личные качества", "компетенции"},
}


class ResumeParseError(ValueError):
    """Raised when a PDF cannot provide text for deterministic extraction."""


def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises several parser-specific exceptions.
        raise ResumeParseError("pdf_text_unavailable") from exc
    text = "\n".join(pages).replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ResumeParseError("pdf_text_unavailable")
    return text[:MAX_EXTRACTED_CHARS]


def _field(value: Any, confidence: float, source: str) -> dict[str, Any]:
    return {"value": value, "confidence": confidence, "source": source}


def _lines(text: str) -> list[str]:
    return [line.strip(" •\t-") for line in text.splitlines() if line.strip(" •\t-")]


def _section_lines(lines: list[str], section: str) -> list[str]:
    names = SECTION_NAMES[section]
    start = None
    for index, line in enumerate(lines):
        if line.casefold().rstrip(":") in names:
            start = index + 1
            break
    if start is None:
        return []
    result: list[str] = []
    for line in lines[start:]:
        normalized = line.casefold().rstrip(":")
        if any(normalized in values for values in SECTION_NAMES.values()):
            break
        result.append(line)
    return result


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def parse_resume_text(text: str) -> dict[str, Any]:
    lines = _lines(text)
    header = lines[:8]
    email_matches = _unique(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE))
    phone_matches = _unique(re.findall(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)", text))
    link_matches = _unique(re.findall(r"https?://[^\s,)]+", text, re.IGNORECASE))

    excluded = {"resume", "резюме", "cv", "curriculum vitae"}
    full_name = next(
        (line for line in header if 2 <= len(line.split()) <= 5 and line.casefold() not in excluded
         and not re.search(r"[@:/]", line) and not re.search(r"\d", line)),
        None,
    )

    grade = None
    for match in re.finditer(r"(?<![\w-])(junior|middle|senior|джуниор|джун|мидл|сениор|сеньор)(?![\w-])", text, re.IGNORECASE):
        grade = GRADE_ALIASES[match.group(1).casefold()]
        break

    skill_text = "\n".join(_section_lines(lines, "skills")) or text
    skills = [skill for skill in SKILL_DICTIONARY if re.search(rf"(?<![\w+#.]){re.escape(skill)}(?![\w+#.])", skill_text, re.IGNORECASE)]
    soft_text = "\n".join(_section_lines(lines, "soft_skills")) or text
    soft_skills = [skill for skill in SOFT_SKILL_DICTIONARY if skill.casefold() in soft_text.casefold()]

    experience: list[dict[str, Any]] = []
    date_pattern = re.compile(r"(?P<start>\d{4}(?:-\d{2})?)\s*(?:[-–—]|to|по)\s*(?P<end>\d{4}(?:-\d{2})?|present|настоящее)", re.IGNORECASE)
    for line in _section_lines(lines, "experience"):
        date_match = date_pattern.search(line)
        if not date_match:
            continue
        before_date = line[:date_match.start()].strip(" ,|–—-")
        parts = re.split(r"\s+(?:at|в|@)\s+|\s*[|–—]\s*", before_date, maxsplit=1, flags=re.IGNORECASE)
        role = parts[0].strip() if parts else before_date
        company = parts[1].strip() if len(parts) > 1 else "Не указано"
        start = date_match.group("start")
        end = date_match.group("end").casefold()
        if len(start) == 4:
            start = f"{start}-01"
        if end in {"present", "настоящее"}:
            normalized_end = "present"
        else:
            normalized_end = f"{end}-01" if len(end) == 4 else end
        experience.append({
            "role": role[:120], "company": company[:120], "started_on": start,
            "ended_on": normalized_end, "description": None,
            "confidence": 0.78, "source": "experience_section",
        })

    role = next(
        (
            line for line in header[1:]
            if line != full_name
            and len(line) <= 160
            and not re.search(r"[@\d]", line)
            and line.casefold().rstrip(":") not in excluded
            and not any(line.casefold().rstrip(":") in values for values in SECTION_NAMES.values())
            and not line.casefold().startswith(("grade", "уровень", "грейд"))
        ),
        None,
    )
    contacts = {
        "emails": email_matches[:5], "phones": phone_matches[:5], "links": link_matches[:5],
        "confidence": 0.98 if email_matches or phone_matches else 0.0,
        "source": "contact_patterns",
    }
    return {
        "parser_version": PARSER_VERSION,
        "text_available": True,
        "fields": {
            "full_name": _field(full_name, 0.92 if full_name else 0.0, "header"),
            "headline": _field(role, 0.55 if role else 0.0, "header"),
            "contacts": contacts,
            "declared_grade": _field(grade, 0.82 if grade else 0.0, "grade_pattern"),
            "skills": [_field(skill, 0.88, "skills_dictionary") for skill in skills[:30]],
            "experience": experience[:12],
            "soft_skills": [_field(skill, 0.70, "soft_skills_dictionary") for skill in soft_skills[:20]],
        },
    }


def parse_resume_pdf(content: bytes) -> dict[str, Any]:
    text = extract_pdf_text(content)
    return parse_resume_text(text)


def unsupported_extraction() -> dict[str, Any]:
    return {
        "parser_version": PARSER_VERSION,
        "text_available": False,
        "fields": {
            "full_name": _field(None, 0.0, "unavailable"),
            "headline": _field(None, 0.0, "unavailable"),
            "contacts": {"emails": [], "phones": [], "links": [], "confidence": 0.0, "source": "unavailable"},
            "declared_grade": _field(None, 0.0, "unavailable"),
            "skills": [], "experience": [], "soft_skills": [],
        },
    }
