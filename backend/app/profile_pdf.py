"""Deterministic, candidate-owned standardized profile PDF rendering.

The renderer intentionally has no filesystem or database dependency. It emits
an on-demand PDF from the already filtered professional profile response, so
protected identity data cannot accidentally enter the artifact.
"""

from __future__ import annotations

import textwrap
from datetime import UTC, datetime
from typing import Any

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 50
TOP_Y = 790
LINE_HEIGHT = 15
LINES_PER_PAGE = 42


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip()


def _safe_characters(value: str) -> str:
    """Keep one UTF-16 code unit per PDF CID and replace unsupported values."""

    return "".join(character if ord(character) <= 0xFFFF else "?" for character in value)


def _hex_text(value: str) -> str:
    encoded = _safe_characters(value).encode("utf-16-be", errors="replace")
    return f"<{encoded.hex().upper()}>"


def _wrapped(value: str, width: int = 92) -> list[str]:
    value = _safe_characters(value)
    if not value:
        return [""]
    return textwrap.wrap(
        value,
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=True,
    ) or [""]


def _profile_lines(profile: dict[str, Any], generated_at: datetime) -> list[tuple[str, int]]:
    """Return presentation lines and font sizes from public profile data only."""

    preferences = profile.get("work_preferences")
    preferences = preferences if isinstance(preferences, dict) else {}
    experiences = profile.get("experience")
    experiences = experiences if isinstance(experiences, list) else []
    skills = profile.get("skills")
    skills = skills if isinstance(skills, list) else []

    lines: list[tuple[str, int]] = [
        ("FSP TALENT", 18),
        ("STANDARDIZED PROFESSIONAL PROFILE", 13),
        ("Candidate-declared professional information", 9),
        (f"Generated {generated_at.astimezone(UTC).date().isoformat()}", 8),
        ("", 8),
    ]

    display_name = _text(profile.get("display_name"), "Unnamed candidate")
    lines.append((display_name, 16))
    for label, key in (("Headline", "headline"), ("Location", "location")):
        value = _text(profile.get(key))
        if value:
            lines.append((f"{label}: {value}", 10))

    summary = _text(profile.get("summary"))
    if summary:
        lines.extend((("", 8), ("ABOUT", 11)))
        lines.extend((line, 10) for line in _wrapped(summary))

    if skills:
        lines.extend((("", 8), ("SKILLS", 11)))
        lines.extend(
            (line, 10)
            for line in _wrapped(" · ".join(_text(skill) for skill in skills if _text(skill)))
        )

    if experiences:
        lines.extend((("", 8), ("EXPERIENCE", 11)))
        for experience in experiences:
            if not isinstance(experience, dict):
                continue
            role = _text(experience.get("role"), "Role not specified")
            company = _text(experience.get("company"), "Company not specified")
            started = _text(experience.get("started_on"))
            ended = _text(experience.get("ended_on"), "present")
            period = f"{started} – {ended}" if started else ended
            lines.append((f"{role} · {company} · {period}", 10))
            description = _text(experience.get("description"))
            if description:
                lines.extend((f"  {line}", 9) for line in _wrapped(description, 88))
            technologies = experience.get("technologies")
            if isinstance(technologies, list) and technologies:
                tech_text = "Technologies: " + ", ".join(
                    _text(technology) for technology in technologies if _text(technology)
                )
                lines.extend((f"  {line}", 9) for line in _wrapped(tech_text, 88))

    work_values = []
    for key, label in (
        ("work_mode", "Work mode"),
        ("employment_type", "Employment type"),
        ("availability", "Availability"),
    ):
        value = _text(preferences.get(key))
        if value:
            work_values.append(f"{label}: {value}")
    if work_values:
        lines.extend((("", 8), ("WORK PREFERENCES", 11)))
        lines.extend((line, 10) for line in work_values)

    lines.extend(
        (
            ("", 12),
            ("This artifact contains candidate-declared profile information.", 8),
            ("It is not a verified assessment grade or employer recommendation.", 8),
        )
    )
    return lines


def _page_content(lines: list[tuple[str, int]], page_number: int, page_count: int) -> bytes:
    commands = ["BT"]
    y = TOP_Y
    for value, size in lines:
        commands.append(f"/F1 {size} Tf 1 0 0 1 {MARGIN_X} {y} Tm {_hex_text(value)} Tj")
        y -= LINE_HEIGHT if size <= 10 else LINE_HEIGHT + 2
    commands.append(
        f"/F1 7 Tf 1 0 0 1 {MARGIN_X} 28 Tm {_hex_text(f'Page {page_number} of {page_count}')} Tj"
    )
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def _cmap(characters: set[int]) -> bytes:
    entries = "\n".join(f"<{code:04X}> <{code:04X}>" for code in sorted(characters))
    cmap = f"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def
/CMapName /FSPProfileUnicode def
/CMapType 2 def
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
{len(characters)} beginbfchar
{entries}
endbfchar
endcmap
CMapName currentdict /CMap defineresource pop
end
end
"""
    return cmap.encode("ascii")


def _pdf_object(body: bytes) -> bytes:
    return body


def render_profile_pdf(profile: dict[str, Any], *, generated_at: datetime | None = None) -> bytes:
    """Render a valid on-demand PDF from a public candidate profile mapping."""

    generated_at = generated_at or datetime.now(UTC)
    all_lines = _profile_lines(profile, generated_at)
    pages = [
        all_lines[index : index + LINES_PER_PAGE]
        for index in range(0, len(all_lines), LINES_PER_PAGE)
    ]
    page_count = max(1, len(pages))

    used_characters = {0x0000}
    for value, _ in all_lines:
        used_characters.update(ord(character) for character in _safe_characters(value))
    for page_number in range(1, page_count + 1):
        used_characters.update(
            ord(character) for character in f"Page {page_number} of {page_count}"
        )

    objects: list[bytes] = []
    page_object_numbers: list[int] = []
    content_object_numbers: list[int] = []
    for page in pages:
        page_object_numbers.append(0)
        content_object_numbers.append(0)

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")  # Filled after page object numbers are known.
    objects.append(
        b"<< /Type /Font /Subtype /Type0 /BaseFont /FSPProfile /Encoding /Identity-H /DescendantFonts [4 0 R] /ToUnicode 5 0 R >>"
    )
    objects.append(
        b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /FSPProfile /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /DW 1000 >>"
    )
    objects.append(b"")  # Filled with the Unicode extraction map.

    for index, page in enumerate(pages):
        content_number = len(objects) + 1
        content = _page_content(page, index + 1, page_count)
        objects.append(
            f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream"
        )
        content_object_numbers[index] = content_number
        page_number = len(objects) + 1
        objects.append(b"")
        page_object_numbers[index] = page_number

    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{number} 0 R' for number in page_object_numbers)}] "
        f"/Count {page_count} >>"
    ).encode()
    objects[4] = (
        f"<< /Length {len(_cmap(used_characters))} >>\nstream\n".encode()
        + _cmap(used_characters)
        + b"endstream"
    )
    for index, page_number in enumerate(page_object_numbers):
        objects[page_number - 1] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_numbers[index]} 0 R >>"
        ).encode()

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_number} 0 obj\n".encode())
        output.extend(_pdf_object(body))
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)
