"""Locate resume candidates on disk (default: ~/Downloads)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .extract import SUPPORTED_EXTENSIONS, extract_text

MAX_FILE_BYTES = 8 * 1024 * 1024
NAME_HINT = re.compile(r"(resume|cv|curriculum)", re.IGNORECASE)
SECTION_HINTS = (
    "experience",
    "education",
    "skills",
    "summary",
    "projects",
    "work history",
    "employment",
)


@dataclass
class Candidate:
    path: Path
    text: str

    @property
    def name_matches(self) -> bool:
        return bool(NAME_HINT.search(self.path.stem))


def default_resume_dirs() -> list[Path]:
    env = os.environ.get("RESUME_DIRS")
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p.strip()]
    dirs = [Path.home() / "Downloads", Path.cwd() / "resumes"]
    return dirs


def looks_like_resume(text: str) -> bool:
    lowered = text.lower()
    hits = sum(1 for hint in SECTION_HINTS if hint in lowered)
    return hits >= 2 and 150 <= len(lowered) <= 60_000


def find_candidates(dirs: list[Path], recursive: bool = False, include_all: bool = False) -> list[Candidate]:
    seen: set[Path] = set()
    found: list[Candidate] = []
    for directory in dirs:
        directory = directory.expanduser()
        if not directory.is_dir():
            continue
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        for path in sorted(iterator):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if path.name.startswith(("~$", ".")) or path.stat().st_size > MAX_FILE_BYTES:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                text = extract_text(path)
            except Exception:  # unreadable/corrupt file; skip rather than abort discovery
                continue
            if include_all or NAME_HINT.search(path.stem) or looks_like_resume(text):
                found.append(Candidate(path=path, text=text))
    return found
