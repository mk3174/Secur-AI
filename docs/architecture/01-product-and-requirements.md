# SecurAI — Part 1: Product & Requirements

> Software Architecture Document (SAD) — Sections 1–6
> Covers: Executive Summary, Product Vision, Functional Requirements, Non‑Functional Requirements, User Personas, User Stories.

---

## 1. Executive Summary

**SecurAI** is an enterprise **AI Gateway + LLMOps + AgentOps + AI Security** platform. It gives organizations a single, governed control plane in front of every Large Language Model (LLM) and AI agent they run — whether those models are open‑source (Llama, Gemma, Qwen, Mistral, Phi), fine‑tuned in‑house, or hosted by external providers (OpenAI, Anthropic).

The platform solves the operational and safety problems that emerge once a company runs more than one or two AI applications: prompt injection and jailbreaks, hallucinations, uncontrolled cost, lack of observability, inconsistent model routing, fragmented provider integrations, GPU scarcity, and the absence of a managed model/fine‑tuning lifecycle.

### What it delivers

| Capability | Outcome |
|---|---|
| **Unified Gateway** | One OpenAI‑compatible API + key management, authn/z, rate limits, caching, streaming, logging. |
| **Prompt Firewall** | Inbound/outbound guardrails: injection/jailbreak/PII/secret detection, moderation, policy enforcement. |
| **LLM Router** | Cost/latency/quality/task/GPU‑aware routing with automatic fallback across providers and self‑hosted models. |
| **Model Registry** | Versioned models, metrics, tags, lineage, deployment & evaluation history, artifacts. |
| **Fine‑Tuning Pipeline** | Dataset curation → LoRA/QLoRA training → evaluation → registry → deployment. |
| **Evaluation System** | Offline benchmarks, hallucination/faithfulness/context metrics, A/B testing, human feedback. |
| **Observability** | Prometheus/Grafana metrics, OpenTelemetry traces, Langfuse LLM traces, MLflow experiments, structured logs, alerts. |
| **Dashboard** | Org/project/model/agent/deployment/cost/security visibility and administration. |
| **Multi‑Agent System** | Planner, Research, Coding, Security, Documentation, Evaluation, Monitoring agents. |

### Architectural stance

SecurAI is built as a **microservice‑ready modular monolith**. A single deployable Python (FastAPI) application is internally partitioned into bounded contexts (modules) with strict dependency rules and an internal event bus. GPU‑bound and infrastructure‑heavy concerns (model serving via vLLM, training jobs, async workers) run as **separate processes/services from day one**, because their scaling and lifecycle differ fundamentally from the control plane. This keeps the system **buildable by one engineer in phases** while preserving a clean path to full microservice extraction later.

### Realism assessment (one‑engineer feasibility)

The full feature set is **not** buildable at once by a single engineer. The design therefore prioritizes a **phased roadmap** (see Part 7) where each phase is independently demoable and production‑deployable:

1. **MVP** — secure gateway + one local vLLM model + auth + logging + dashboard + Docker.
2. **Intelligent routing** — multi‑model, rule‑based routing, cost/latency, retries, Redis cache.
3. **AI safety** — prompt firewall, PII masking, moderation, guardrails, audit logs.
4. **Evaluation & observability** — eval pipelines, hallucination detection, feedback, MLflow, Langfuse, Grafana.
5. **Fine‑tuning & deployment** — dataset curation, LoRA/QLoRA, registry, automated deploy, Kubernetes, CI/CD.

Each module is designed so it can later be extracted into its own microservice with minimal refactoring, by keeping module boundaries explicit and communication contract‑first.

---

## 2. Product Vision

### 2.1 Vision statement

> *"Make it as safe, observable, and cost‑efficient to run AI in production as it is to run a database — through one gateway that any team can adopt in an afternoon."*

### 2.2 Positioning

SecurAI sits at the intersection of three product categories that enterprises currently buy separately:

