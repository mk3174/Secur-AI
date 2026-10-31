import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from docx import Document

from resume_tailor.llm import OUTPUT_CONTRACT, TailorSession, build_user_message, load_system_prompt, strip_fences
from resume_tailor.render import markdown_to_text, render_docx

SAMPLE_MD = """# Jane Doe
Austin, TX | jane@example.com

## Professional Summary
Data Engineer building **ETL/ELT** pipelines.

## Skills
**Languages:** SQL, Python

## Experience
### Data Engineer | Acme Corp | Austin, TX | Jun 2023 - Present
- Built pipelines into Redshift.

## Education
### B.S. Computer Science | University of Texas | 2023
"""


class RenderTests(unittest.TestCase):
    def test_renders_single_column_docx_without_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = render_docx(SAMPLE_MD, Path(tmp) / "r.docx")
            doc = Document(str(out))
            texts = [p.text for p in doc.paragraphs]
            self.assertEqual(len(doc.tables), 0)
            self.assertEqual(texts[0], "Jane Doe")
            self.assertIn("PROFESSIONAL SUMMARY", texts)
            self.assertIn("Data Engineer, Acme Corp, Austin, TX\tJun 2023 - Present", texts)
            bullets = [p for p in doc.paragraphs if p.style.name == "List Bullet"]
            self.assertEqual(len(bullets), 1)
            summary = next(p for p in doc.paragraphs if p.text.startswith("Data Engineer building"))
            self.assertTrue(any(r.bold and r.text == "ETL/ELT" for r in summary.runs))

    def test_markdown_to_text_strips_markup(self):
        text = markdown_to_text(SAMPLE_MD)
        self.assertNotIn("**", text)
        self.assertNotIn("## ", text)


class LLMTests(unittest.TestCase):
    def test_strip_fences(self):
        self.assertEqual(strip_fences("```markdown\n# Hi\n```"), "# Hi")
        self.assertEqual(strip_fences("# Hi"), "# Hi")

    def test_system_prompt_includes_user_prompt_and_contract(self):
        prompt = load_system_prompt()
        self.assertIn("ATS score of 90%+", prompt)
        self.assertIn("Never invent", prompt)
        self.assertIn(OUTPUT_CONTRACT.strip(), prompt)

    def test_user_message_contains_both_inputs(self):
        msg = build_user_message("RESUME BODY", "JD BODY")
        self.assertIn("RESUME BODY", msg)
        self.assertIn("JD BODY", msg)

    def test_session_uses_opus_5_5_and_keeps_history(self):
        fake_response = SimpleNamespace(content=[SimpleNamespace(type="text", text="```markdown\n# Draft\n```")])
        fake_client = mock.MagicMock()
        fake_client.messages.create.return_value = fake_response
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}), mock.patch(
            "anthropic.Anthropic", return_value=fake_client
        ):
            session = TailorSession()
            draft = session.tailor("resume", "jd")
            session.refine(80.0, ["spark"], 90.0)
        self.assertEqual(draft, "# Draft")
        kwargs = fake_client.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-opus-5-5")
        self.assertEqual(kwargs["output_config"], {"effort": "high"})
        roles = [m["role"] for m in session.messages]
        self.assertEqual(roles, ["user", "assistant", "user", "assistant"])
        self.assertIn("spark", session.messages[2]["content"])


if __name__ == "__main__":
    unittest.main()
