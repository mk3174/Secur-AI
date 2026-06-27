# SecurAI control-plane API image (CPU-only; no ML deps).
# Multi-stage, slim, non-root.

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

FROM base AS builder
WORKDIR /build
COPY apps/api/pyproject.toml apps/api/README.md ./
COPY apps/api/src ./src
RUN pip install --upgrade pip && pip install --prefix=/install .

FROM base AS runtime
RUN useradd --create-home --uid 10001 securai
WORKDIR /app
COPY --from=builder /install /usr/local
COPY apps/api/src ./src
ENV PYTHONPATH=/app/src \
    SECURAI_DATABASE_URL=sqlite+aiosqlite:///./securai.db
USER securai
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status==200 else 1)"
CMD ["uvicorn", "securai.main:app", "--host", "0.0.0.0", "--port", "8000"]