- **AI Gateway / LLM proxy** (routing, keys, caching, fallback).
- **LLM/Agent Observability** (traces, evals, cost analytics).
- **AI Security / Guardrails** (prompt firewall, PII, policy).

By unifying them, SecurAI becomes the **system of record for AI usage** in an organization: every prompt, completion, cost unit, safety decision, and evaluation flows through it.

### 2.3 Target customers

- Mid‑to‑large enterprises with **multiple AI applications** and compliance obligations (finance, healthcare, SaaS).
- Platform/ML‑platform teams who must offer **AI as an internal service** to product teams.
- Regulated organizations needing **auditability, data‑residency, and PII controls**.

### 2.4 Product principles

1. **Drop‑in compatibility** — expose an OpenAI‑compatible API so existing SDKs work with a base‑URL change.
2. **Safe by default** — guardrails on by default with sane policies; teams opt *out*, not *in*.
3. **Everything is observable** — no silent failures; every decision is traceable and attributable to an org/project/key.
4. **Cost is a first‑class metric** — every request carries token and cost accounting.
5. **Open‑model first** — self‑hosted models are first‑class citizens, not an afterthought.
6. **Extensible** — providers, guardrails, routers, evaluators, and agents are plugins behind stable interfaces.

### 2.5 Success metrics (product KPIs)

| KPI | Target |
|---|---|
| Gateway p99 added latency (excl. model time) | < 50 ms |
| Guardrail false‑positive rate | < 2% |
| Cost attribution coverage | 100% of requests |
| Cache hit rate (eligible traffic) | > 25% |
| Mean time to detect a security incident | < 1 min |
| Time‑to‑first‑request for a new team | < 30 min |

---

## 3. Functional Requirements

Requirements use **MoSCoW** prioritization and are mapped to the phase in which they land.

### 3.1 AI Gateway (FR‑GW)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑GW‑01 | Expose OpenAI‑compatible `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`. | Must | 1 |
| FR‑GW‑02 | Authenticate requests via API keys (hashed at rest) and dashboard via OIDC/JWT. | Must | 1 |
| FR‑GW‑03 | Authorize by org/project scope and role (RBAC). | Must | 1 |
| FR‑GW‑04 | Per‑key / per‑project rate limiting and quotas (token + request based). | Must | 1/2 |
| FR‑GW‑05 | Validate and normalize requests against provider‑agnostic schema. | Must | 1 |
| FR‑GW‑06 | Stream responses via SSE; support non‑streaming. | Must | 1 |
| FR‑GW‑07 | Structured request/response logging with redaction. | Must | 1 |
| FR‑GW‑08 | Response caching (semantic + exact) with TTL and bypass controls. | Should | 2 |
| FR‑GW‑09 | Idempotency keys and request retries with backoff. | Should | 2 |

### 3.2 Prompt Firewall (FR‑FW)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑FW‑01 | Detect prompt injection on inbound prompts. | Must | 3 |
| FR‑FW‑02 | Detect jailbreak attempts. | Must | 3 |
| FR‑FW‑03 | Detect & mask PII (configurable entities). | Must | 3 |
| FR‑FW‑04 | Detect secrets/credentials in prompts. | Must | 3 |
| FR‑FW‑05 | Content moderation (categories: hate, sexual, violence, self‑harm). | Must | 3 |
| FR‑FW‑06 | Policy engine: allow / block / mask / redact / require‑approval per org/project. | Must | 3 |
| FR‑FW‑07 | Output validation (PII leak, schema, toxicity) on responses. | Must | 3 |
| FR‑FW‑08 | Immutable security audit log of every decision. | Must | 3 |

### 3.3 LLM Router (FR‑RT)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑RT‑01 | Register model providers: vLLM (self‑host), OpenAI, Anthropic; pluggable adapters. | Must | 1/2 |
| FR‑RT‑02 | Support self‑hosted Llama, Gemma, Qwen, Mistral, Phi via vLLM. | Must | 1/2 |
| FR‑RT‑03 | Routing strategies: latency, cost, quality, task‑specific, GPU‑availability. | Must | 2 |
| FR‑RT‑04 | Automatic fallback chains on error/timeout/capacity. | Must | 2 |
| FR‑RT‑05 | Weighted / canary routing for rollout and A/B. | Should | 4 |
| FR‑RT‑06 | Health checks and circuit breaking per backend. | Must | 2 |

