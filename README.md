# Secur-AI — Resume Tailor

Tailor a resume to any job description (JD) with one command. The tool:

1. Scans your **Downloads** folder (and `resumes/`) for resumes (`.docx`, `.pdf`, `.md`, `.txt`).
2. **Ranks** them by ATS fit against the JD (weighted keyword coverage + years-of-experience fit).
3. Sends the best one, the JD, and the saved **system prompt** (`prompts/system_prompt.md`) to **Claude Opus 5.5**.
4. Re-scores the draft and runs refinement passes until the ATS score is **90%+**.
5. Writes an ATS-friendly **Word (.docx)** resume plus a Markdown copy and a before/after ATS report.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...        # Cloud Agents: add it under Cursor Dashboard > Cloud Agents > Secrets
```

## Usage

```bash
# Save the JD (any text file works; jobs/ keeps a history)
cat > jobs/fire-tv-data-engineer.md

# See which resume in ~/Downloads matches best
python -m resume_tailor rank --jd jobs/fire-tv-data-engineer.md

# Pick the best resume and tailor it
python -m resume_tailor tailor --jd jobs/fire-tv-data-engineer.md
#   -> output/<slug>/tailored_resume.docx, tailored_resume.md, ats_report.txt

# Use a specific resume / folder / output name
python -m resume_tailor tailor --jd jobs/role.md --resume ~/Downloads/MyResume.docx --name fire-tv-de
python -m resume_tailor tailor --jd jobs/role.md --resumes-dir ~/Documents/Resumes --recursive

# Score any resume against a JD, or render Markdown to .docx
python -m resume_tailor score  --jd jobs/role.md --resume output/fire-tv-de/tailored_resume.md
python -m resume_tailor render output/fire-tv-de/tailored_resume.md
```

Options for `tailor`: `--model` (default `claude-opus-5-5`), `--effort low|medium|high|xhigh|max` (default `high`),
`--min-score` (default 90), `--max-passes` (default 3), `--dry-run` (select and score only).

## Using it from Cursor chat

Paste a JD and say "tailor my resume to this". The repo ships a rule (`.cursor/rules/resume-tailor.mdc`) and a skill
(`.cursor/skills/resume-tailor/SKILL.md`) that make the agent follow this exact workflow every time, always with
Claude Opus 5.5 and the saved system prompt. In a Cloud Agent run your local Downloads folder is not available, so
attach the resume in chat or commit it to `resumes/`.

## Layout

```
prompts/system_prompt.md       The ATS resume-writer system prompt (kept verbatim)
jobs/                          Saved job descriptions
resume_tailor/                 discover.py (find resumes) · scoring.py (ATS score) · llm.py (Claude Opus 5.5)
                               render.py (Markdown -> ATS-friendly .docx) · cli.py
tests/                         python -m unittest discover -s tests
```

## Truthfulness

The system prompt allows rewriting bullets and adding realistic portfolio projects, but never invents employers,
job titles, dates, or degrees. Review the output before sending it anywhere.
