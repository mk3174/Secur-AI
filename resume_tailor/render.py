"""Render the Markdown resume produced by the model into an ATS-friendly .docx (single column, no tables)."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

BODY_FONT = "Calibri"
BODY_SIZE = Pt(10.5)
NAME_SIZE = Pt(18)
SECTION_SIZE = Pt(11.5)
MARGIN = Inches(0.65)

BOLD_SPLIT = re.compile(r"(\*\*[^*]+\*\*)")


def _set_base_style(doc: Document) -> None:
    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = BODY_SIZE
    style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    style.paragraph_format.space_after = Pt(2)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.line_spacing = 1.0
    for section in doc.sections:
        section.top_margin = section.bottom_margin = MARGIN
        section.left_margin = section.right_margin = MARGIN


def _bottom_border(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "444444")
    borders.append(bottom)
    p_pr.append(borders)


def _add_inline(paragraph, text: str, size=None, bold_all: bool = False) -> None:
    for chunk in BOLD_SPLIT.split(text):
        if not chunk:
            continue
        is_bold = chunk.startswith("**") and chunk.endswith("**")
        run = paragraph.add_run(chunk[2:-2] if is_bold else chunk)
        run.bold = bold_all or is_bold
        if size:
            run.font.size = size


def _right_tab(paragraph, doc: Document) -> None:
    section = doc.sections[0]
    usable = section.page_width - section.left_margin - section.right_margin
    paragraph.paragraph_format.tab_stops.add_tab_stop(usable, WD_TAB_ALIGNMENT.RIGHT)


def _entry_heading(doc: Document, line: str) -> None:
    """### Title | Company | Location | Dates  ->  'Title, Company — Location <tab> Dates'."""
    parts = [p.strip() for p in line.split("|")]
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(1)
    paragraph.paragraph_format.keep_with_next = True
    dates = parts[-1] if len(parts) >= 3 and _looks_like_dates(parts[-1]) else None
    head = parts[:-1] if dates else parts
    title = head[0] if head else ""
    rest = head[1:]
    _add_inline(paragraph, title, bold_all=True)
    if rest:
        _add_inline(paragraph, ", " + ", ".join(r for r in rest if r))
    if dates:
        _right_tab(paragraph, doc)
        _add_inline(paragraph, "\t" + dates)


def _looks_like_dates(text: str) -> bool:
    return bool(re.search(r"(19|20)\d{2}|present|current", text, re.IGNORECASE))


def render_docx(markdown: str, out_path: Path) -> Path:
    doc = Document()
    _set_base_style(doc)

    lines = [ln.rstrip() for ln in markdown.strip().splitlines()]
    seen_name = False
    seen_contact = False
    in_skills = False

    for raw in lines:
        line = raw.strip()
        if not line or line in {"---", "***"}:
            continue

        if line.startswith("# ") and not seen_name:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            _add_inline(p, line[2:].strip(), size=NAME_SIZE, bold_all=True)
            seen_name = True
            continue

        if seen_name and not seen_contact and not line.startswith("#"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(6)
            _add_inline(p, line.replace("**", ""))
            seen_contact = True
            continue

        if line.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            heading = line[3:].strip().upper()
            run = p.add_run(heading)
            run.bold = True
            run.font.size = SECTION_SIZE
            run.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
            _bottom_border(p)
            in_skills = "SKILL" in heading
            continue

        if line.startswith("### "):
            _entry_heading(doc, line[4:])
            continue

        if line.startswith(("- ", "* ", "• ")):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.left_indent = Inches(0.25)
            _add_inline(p, line[2:].strip())
            continue

        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1 if in_skills else 3)
        _add_inline(p, line)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path


def markdown_to_text(markdown: str) -> str:
    """Approximation of what an ATS parser will read from the rendered document."""
    text = re.sub(r"^#+\s*", "", markdown, flags=re.MULTILINE)
    text = text.replace("**", "").replace("|", " ")
    return text
