# SecurAI — Software Architecture Document (SAD)

**SecurAI** is an enterprise **AI Gateway · LLMOps · AgentOps · AI Security** platform: a single governed control plane in front of every LLM and AI agent an organization runs — open‑source (Llama, Gemma, Qwen, Mistral, Phi), fine‑tuned, or external (OpenAI, Anthropic) — providing routing, safety, observability, evaluation, fine‑tuning, and cost control.

> **Status:** Architecture & planning document. **No implementation code** — this defines the system in enough detail that an engineer can build it phase by phase.
>
> **Architectural stance:** A **microservice‑ready modular monolith** (control plane) + **separately deployed GPU/data‑plane services** (vLLM inference, LoRA/QLoRA training, async workers). Designed to be **built by one engineer in phases**, each phase independently deployable, with a clean path to microservice extraction.

---

## How to read this document

The SAD is split into 8 parts for maintainability. All 50 required sections are covered, mapped below.

| Part | File | Sections |
|---|---|---|
| **1. Product & Requirements** | [`01-product-and-requirements.md`](./01-product-and-requirements.md) | 1 Executive Summary · 2 Product Vision · 3 Functional Requirements · 4 Non‑Functional Requirements · 5 User Personas · 6 User Stories |
| **2. Architecture** | [`02-architecture.md`](./02-architecture.md) | 7 High‑Level Architecture · 8 Low‑Level Architecture · 9 Service Breakdown · 10 API Gateway Design · 11 Authentication Flow |
| **3. Data & Flows** | [`03-data-and-flows.md`](./03-data-and-flows.md) | 12 Database Design · 13 ER Diagram · 14 Service Communication · 15 Event Flow · 16 Data Flow · 17 Request Lifecycle |
| **4. Structure & Modules** | [`04-structure-and-modules.md`](./04-structure-and-modules.md) | 18 Folder Structure · 19 Backend Architecture · 20 Frontend Architecture · 21 AI Module Architecture |
| **5. AI Pipelines** | [`05-ai-pipelines.md`](./05-ai-pipelines.md) | 22 Training Pipeline · 23 Inference Pipeline · 24 Evaluation Pipeline |
| **6. Deployment & Platform** | [`06-deployment-and-platform.md`](./06-deployment-and-platform.md) | 25 Deployment · 26 Kubernetes · 27 CI/CD · 28 Security · 29 Monitoring · 30 Logging · 31 AI Safety · 32 Agent Framework · 33 Infrastructure Diagram |
| **7. Quality & Operations** | [`07-quality-and-operations.md`](./07-quality-and-operations.md) | 34 Scaling · 35 Disaster Recovery · 36 Testing · 37 Technology Decisions · 38 Why Each Technology · 39 Future Roadmap · 40 Risks & Trade‑offs · 41 Estimated Effort · 42 Implementation Order |
| **8. Process & Standards** | [`08-process-and-standards.md`](./08-process-and-standards.md) | 43 Git Branching · 44 Code Quality · 45 Coding Conventions · 46 Documentation · 47 API Docs · 48 Definition of Done · 49 Deployment Checklist · 50 Final Architecture |

---

## Section index (all 50)

