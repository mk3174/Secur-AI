"""Claude Opus 5.5 tailoring calls."""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import DEFAULT_EFFORT, DEFAULT_MODEL

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md"

# Appended to the user's system prompt so the model's output can be parsed into a .docx deterministically.
OUTPUT_CONTRACT = """
## 9. OUTPUT CONTRACT (machine-parsed; follow exactly)
Return ONLY the resume as Markdown. No preamble, no commentary, no code fences. Structure:

# Full Name
City, ST | Phone | Email | LinkedIn | GitHub          <- one line, pipe-separated; include only items present in the source resume

## Professional Summary
One paragraph, 3-5 lines.

## Skills
**Category Name:** skill, skill, skill                 <- one line per category, 4-7 categories, JD terminology first

## Experience
### Job Title | Company | Location | Mon YYYY - Mon YYYY
- Bullet (XYZ / STAR, quantified, JD keywords first)

## Projects
### Project Title | Tech, Stack, Used
- Bullet

## Education
### Degree | School | Location | Year

## Certifications
- Item (omit this section entirely if none)

Rules:
- Use "-" for bullets; no tables, columns, images, icons, HTML or emoji.
- Keep every employer, job title, date range and degree exactly as written in the source resume.
- Keep the whole resume to two pages or fewer (roughly 600-850 words).
- Keep bullets to one or two lines each; 3-5 bullets per role, most JD-relevant first.
"""


def load_system_prompt(path: Path | None = None) -> str:
    return (path or PROMPT_PATH).read_text(encoding="utf-8").strip() + "\n" + OUTPUT_CONTRACT


def build_user_message(resume_text: str, jd_text: str) -> str:
    return (
        "## 1. MY CURRENT RESUME\n\n"
        f"{resume_text.strip()}\n\n"
        "## 2. TARGET JOB DESCRIPTION\n\n"
        f"{jd_text.strip()}\n\n"
        "Produce the optimized resume now, following the output contract exactly."
    )


def build_refinement_message(ats_score: float, missing: list[str], target: float) -> str:
    return (
        f"ATS check of your draft: {ats_score:.1f}% (target {target:.0f}%+).\n"
        f"Keywords from the JD still missing or not detectable: {', '.join(missing)}.\n"
        "Revise the resume so these terms appear naturally (skills, summary, bullets, projects) where truthful and "
        "relevant, keep employers/titles/dates/degrees unchanged, keep it within two pages, and return the FULL "
        "resume again following the output contract exactly."
    )


def strip_fences(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$", text, re.DOTALL)
    return match.group(1).strip() if match else text


class TailorSession:
    """A multi-turn conversation with Claude so refinement passes keep the original context."""

    def __init__(self, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT, system_prompt: str | None = None):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it (or add it as a Cloud Agent secret) to call Claude Opus 5.5."
            )
        from anthropic import Anthropic

        self.client = Anthropic()
        self.model = model
        self.effort = effort
        self.system_prompt = system_prompt or load_system_prompt()
        self.messages: list[dict] = []

    def _send(self, content: str, max_tokens: int = 8000) -> str:
        self.messages.append({"role": "user", "content": content})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=self.messages,
            output_config={"effort": self.effort},
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        self.messages.append({"role": "assistant", "content": text})
        return strip_fences(text)

    def tailor(self, resume_text: str, jd_text: str) -> str:
        return self._send(build_user_message(resume_text, jd_text))

    def refine(self, ats_score: float, missing: list[str], target: float) -> str:
        return self._send(build_refinement_message(ats_score, missing, target))
