---
name: resume-tailor
description: Tailor/trim a resume to a pasted job description (JD) using the saved ATS system prompt and Claude Opus 5.5. Use whenever the user pastes a JD, says "tailor/trim/optimize my resume", "update resume to this JD", or asks for an ATS-optimized resume.
---

# Resume Tailor workflow

The system prompt that governs every rewrite lives in `prompts/system_prompt.md`. Do not paraphrase it; load it verbatim.
The model for the rewrite is always **Claude Opus 5.5** (`claude-opus-5-5` on the Claude API; `claude-opus-5-5-high` as a Cursor subagent model).

## Steps

1. **Save the JD.** Write the pasted JD to `jobs/<company-role-slug>.md` (plain text, no edits).

2. **Find the best source resume.** Scan the user's Downloads folder (and `./resumes/`) and rank every resume by ATS fit against the JD:

   ```bash
   pip install -r requirements.txt
   python -m resume_tailor rank --jd jobs/<slug>.md --resumes-dir ~/Downloads --resumes-dir resumes
   ```

   Pick the top-ranked file. If the user attached a resume or named one, use that instead (`--resume path`).
   In a Cloud Agent VM `~/Downloads` is not mounted; look for attached files, files in `resumes/`, or ask the user to attach / commit one. Never fabricate a source resume.

3. **Tailor with Claude Opus 5.5.** Prefer the CLI (needs `ANTHROPIC_API_KEY`):

   ```bash
   python -m resume_tailor tailor --jd jobs/<slug>.md --resumes-dir ~/Downloads --out output
   # or: --resume path/to/resume.docx
   ```

   It selects the resume, scores the baseline, calls `claude-opus-5-5`, re-scores the draft, runs refinement passes until the ATS score is >= 90% (max 3), and writes `output/<slug>/tailored_resume.docx`, `tailored_resume.md`, and `ats_report.txt`.

   **If `ANTHROPIC_API_KEY` is not available**, do the model step via a Cursor subagent instead: launch a `generalPurpose` Task with model `claude-opus-5-5-high`, whose prompt is the full text of `prompts/system_prompt.md` plus the `OUTPUT CONTRACT` from `resume_tailor/llm.py`, followed by the extracted resume text and the JD. Save the returned Markdown to `output/<slug>/tailored_resume.md`, then:

   ```bash
   python -m resume_tailor score  --jd jobs/<slug>.md --resume output/<slug>/tailored_resume.md
   python -m resume_tailor render output/<slug>/tailored_resume.md --out output/<slug>/tailored_resume.docx
   ```

   If the score is below 90%, feed the `Missing (...)` list back to the same subagent and ask for a revision that naturally includes those terms; re-score and re-render.

4. **Verify before delivering.** Confirm: no invented employers/titles/dates/degrees versus the source resume; two pages or fewer (~600-850 words); no tables/columns/graphics; ATS score >= 90%. Report before/after scores and the remaining missing keywords.

5. **Deliver** the `.docx` (copy to the artifacts folder in a Cloud Agent run) and summarize the key changes.

## Guardrails
- Keep employers, job titles, date ranges, and degrees exactly as in the source resume.
- Bullets may be rewritten/fabricated to match JD responsibilities (per the system prompt), but keep them realistic and interview-defensible.
- Keep the output ATS-friendly: single column, standard headings, plain bullets.
