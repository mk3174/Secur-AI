"""Plain-text extraction from the resume formats commonly found in a Downloads folder."""

from __future__ import annotations

import re
from pathlib import Path

SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".md", ".txt"}


class UnsupportedFormat(ValueError):
    pass


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _clean(_extract_docx(path))
    if suffix == ".pdf":
        return _clean(_extract_pdf(path))
    if suffix in {".md", ".txt"}:
        return _clean(path.read_text(encoding="utf-8", errors="replace"))
    raise UnsupportedFormat(f"Unsupported resume format: {path.suffix}")


def _extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts: list[str] = [p.text for p in doc.paragraphs]
    # Some resumes lay out content in tables; flatten them row by row so no text is lost.
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            parts.append(" | ".join(dict.fromkeys(c for c in cells if c)))
    return "\n".join(parts)


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _clean(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u2022", "- ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
