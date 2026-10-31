"""Keyword extraction from a job description and ATS-style scoring of a resume against it."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

STOPWORDS = set(
    """
a about above across after again against all also although always am among an and any are around as at be because been
before being below between both but by can could did do does doing done down during each either else ever every few for
from further had has have having he her here hers herself him himself his how i if in into is it its itself just let may
me might more most much must my myself no nor not now of off on once one only or other ought our ours ourselves out over
own same shall she should so some such than that the their theirs them themselves then there these they this those through
to too under until up us very was we were what when where which while who whom why will with within without would you your
yours yourself yourselves etc eg ie via per using use used uses including include includes ability able across strong
excellent good great high highly well new ideal candidate role team teams work working opportunity environment years
experience experienced required requirements preferred qualifications basic key job responsibilities description
contribute contributing support supporting ensure understand understanding appropriate early career eager develop
business decisions make made solid willingness learn eye effectively cross functional teammates translate defined
domain alongside senior engineers engineer complex problems escalating partner stakeholders implement reliable
solutions products clearly document ease maintainability others participate discussions planning product
critical curate consume accelerate how build building test testing debug knowledge like basics designing implementing
vs one scripting language languages technologies such programs programs development deployment design
data tools foundations fire tv pipelines systems services workflows mechanisms issues trade offs owned own
""".split()
)

# Multi-word technical phrases recognised as a single keyword. Lower-case, longest-first matching.
TECH_PHRASES = [
    "self-service analytics",
    "conversational analytics",
    "agentic analytics",
    "ai-assisted development",
    "ai assisted analytics",
    "ai-enabled analytics",
    "data quality controls",
    "iam roles and permissions",
    "relational model",
    "dimensional model",
    "dimensional modeling",
    "data modeling",
    "data modelling",
    "data warehousing",
    "data warehouse",
    "data lake",
    "data lakehouse",
    "data pipelines",
    "data pipeline",
    "etl pipelines",
    "etl pipeline",
    "etl/elt",
    "elt/etl",
    "data quality",
    "data governance",
    "data infrastructure",
    "data products",
    "data engineering",
    "data science",
    "data scientist",
    "data analytics",
    "business intelligence",
    "executive reporting",
    "lifecycle analytics",
    "star schema",
    "snowflake schema",
    "slowly changing dimensions",
    "aws glue",
    "amazon redshift",
    "amazon s3",
    "aws lambda",
    "amazon emr",
    "amazon kinesis",
    "kinesis firehose",
    "kinesis data streams",
    "step functions",
    "lake formation",
    "apache spark",
    "apache airflow",
    "apache kafka",
    "apache hive",
    "apache hadoop",
    "apache flink",
    "apache iceberg",
    "delta lake",
    "machine learning",
    "deep learning",
    "natural language processing",
    "computer vision",
    "large language models",
    "large language model",
    "generative ai",
    "prompt engineering",
    "retrieval augmented generation",
    "vector database",
    "ci/cd",
    "continuous integration",
    "continuous delivery",
    "continuous deployment",
    "infrastructure as code",
    "unit testing",
    "integration testing",
    "code reviews",
    "code review",
    "design reviews",
    "on-call",
    "monitoring and alerting",
    "monitoring, alerting",
    "rest api",
    "rest apis",
    "restful apis",
    "microservices",
    "distributed systems",
    "version control",
    "power bi",
    "sql server",
    "google cloud",
    "google cloud platform",
    "big data",
    "schema design",
    "query optimization",
    "performance tuning",
    "stored procedures",
    "a/b testing",
    "experimentation",
    "privacy",
    "compliance",
    "retention",
    "governance",
    "normalization",
    "denormalization",
    "threat modeling",
    "penetration testing",
    "incident response",
    "vulnerability management",
    "identity and access management",
    "zero trust",
    "object-oriented programming",
    "agile",
    "scrum",
]

TECH_TERMS = set(
    """