### 3.4 Model Registry (FR‑MR)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑MR‑01 | Register model + version with immutable metadata. | Must | 5 |
| FR‑MR‑02 | Store metrics, tags, training & deployment history, eval reports. | Must | 5 |
| FR‑MR‑03 | Track lineage (dataset → run → model → deployment). | Must | 5 |
| FR‑MR‑04 | Store/reference artifacts (adapters, configs) in object storage. | Must | 5 |
| FR‑MR‑05 | Lifecycle stages: staging → production → archived. | Must | 5 |

### 3.5 Fine‑Tuning Pipeline (FR‑FT)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑FT‑01 | Dataset ingestion, cleaning, deduplication, validation. | Must | 5 |
| FR‑FT‑02 | LoRA and QLoRA training jobs on GPU workers. | Must | 5 |
| FR‑FT‑03 | Track runs in MLflow with params/metrics/artifacts. | Must | 5 |
| FR‑FT‑04 | Post‑training evaluation gate before promotion. | Must | 5 |
| FR‑FT‑05 | Promote adapter to registry and deploy to vLLM. | Must | 5 |

### 3.6 Evaluation System (FR‑EV)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑EV‑01 | Offline benchmark runs against datasets. | Must | 4 |
| FR‑EV‑02 | Metrics: latency, accuracy, hallucination, faithfulness, context precision/recall, token usage, cost. | Must | 4 |
| FR‑EV‑03 | A/B testing across models/prompts. | Should | 4 |
| FR‑EV‑04 | Human feedback collection (thumbs, ratings, annotations). | Must | 4 |
| FR‑EV‑05 | Eval reports linked to model versions in registry. | Must | 4/5 |

### 3.7 Observability (FR‑OB)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑OB‑01 | Prometheus metrics for gateway, router, firewall, workers. | Must | 1/4 |
| FR‑OB‑02 | OpenTelemetry distributed tracing across services. | Must | 4 |
| FR‑OB‑03 | Langfuse LLM tracing (prompt/response/cost/latency). | Must | 4 |
| FR‑OB‑04 | MLflow experiment tracking. | Must | 4/5 |
| FR‑OB‑05 | Grafana dashboards + alerting rules. | Must | 4 |
| FR‑OB‑06 | Centralized structured logs with correlation IDs. | Must | 1 |

### 3.8 Dashboard (FR‑DB)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑DB‑01 | Manage users, orgs, projects, API keys. | Must | 1 |
| FR‑DB‑02 | View models, agents, deployments. | Must | 1/2 |
| FR‑DB‑03 | Cost, token, latency, request analytics. | Must | 2/4 |
| FR‑DB‑04 | GPU usage and capacity views. | Should | 5 |
| FR‑DB‑05 | Security incident console (firewall decisions, audits). | Must | 3 |
| FR‑DB‑06 | Evaluation results and A/B comparisons. | Must | 4 |

### 3.9 Multi‑Agent System (FR‑AG)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑AG‑01 | Agent runtime with tool use, memory, and step tracing. | Should | 4/5 |
| FR‑AG‑02 | Built‑in agents: Planner, Research, Coding, Security, Documentation, Evaluation, Monitoring. | Should | 5 |
| FR‑AG‑03 | Agents run through the gateway/firewall (no bypass). | Must | 5 |
| FR‑AG‑04 | Per‑agent budgets, guardrails, and observability. | Must | 5 |