1. [Executive Summary](./01-product-and-requirements.md#1-executive-summary)
2. [Product Vision](./01-product-and-requirements.md#2-product-vision)
3. [Functional Requirements](./01-product-and-requirements.md#3-functional-requirements)
4. [Non‑Functional Requirements](./01-product-and-requirements.md#4-nonfunctional-requirements)
5. [User Personas](./01-product-and-requirements.md#5-user-personas)
6. [User Stories](./01-product-and-requirements.md#6-user-stories)
7. [High‑Level Architecture](./02-architecture.md#7-highlevel-architecture)
8. [Low‑Level Architecture](./02-architecture.md#8-lowlevel-architecture)
9. [Service Breakdown](./02-architecture.md#9-service-breakdown)
10. [API Gateway Design](./02-architecture.md#10-api-gateway-design)
11. [Authentication Flow](./02-architecture.md#11-authentication-flow)
12. [Database Design](./03-data-and-flows.md#12-database-design)
13. [ER Diagram](./03-data-and-flows.md#13-er-diagram)
14. [Service Communication](./03-data-and-flows.md#14-service-communication)
15. [Event Flow](./03-data-and-flows.md#15-event-flow)
16. [Data Flow](./03-data-and-flows.md#16-data-flow)
17. [Request Lifecycle](./03-data-and-flows.md#17-request-lifecycle)
18. [Folder Structure](./04-structure-and-modules.md#18-folder-structure)
19. [Backend Architecture](./04-structure-and-modules.md#19-backend-architecture)
20. [Frontend Architecture](./04-structure-and-modules.md#20-frontend-architecture)
21. [AI Module Architecture](./04-structure-and-modules.md#21-ai-module-architecture)
22. [Training Pipeline](./05-ai-pipelines.md#22-training-pipeline-finetuning)
23. [Inference Pipeline](./05-ai-pipelines.md#23-inference-pipeline)
24. [Evaluation Pipeline](./05-ai-pipelines.md#24-evaluation-pipeline)
25. [Deployment Architecture](./06-deployment-and-platform.md#25-deployment-architecture)
26. [Kubernetes Architecture](./06-deployment-and-platform.md#26-kubernetes-architecture)
27. [CI/CD Pipeline](./06-deployment-and-platform.md#27-cicd-pipeline)
28. [Security Architecture](./06-deployment-and-platform.md#28-security-architecture)
29. [Monitoring Architecture](./06-deployment-and-platform.md#29-monitoring-architecture)
30. [Logging Architecture](./06-deployment-and-platform.md#30-logging-architecture)
31. [AI Safety Architecture](./06-deployment-and-platform.md#31-ai-safety-architecture)
32. [Agent Framework Design](./06-deployment-and-platform.md#32-agent-framework-design)
33. [Infrastructure Diagram](./06-deployment-and-platform.md#33-infrastructure-diagram)
34. [Scaling Strategy](./07-quality-and-operations.md#34-scaling-strategy)
35. [Disaster Recovery](./07-quality-and-operations.md#35-disaster-recovery)
36. [Testing Strategy](./07-quality-and-operations.md#36-testing-strategy)
37. [Technology Decisions](./07-quality-and-operations.md#37-technology-decisions)
38. [Why Each Technology](./07-quality-and-operations.md#38-why-each-technology-was-chosen)
39. [Future Roadmap](./07-quality-and-operations.md#39-future-roadmap-postmvp-capabilities)
40. [Risks & Trade‑offs](./07-quality-and-operations.md#40-risks--tradeoffs)
41. [Estimated Development Effort](./07-quality-and-operations.md#41-estimated-development-effort-phased-by-scope-not-calendar)
42. [Recommended Order of Implementation](./07-quality-and-operations.md#42-recommended-order-of-implementation)
43. [Git Branching Strategy](./08-process-and-standards.md#43-git-branching-strategy)
44. [Code Quality Standards](./08-process-and-standards.md#44-code-quality-standards)
45. [Coding Conventions](./08-process-and-standards.md#45-coding-conventions)
46. [Documentation Standards](./08-process-and-standards.md#46-documentation-standards)
47. [API Documentation Strategy](./08-process-and-standards.md#47-api-documentation-strategy)
48. [Definition of Done](./08-process-and-standards.md#48-definition-of-done-per-module)
49. [Production Deployment Checklist](./08-process-and-standards.md#49-production-deployment-checklist)
50. [Final Recommended Architecture](./08-process-and-standards.md#50-final-recommended-architecture)

---

## Development roadmap (at a glance)

The platform grows in capability rather than being built all at once. Each phase is independently demoable and production‑deployable. (Full detail in [Part 7 §41–42](./07-quality-and-operations.md#41-estimated-development-effort-phased-by-scope-not-calendar).)

| Phase | Goal | Headline features |
|---|---|---|
| **P1 — MVP** | A secure AI gateway | FastAPI backend · auth · prompt logging · single local LLM via vLLM · basic dashboard · Docker |
| **P2 — Intelligent Routing** | Distributed inference & perf | Multiple models · rule‑based routing · cost estimation · latency tracking · retries · Redis caching |
| **P3 — AI Safety** | Security‑focused AI | Prompt injection detection · PII masking · output moderation · guardrails · security audit logs |
| **P4 — Evaluation & Observability** | Operating AI systems | Eval pipelines · hallucination detection · user feedback · MLflow · Langfuse traces · Grafana |
| **P5 — Fine‑Tuning & Deployment** | Full lifecycle | Dataset curation · LoRA/QLoRA · model registry · automated deploy · Kubernetes · CI/CD |

> **Feasibility note:** the complete feature set is **not** achievable in a single build by one engineer; the phased roadmap above is the deliberate de‑risking strategy. Each module is bounded so it can later become a standalone microservice.

---

## Core capabilities map

AI Gateway · Prompt Firewall · LLM Router · Model Registry · Fine‑Tuning Pipeline · Evaluation System · Observability · Dashboard · Multi‑Agent System · Deployment (Docker/K8s/Helm/Terraform/GitHub Actions on AWS/GCP/Azure).

Architectural patterns: Clean Architecture · Domain‑Driven Design · Hexagonal (Ports & Adapters) · Dependency Injection · Repository · CQRS (where beneficial) · Event‑Driven (transactional outbox + Kafka) · Microservice‑ready modular monolith.
