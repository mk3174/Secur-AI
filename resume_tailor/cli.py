"""Command-line interface.

    python -m resume_tailor rank   --jd jobs/role.md [--resumes-dir ~/Downloads]
    python -m resume_tailor tailor --jd jobs/role.md [--resume path] [--out output/]
    python -m resume_tailor score  --jd jobs/role.md --resume path
    python -m resume_tailor render draft.md --out tailored.docx
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import DEFAULT_EFFORT, DEFAULT_MODEL, TARGET_ATS_SCORE
from .discover import Candidate, default_resume_dirs, find_candidates
from .extract import extract_text
from .render import markdown_to_text, render_docx
from .scoring import extract_keywords, score_resume


def _read_jd(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    path = Path(value).expanduser()
    if path.is_file():
        return extract_text(path) if path.suffix.lower() in {".docx", ".pdf"} else path.read_text(encoding="utf-8")
    return value  # raw JD text passed inline


def _slug(text: str, fallback: str = "job") -> str:
    first = next((ln for ln in text.splitlines() if ln.strip()), fallback)
    slug = re.sub(r"[^a-z0-9]+", "-", first.lower()).strip("-")[:48]
    return slug or fallback


def _rank(candidates: list[Candidate], jd_text: str) -> list[tuple[Candidate, float]]:
    keywords = extract_keywords(jd_text)
    ranked = []
    for cand in candidates:
        report = score_resume(cand.text, jd_text, keywords)
        bonus = 2.0 if cand.name_matches else 0.0
        ranked.append((cand, report.ats_score + bonus, report))
    ranked.sort(key=lambda r: r[1], reverse=True)
    return ranked


def _print_ranking(ranked) -> None:
    print("\nResume candidates ranked against the JD:")
    for i, (cand, composite, report) in enumerate(ranked, 1):
        yrs = f"{report.resume_years:.1f}y" if report.resume_years is not None else "?y"
        print(f"  {i:>2}. {composite:5.1f}  kw={report.keyword_score:5.1f}%  exp={yrs:>5}  {cand.path}")


def cmd_rank(args) -> int:
    jd_text = _read_jd(args.jd)
    dirs = [Path(d) for d in args.resumes_dir] if args.resumes_dir else default_resume_dirs()
    candidates = find_candidates(dirs, recursive=args.recursive, include_all=args.all)
    if not candidates:
        print(f"No resume files found in: {', '.join(str(d) for d in dirs)}", file=sys.stderr)
        return 2
    ranked = _rank(candidates, jd_text)
    _print_ranking(ranked)
    best = ranked[0]
    print(f"\nBest match: {best[0].path}\n")
    print(best[2].summary())
    return 0


def cmd_score(args) -> int:
    jd_text = _read_jd(args.jd)
    resume_path = Path(args.resume).expanduser()
    resume_text = extract_text(resume_path)
    if resume_path.suffix.lower() == ".md":
        resume_text = markdown_to_text(resume_text)
    report = score_resume(resume_text, jd_text)
    print(report.summary())
    return 0 if report.ats_score >= args.min_score else 1


def cmd_render(args) -> int:
    markdown = Path(args.markdown).read_text(encoding="utf-8")
    out = Path(args.out) if args.out else Path(args.markdown).with_suffix(".docx")
    render_docx(markdown, out)
    print(f"Wrote {out}")
    return 0


def cmd_tailor(args) -> int:
    jd_text = _read_jd(args.jd)
    keywords = extract_keywords(jd_text)

    if args.resume:
        resume_path = Path(args.resume).expanduser()
        resume_text = extract_text(resume_path)
        print(f"Using resume: {resume_path}")
    else:
        dirs = [Path(d) for d in args.resumes_dir] if args.resumes_dir else default_resume_dirs()
        candidates = find_candidates(dirs, recursive=args.recursive, include_all=args.all)
        if not candidates:
            print(f"No resume files found in: {', '.join(str(d) for d in dirs)}", file=sys.stderr)
            return 2
        ranked = _rank(candidates, jd_text)
        _print_ranking(ranked)
        resume_path, resume_text = ranked[0][0].path, ranked[0][0].text
        print(f"\nSelected: {resume_path}")

    baseline = score_resume(resume_text, jd_text, keywords)
    print(f"\nBaseline {baseline.summary()}\n")

    slug = args.name or _slug(jd_text)
    out_dir = Path(args.out).expanduser() / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "job_description.md").write_text(jd_text, encoding="utf-8")
    (out_dir / "source_resume.txt").write_text(resume_text, encoding="utf-8")

    if args.dry_run:
        print(f"Dry run: inputs saved to {out_dir}. No model call made.")
        return 0

    from .llm import TailorSession

    session = TailorSession(model=args.model, effort=args.effort)
    print(f"Tailoring with {args.model} (effort={args.effort})...")
    draft = session.tailor(resume_text, jd_text)
    report = score_resume(markdown_to_text(draft), jd_text, keywords)
    print(f"Pass 1 -> ATS {report.ats_score:.1f}%")

    passes = 1
    while report.ats_score < args.min_score and passes < args.max_passes:
        passes += 1
        print(f"Below {args.min_score:.0f}%; refining (missing: {', '.join(report.missing[:12])}...)")
        draft = session.refine(report.ats_score, report.missing, args.min_score)
        report = score_resume(markdown_to_text(draft), jd_text, keywords)
        print(f"Pass {passes} -> ATS {report.ats_score:.1f}%")

    md_path = out_dir / "tailored_resume.md"
    docx_path = out_dir / "tailored_resume.docx"
    md_path.write_text(draft, encoding="utf-8")
    render_docx(draft, docx_path)
    (out_dir / "ats_report.txt").write_text(
        f"Source resume: {resume_path}\nModel: {args.model} (effort={args.effort}), passes={passes}\n\n"
        f"BEFORE\n{baseline.summary()}\n\nAFTER\n{report.summary()}\n",
        encoding="utf-8",
    )

    print(f"\nFinal {report.summary()}")
    print(f"\nWrote:\n  {docx_path}\n  {md_path}\n  {out_dir / 'ats_report.txt'}")
    return 0 if report.ats_score >= args.min_score else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resume_tailor", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_discovery(p):
        p.add_argument("--resumes-dir", action="append", help="Folder(s) to scan (default: ~/Downloads and ./resumes)")
        p.add_argument("--recursive", action="store_true", help="Scan sub-folders too")
        p.add_argument("--all", action="store_true", help="Consider every docx/pdf/md/txt, not just resume-looking files")

    p_rank = sub.add_parser("rank", help="Rank resumes in a folder against a JD")
    p_rank.add_argument("--jd", required=True, help="JD file path, '-' for stdin, or inline text")
    add_discovery(p_rank)
    p_rank.set_defaults(func=cmd_rank)

    p_score = sub.add_parser("score", help="ATS-score one resume against a JD")
    p_score.add_argument("--jd", required=True)
    p_score.add_argument("--resume", required=True)
    p_score.add_argument("--min-score", type=float, default=TARGET_ATS_SCORE)
    p_score.set_defaults(func=cmd_score)

    p_render = sub.add_parser("render", help="Render a Markdown resume to an ATS-friendly .docx")
    p_render.add_argument("markdown")
    p_render.add_argument("--out")
    p_render.set_defaults(func=cmd_render)

    p_tailor = sub.add_parser("tailor", help="Pick the best resume and tailor it to the JD with Claude Opus 5.5")
    p_tailor.add_argument("--jd", required=True, help="JD file path, '-' for stdin, or inline text")
    p_tailor.add_argument("--resume", help="Skip discovery and use this resume file")
    add_discovery(p_tailor)
    p_tailor.add_argument("--out", default="output", help="Output root folder (default: ./output)")
    p_tailor.add_argument("--name", help="Sub-folder name for this job (default: derived from the JD)")
    p_tailor.add_argument("--model", default=DEFAULT_MODEL)
    p_tailor.add_argument("--effort", default=DEFAULT_EFFORT, choices=["low", "medium", "high", "xhigh", "max"])
    p_tailor.add_argument("--min-score", type=float, default=TARGET_ATS_SCORE)
    p_tailor.add_argument("--max-passes", type=int, default=3, help="Refinement passes until min-score is reached")
    p_tailor.add_argument("--dry-run", action="store_true", help="Select + score only; do not call the model")
    p_tailor.set_defaults(func=cmd_tailor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