### 3.10 Deployment (FR‑DP)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR‑DP‑01 | Dockerfiles + Docker Compose for local/full stack. | Must | 1 |
| FR‑DP‑02 | Kubernetes manifests + Helm chart. | Must | 5 |
| FR‑DP‑03 | Terraform for cloud infra (EKS/GKE/AKS + managed PG/Redis/object store). | Should | 5 |
| FR‑DP‑04 | GitHub Actions CI/CD with environments and gates. | Must | 1→5 |

---

## 4. Non‑Functional Requirements

| ID | Category | Requirement | Target / SLO |
|---|---|---|---|
| NFR‑01 | **Availability** | Control plane HA. | 99.9% monthly; stateless replicas behind LB. |
| NFR‑02 | **Latency** | Gateway overhead excluding model inference. | p50 < 15 ms, p99 < 50 ms. |
| NFR‑03 | **Scalability** | Horizontal scale of gateway and workers. | 5k RPS control plane; linear with replicas. |
| NFR‑04 | **Throughput** | Inference throughput via vLLM continuous batching. | Maximize GPU utilization (>70%). |
| NFR‑05 | **Security** | Encryption in transit (TLS) & at rest; secrets in a vault; least privilege. | No plaintext secrets/keys in DB/logs. |
| NFR‑06 | **Privacy** | PII never logged unredacted; configurable retention. | Redaction before persistence. |
| NFR‑07 | **Fault tolerance** | Graceful degradation; fallback models; circuit breakers; retries with backoff. | No single backend failure causes outage. |
| NFR‑08 | **Observability** | Metrics, traces, logs, LLM traces with correlation IDs. | 100% request traceability. |
| NFR‑09 | **Consistency** | Strong consistency for control data (PG); eventual for analytics. | — |
| NFR‑10 | **Durability** | Durable storage for registry/artifacts/audit. | Object store 11 9's; PG PITR. |
| NFR‑11 | **Maintainability** | Modular boundaries, typed code, ≥80% coverage on core modules. | Lint/type/test gates in CI. |
| NFR‑12 | **Extensibility** | Plugin interfaces for providers/guardrails/routers/evaluators/agents. | Add provider w/o core changes. |
| NFR‑13 | **Portability** | Cloud‑agnostic; runs on EKS/GKE/AKS and locally via Compose. | — |
| NFR‑14 | **Compliance‑readiness** | Audit trails, RBAC, data residency hooks. | SOC2‑aligned controls. |
| NFR‑15 | **Performance budget** | Guardrail pipeline latency budget. | < 30 ms for fast detectors; heavy detectors async/sampled. |
| NFR‑16 | **Testability** | Hexagonal ports allow in‑memory adapters for tests. | Fast unit suite < 60 s. |
| NFR‑17 | **Cost efficiency** | Caching + routing reduce provider spend. | Track $ per 1k tokens per route. |

---

## 5. User Personas

| Persona | Role | Goals | Pain points SecurAI solves |
|---|---|---|---|
| **Maya — Platform/ML Platform Engineer** | Owns internal AI platform. | Offer governed AI to product teams; control cost; enforce safety. | Fragmented providers, no central control, surprise bills. |
| **Devin — Application Developer** | Builds product features on LLMs. | Call models with one SDK; reliability; fallbacks. | Provider lock‑in, rate limits, flaky uptime. |
| **Sara — Security / AppSec Engineer** | Owns AI risk & compliance. | Block injection/PII leaks; audit everything; enforce policy. | No visibility into prompts; data exfiltration risk. |
| **Raj — ML / Research Engineer** | Fine‑tunes and evaluates models. | LoRA/QLoRA training, track experiments, promote best model. | Manual training/eval, no registry, no lineage. |
| **Lena — FinOps / Engineering Manager** | Owns budget & reporting. | Attribute spend per team/project; forecast. | No per‑team cost attribution. |
| **Omar — SRE / DevOps** | Runs the platform. | Deploy, scale, alert, recover. | No SLOs, no dashboards, hard rollbacks. |
| **Priya — Org Admin** | Administers tenant. | Manage users, projects, keys, roles. | No tenant isolation / RBAC. |

---

## 6. User Stories