sql nosql python java scala r go golang c c++ c# javascript typescript node node.js react angular vue django flask fastapi
spring kotlin swift rust ruby php perl bash shell powershell kornshell ksh linux unix windows
aws azure gcp redshift s3 glue emr kinesis firehose lambda iam athena dynamodb rds aurora ec2 ecs eks eventbridge sns sqs
cloudwatch cloudformation terraform ansible docker kubernetes k8s helm jenkins github gitlab bitbucket git
hadoop hive spark pyspark sparksql hiveql pl/sql plsql t-sql tsql ddl dml mdx hdfs mapreduce presto trino flink kafka
airflow dbt snowflake bigquery databricks synapse redshift fivetran stitch informatica talend ssis ssrs ssas
postgresql postgres mysql oracle mariadb sqlite mssql mongodb cassandra redis elasticsearch opensearch neo4j
tableau looker quicksight powerbi superset metabase excel pandas numpy scipy scikit-learn sklearn tensorflow pytorch keras
xgboost mlflow sagemaker bedrock openai anthropic claude langchain llamaindex rag llm llms genai agentic copilot cursor
etl elt olap oltp warehouse lakehouse parquet avro orc json xml csv yaml api apis grpc graphql rest
jira confluence agile scrum kanban ci/cd devops dataops mlops sre
iam oauth saml sso siem soc nist iso soc2 gdpr ccpa hipaa pci sox encryption tls
ai ml nlp cv bi dq sla slas kpi kpis
""".split()
)

# Equivalent surface forms that should count as a match for a given keyword.
SYNONYMS: dict[str, list[str]] = {
    "etl/elt": ["etl", "elt"],
    "elt/etl": ["etl", "elt"],
    "etl pipelines": ["etl pipeline", "etl"],
    "data pipelines": ["data pipeline", "pipelines"],
    "amazon redshift": ["redshift"],
    "aws glue": ["glue"],
    "amazon s3": ["s3"],
    "aws lambda": ["lambda"],
    "amazon emr": ["emr"],
    "amazon kinesis": ["kinesis"],
    "kinesis firehose": ["firehose"],
    "iam roles and permissions": ["iam"],
    "apache spark": ["spark", "pyspark"],
    "apache airflow": ["airflow"],
    "apache kafka": ["kafka"],
    "apache hive": ["hive"],
    "apache hadoop": ["hadoop"],
    "postgresql": ["postgres"],
    "ci/cd": ["ci cd", "cicd", "continuous integration", "continuous delivery"],
    "large language models": ["llm", "llms"],
    "large language model": ["llm", "llms"],
    "generative ai": ["genai", "gen ai"],
    "genai": ["generative ai", "gen ai"],
    "llm": ["large language model"],
    "llms": ["large language models"],
    "on-call": ["on call", "oncall"],
    "code reviews": ["code review"],
    "code review": ["code reviews"],
    "data modeling": ["data modelling", "data model", "data models"],
    "data warehousing": ["data warehouse", "warehouse"],
    "dimensional model": ["dimensional modeling", "star schema", "dimensional"],
    "relational model": ["relational", "normalized", "normalization", "3nf"],
    "self-service analytics": ["self service analytics", "self-service"],
    "ai-assisted development": ["ai assisted development", "ai-assisted", "copilot", "cursor"],
    "ai assisted analytics": ["ai-assisted analytics", "ai-assisted", "ai assisted"],
    "ai-enabled analytics": ["ai enabled analytics", "ai-enabled"],
    "data quality controls": ["data quality checks", "data quality"],
    "monitoring, alerting": ["monitoring", "alerting"],
    "business intelligence": ["bi"],
    "data science": ["data scientists", "data scientist"],
    "data engineering": ["data engineer"],
    "data products": ["data product"],
    "data infrastructure": ["infrastructure"],
    "experimentation": ["a/b testing", "a/b tests", "experiments"],
    "sparksql": ["spark sql"],
    "hiveql": ["hive ql", "hive"],
    "pl/sql": ["plsql"],
    "kornshell": ["ksh", "shell scripting", "bash"],
    "scripting language": ["python", "bash", "shell"],
    "machine learning": ["ml"],
    "sql": ["sql"],
}

ACRONYM = re.compile(r"\b[A-Z][A-Z0-9/+#.-]{1,7}\b")
TOKEN = re.compile(r"[a-z0-9][a-z0-9+#./-]*[a-z0-9+#]|[a-z0-9]", re.IGNORECASE)
YEARS_REQUIRED = re.compile(r"(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years|yrs)", re.IGNORECASE)

MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
DATE_RANGE = re.compile(
    rf"(?:(?:{MONTHS})[a-z]*\.?\s+)?(\d{{4}})\s*(?:-|–|—|to|through)\s*"
    rf"(?:(?:(?:{MONTHS})[a-z]*\.?\s+)?(\d{{4}})|(present|current|now|today))",
    re.IGNORECASE,
)


@dataclass
class Keyword:
    term: str
    weight: float
    count: int = 1

    @property
    def importance(self) -> float:
        return self.weight * (1.0 + math.log(self.count))


@dataclass
class ScoreReport:
    ats_score: float
    keyword_score: float
    experience_fit: float
    resume_years: float | None
    required_years: int | None
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"ATS score: {self.ats_score:.1f}%  (keywords {self.keyword_score:.1f}%, experience fit {self.experience_fit:.0f}%)",
        ]
        if self.required_years is not None:
            yrs = f"{self.resume_years:.1f}" if self.resume_years is not None else "unknown"
            lines.append(f"Experience: JD asks {self.required_years}+ yrs, resume shows ~{yrs} yrs")
        lines.append(f"Matched ({len(self.matched)}): {', '.join(self.matched)}")
        lines.append(f"Missing ({len(self.missing)}): {', '.join(self.missing)}")
        return "\n".join(lines)


def _normalize(text: str) -> str:
    text = text.lower().replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"\s+", " ", text)
    return text


def extract_keywords(jd_text: str, limit: int = 70) -> list[Keyword]:
    """Pull the terms an ATS is most likely to screen for, weighted by technical specificity."""
    original = jd_text
    text = _normalize(jd_text)
    counts: dict[str, Keyword] = {}

    def bump(term: str, weight: float) -> None:
        if term in counts:
            counts[term].count += 1
            counts[term].weight = max(counts[term].weight, weight)
        else:
            counts[term] = Keyword(term=term, weight=weight)

    consumed = text
    for phrase in sorted(TECH_PHRASES, key=len, reverse=True):
        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])")
        hits = pattern.findall(consumed)
        if hits:
            for _ in hits:
                bump(phrase, 3.0)
            consumed = pattern.sub(" ", consumed)

    acronyms = {m.lower() for m in ACRONYM.findall(original)}

    tokens = [t.lower().strip(".") for t in TOKEN.findall(consumed)]
    for tok in tokens:
        if tok in TECH_TERMS:
            bump(tok, 3.0)
        elif tok in acronyms and tok not in STOPWORDS and len(tok) >= 2:
            bump(tok, 2.0)

    generic: dict[str, int] = {}
    for tok in tokens:
        if tok in TECH_TERMS or tok in STOPWORDS or len(tok) < 4 or tok.isdigit():
            continue
        generic[tok] = generic.get(tok, 0) + 1
    for tok, n in generic.items():
        if n >= 2:
            counts.setdefault(tok, Keyword(term=tok, weight=1.0, count=n))

    for a, b in zip(tokens, tokens[1:]):
        if a in STOPWORDS or b in STOPWORDS or len(a) < 3 or len(b) < 3:
            continue
        if a.isdigit() or b.isdigit():
            continue
        bigram = f"{a} {b}"
        if bigram in counts or any(bigram in p for p in counts):
            continue
        n = len(re.findall(re.escape(bigram), consumed))
        if n >= 2:
            counts[bigram] = Keyword(term=bigram, weight=1.5, count=n)

    ranked = sorted(counts.values(), key=lambda k: k.importance, reverse=True)
    return ranked[:limit]


_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _term_pattern(term: str) -> re.Pattern[str]:
    """Word-boundary regex tolerant of space/hyphen/slash variation ("on-call" ~ "on call", "etl/elt" ~ "etl elt")."""
    cached = _PATTERN_CACHE.get(term)
    if cached:
        return cached
    pieces = [re.escape(p) for p in re.split(r"[\s\-/]+", term.strip()) if p]
    body = r"[\s\-/]*".join(pieces)
    pattern = re.compile(r"(?<![a-z0-9])" + body + r"(?:s|es|ing|ed)?(?![a-z0-9])")
    _PATTERN_CACHE[term] = pattern
    return pattern


def keyword_present(term: str, resume_norm: str) -> bool:
    if _term_pattern(term).search(resume_norm):
        return True
    return any(_term_pattern(s).search(resume_norm) for s in SYNONYMS.get(term, []))


def resume_years(resume_text: str) -> float | None:
    """Estimate total years of experience from date ranges, merging overlaps."""
    from datetime import date

    now_year = date.today().year
    intervals: list[tuple[int, int]] = []
    for start, end, present in DATE_RANGE.findall(resume_text):
        s = int(start)
        e = now_year if present else int(end)
        if 1980 <= s <= now_year and s <= e <= now_year + 1:
            intervals.append((s, e))
    if not intervals:
        return None
    intervals.sort()
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    total = sum(max(e - s, 0.5) for s, e in merged)
    return round(total, 1)


def required_years(jd_text: str) -> int | None:
    values = [int(m) for m in YEARS_REQUIRED.findall(jd_text)]
    return min(values) if values else None


def score_resume(resume_text: str, jd_text: str, keywords: list[Keyword] | None = None) -> ScoreReport:
    keywords = keywords or extract_keywords(jd_text)
    resume_norm = _normalize(resume_text)

    total = sum(k.importance for k in keywords) or 1.0
    matched, missing = [], []
    hit_weight = 0.0
    for kw in keywords:
        if keyword_present(kw.term, resume_norm):
            matched.append(kw.term)
            hit_weight += kw.importance
        else:
            missing.append(kw.term)
    keyword_score = 100.0 * hit_weight / total

    req = required_years(jd_text)
    yrs = resume_years(resume_text)
    if req is None:
        experience_fit = 100.0
    elif yrs is None:
        experience_fit = 50.0
    else:
        experience_fit = 100.0 * min(1.0, yrs / req)

    ats = 0.85 * keyword_score + 0.15 * experience_fit
    return ScoreReport(
        ats_score=round(ats, 1),
        keyword_score=round(keyword_score, 1),
        experience_fit=round(experience_fit, 1),
        resume_years=yrs,
        required_years=req,
        matched=matched,
        missing=missing,
    )
