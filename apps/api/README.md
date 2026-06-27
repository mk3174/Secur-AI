# SecurAI API — Phase 1 (MVP secure AI gateway)

The control-plane API: an **OpenAI-compatible AI gateway** with API-key auth,
JWT dashboard auth, RBAC, multi-tenant orgs/projects, prompt logging, cost &
token accounting, rate limiting, Prometheus metrics, and an embedded dashboard.

Built as a **hexagonal modular monolith** (see `docs/architecture/`):
`domain` → `application` → `adapters`/`api`, wired by a DI container.

## Quick start (local, zero infra)

```bash
make install          # create venv + install (uses virtualenv)
make run               # uvicorn on http://localhost:8000
```

Then open `http://localhost:8000/` for the dashboard. A default org, admin
user, and project are created on first run:

- email: `admin@securai.local`
- password: `admin12345`

The default provider is `echo` (a deterministic mock), so the gateway works
without a GPU or any external API.

## Try the gateway (OpenAI-compatible)

1. Sign in to the dashboard, create an **API key** (copy it — shown once).
2. Call it like the OpenAI API:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk_securai_..." \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

Streaming (SSE):

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk_securai_..." \
  -d '{"messages":[{"role":"user","content":"hi"}],"stream":true}'
```

Because the API is OpenAI-compatible, the official OpenAI SDKs work by setting
`base_url=http://localhost:8000/v1` and `api_key=<your SecurAI key>`.

## Connect a real model (vLLM / OpenAI-compatible)

Set environment (see `.env.example`):

```bash
SECURAI_DEFAULT_PROVIDER=openai_compatible
SECURAI_DEFAULT_MODEL=meta-llama/Llama-3.1-8B-Instruct
SECURAI_PROVIDER_BASE_URL=http://localhost:8001/v1
```

Any OpenAI-compatible server works (self-hosted vLLM, OpenAI, etc.).

## API surface

| Area | Endpoint |
|---|---|
| Inference | `POST /v1/chat/completions`, `GET /v1/models` |
| Auth | `POST /api/v1/auth/login`, `GET /api/v1/me` |
| Projects | `GET/POST /api/v1/projects` |
| API keys | `GET/POST /api/v1/projects/{id}/keys`, `POST /api/v1/keys/{id}/revoke` |
| Logs/stats | `GET /api/v1/logs`, `GET /api/v1/stats` |
| Ops | `GET /healthz`, `/readyz`, `/metrics`, `/docs` (OpenAPI) |

## Develop

```bash
make test     # pytest
make lint      # ruff
make fmt       # ruff --fix + format
```

## Run the full stack with Docker

```bash
make compose-up   # API + PostgreSQL (echo provider)
```

## Configuration

All settings are env-driven with the `SECURAI_` prefix (see `.env.example`).
Defaults are dev-friendly (SQLite, echo provider, bootstrap admin). For
production: set a strong `SECURAI_JWT_SECRET`, use a Postgres `DATABASE_URL`,
and disable bootstrap.
