import unittest
from pathlib import Path

from resume_tailor.scoring import extract_keywords, keyword_present, required_years, resume_years, score_resume

JD = (Path(__file__).resolve().parent.parent / "jobs" / "fire-tv-data-engineer.md").read_text(encoding="utf-8")


class KeywordExtractionTests(unittest.TestCase):
    def test_extracts_core_jd_terms(self):
        terms = {k.term for k in extract_keywords(JD)}
        for expected in ["sql", "python", "redshift", "aws glue", "data modeling", "etl/elt", "data quality", "on-call"]:
            self.assertIn(expected, terms)

    def test_generic_words_are_filtered(self):
        terms = {k.term for k in extract_keywords(JD)}
        for noise in ["data", "experience", "team", "the", "tv"]:
            self.assertNotIn(noise, terms)

    def test_tech_terms_outrank_generic_words(self):
        ranked = extract_keywords(JD)
        self.assertEqual(ranked[0].weight, 3.0)


class KeywordMatchingTests(unittest.TestCase):
    def test_hyphen_space_and_slash_variants(self):
        self.assertTrue(keyword_present("on-call", "participated in on call rotation"))
        self.assertTrue(keyword_present("etl/elt", "built etl elt pipelines"))
        self.assertTrue(keyword_present("data quality", "owned data-quality controls"))

    def test_plural_and_synonyms(self):
        self.assertTrue(keyword_present("data pipelines", "built a data pipeline"))
        self.assertTrue(keyword_present("amazon redshift", "loaded into redshift"))
        self.assertTrue(keyword_present("large language models", "fine-tuned llms"))

    def test_no_partial_word_matches(self):
        self.assertFalse(keyword_present("r", "rust developer"))
        self.assertFalse(keyword_present("hive", "archived files"))


class ExperienceTests(unittest.TestCase):
    def test_required_years(self):
        self.assertEqual(required_years(JD), 1)
        self.assertIsNone(required_years("No requirement listed"))

    def test_resume_years_merges_overlaps(self):
        text = "Engineer | Acme | Jan 2020 - Dec 2022\nLead | Beta | 2022 – Present\nIntern | 2018 to 2018"
        self.assertGreaterEqual(resume_years(text), 6.0)


class ScoreTests(unittest.TestCase):
    def test_weak_resume_scores_low_and_strong_resume_scores_high(self):
        weak = "Frontend developer. React, CSS, Figma. 2021 - 2023. Education: BS 2021. Skills: TypeScript"
        strong = (
            "Data Engineer 2023 - Present. Built ETL/ELT data pipelines in SQL and Python on AWS (Redshift, S3, AWS Glue, "
            "EMR, Kinesis, Firehose, Lambda, IAM roles and permissions). Data modeling: dimensional model, relational model, "
            "normalization, data warehouse, data lake. Data quality controls, monitoring, alerting, on-call. Spark, Hadoop, "
            "Hive, HiveQL, SparkSQL, PL/SQL, DDL, MDX, Scala, KornShell. Privacy, compliance, retention, data governance. "
            "Business Intelligence, Data Science, experimentation, executive reporting, lifecycle analytics, GenAI, agentic "
            "analytics, self-service analytics, AI-assisted development, AI assisted analytics, AI-enabled analytics, "
            "code reviews, datasets, data products, data infrastructure, big data."
        )
        self.assertLess(score_resume(weak, JD).ats_score, 30)
        self.assertGreaterEqual(score_resume(strong, JD).ats_score, 90)


if __name__ == "__main__":
    unittest.main()