Stories are grouped by epic. Format: *As a `<persona>`, I want `<capability>` so that `<value>`.* Acceptance criteria (AC) are abbreviated.

### Epic A — Gateway & Access
- **US‑A1** As **Devin**, I want to call an OpenAI‑compatible endpoint with an API key so that I can switch to SecurAI by changing only the base URL.
  - AC: existing OpenAI SDK works; invalid key → 401; scoped key only accesses its project.
- **US‑A2** As **Priya**, I want to create orgs/projects and issue scoped API keys so that teams are isolated.
  - AC: key shown once; stored hashed; revocation is immediate.
- **US‑A3** As **Maya**, I want per‑project rate limits & quotas so that one team can't exhaust capacity.
  - AC: 429 with `Retry‑After`; quota visible in dashboard.
- **US‑A4** As **Devin**, I want streaming responses so that UX is responsive.
  - AC: SSE tokens stream; cancel closes upstream.

### Epic B — Routing & Reliability
- **US‑B1** As **Maya**, I want to route by cost/latency/quality so that I balance spend and UX.
  - AC: policy configurable per project; decision is logged.
- **US‑B2** As **Devin**, I want automatic fallback so that a provider outage doesn't break my app.
  - AC: on 5xx/timeout, next backend is tried; fallback recorded.
- **US‑B3** As **Maya**, I want caching so that repeated prompts are cheaper/faster.
  - AC: exact + semantic cache; per‑project toggle; hit recorded.

### Epic C — Safety
- **US‑C1** As **Sara**, I want prompt‑injection/jailbreak detection so that attacks are blocked.
  - AC: malicious prompt blocked or flagged per policy; audit entry created.
- **US‑C2** As **Sara**, I want PII/secret detection & masking so that sensitive data isn't leaked to providers.
  - AC: configured entities masked before egress; output scanned for leaks.
- **US‑C3** As **Sara**, I want an immutable audit log so that I can investigate incidents.
  - AC: every firewall decision recorded with correlation ID; tamper‑evident.

### Epic D — Evaluation & Observability
- **US‑D1** As **Raj**, I want to run benchmark evals so that I can compare model versions.
  - AC: metrics computed; report linked to registry version.
- **US‑D2** As **Raj**, I want hallucination/faithfulness scoring so that I can gate releases.
  - AC: scores stored; promotion blocked below threshold.
- **US‑D3** As **Omar**, I want Grafana dashboards & alerts so that I detect issues fast.
  - AC: dashboards for latency/error/cost; alert fires on SLO breach.
- **US‑D4** As **Devin**, I want to collect user feedback so that quality improves.
  - AC: feedback API; visible in dashboard; joinable to traces.

### Epic E — Fine‑Tuning & Registry
- **US‑E1** As **Raj**, I want to curate a dataset (clean/dedup/validate) so that training data is high quality.
  - AC: validation report; rejected rows logged.
- **US‑E2** As **Raj**, I want LoRA/QLoRA training jobs so that I can adapt open models cheaply.
  - AC: job tracked in MLflow; adapter artifact stored.
- **US‑E3** As **Raj**, I want to promote a model version so that it serves production traffic.
  - AC: eval gate passed; version deployed to vLLM; lineage recorded.

### Epic F — Agents
- **US‑F1** As **Devin**, I want to run a multi‑agent workflow so that complex tasks are automated.
  - AC: agent steps traced; tools sandboxed; budget enforced.
- **US‑F2** As **Sara**, I want agents to pass through the firewall so that they can't bypass safety.
  - AC: all agent LLM calls go through gateway+firewall; no direct provider access.

### Epic G — FinOps & Admin
- **US‑G1** As **Lena**, I want per‑project cost reports so that I can charge back teams.
  - AC: cost by project/model/time; export CSV.
- **US‑G2** As **Omar**, I want safe deploys & rollbacks so that releases are low‑risk.
  - AC: blue/green or canary; one‑command rollback.

---

*Continue to [Part 2 — Architecture](./02-architecture.md).*
