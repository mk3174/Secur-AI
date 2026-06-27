# SecurAI

**Enterprise AI Gateway · LLMOps · AgentOps · AI Security Platform.**

SecurAI lets organizations securely deploy, route, monitor, evaluate, and govern
many LLMs and AI agents through one unified, **OpenAI-compatible** gateway —
across open-source models (Llama, Gemma, Qwen, Mistral, Phi), fine-tuned models,
and external providers (OpenAI, Anthropic).

The platform is built in phases. The complete architecture is documented in the
Software Architecture Document; this repo implements it incrementally.

## Status

| Phase | Scope | State |
|---|---|---|
| **P1 — MVP secure gateway** | OpenAI-compatible gateway, API-key + JWT auth, RBAC, orgs/projects, prompt logging, cost/token accounting, rate limiting, metrics, dashboard, Docker | **Implemented** → [`apps/api`](./apps/api) |
| P2 — Intelligent routing | Multi-model, strategy routing, cost/latency, retries/fallback, Redis cache | Planned |
| P3 — AI safety | Prompt firewall, PII masking, moderation, guardrails, audit | Planned |
| P4 — Eval & observability | Eval pipelines, hallucination detection, feedback, MLflow, Langfuse, Grafana | Planned |
| P5 — Fine-tuning & deploy | Dataset curation, LoRA/QLoRA, registry, K8s, CI/CD | Planned |

## Repository layout

```
apps/api/            FastAPI control-plane (modular monolith) — Phase 1
deploy/docker/       Dockerfiles
deploy/compose/      docker-compose stack
.github/workflows/   CI (lint + tests + docker build)
docs/architecture/   Software Architecture Document (see the architecture branch/PR)
```

## Run Phase 1 locally

```bash
make install   # venv + deps
make run        # http://localhost:8000  (dashboard + OpenAI-compatible API)
make test       # test suite
```

See [`apps/api/README.md`](./apps/api/README.md) for full usage (creating API
keys, calling the gateway, connecting a real vLLM/OpenAI-compatible model).
