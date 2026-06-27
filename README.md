# SecurAI

**Enterprise AI Gateway · LLMOps · AgentOps · AI Security Platform.**

SecurAI is a production‑grade platform that lets organizations securely deploy, route, monitor, evaluate, fine‑tune, and govern many LLMs and AI agents through one unified, OpenAI‑compatible gateway — across open‑source models (Llama, Gemma, Qwen, Mistral, Phi), fine‑tuned models, and external providers (OpenAI, Anthropic).

It tackles the operational and safety problems that appear once a company runs multiple AI apps: prompt injection, hallucinations, monitoring, model routing, multi‑provider sprawl, cost/token analytics, latency, GPU management, AI security, fine‑tuned model management, evaluation, experiment tracking, multi‑agent systems, and production inference.

## Architecture

The complete **Software Architecture Document (SAD)** — all 50 sections (vision, requirements, high/low‑level architecture, data design, pipelines, deployment, security, observability, roadmap, standards, and more) — lives in:

➡️ **[`docs/architecture/`](./docs/architecture/README.md)**

> This repository currently contains the **architecture & planning** for SecurAI (no implementation code yet). The design is a **microservice‑ready modular monolith** intended to be built by one engineer in phases (MVP → routing → safety → eval/observability → fine‑tuning/deploy).

## Development roadmap

| Phase | Goal |
|---|---|
| P1 MVP | Secure AI gateway: FastAPI, auth, prompt logging, one local vLLM model, basic dashboard, Docker |
| P2 | Intelligent routing: multi‑model, rule‑based routing, cost/latency, retries, Redis caching |
| P3 | AI safety: prompt injection detection, PII masking, output moderation, guardrails, audit logs |
| P4 | Evaluation & observability: eval pipelines, hallucination detection, feedback, MLflow, Langfuse, Grafana |
| P5 | Fine‑tuning & deployment: dataset curation, LoRA/QLoRA, model registry, automated deploy, Kubernetes, CI/CD |

See the [SAD index](./docs/architecture/README.md) for the full breakdown.
