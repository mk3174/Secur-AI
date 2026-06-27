.PHONY: help install dev test lint fmt run compose-up compose-down

API_DIR := apps/api
VENV := $(API_DIR)/.venv
PY := $(VENV)/bin/python

help:
	@echo "SecurAI - developer tasks"
	@echo "  make install      Create venv and install API (dev) deps"
	@echo "  make run          Run the API locally (uvicorn, reload)"
	@echo "  make test         Run the API test suite"
	@echo "  make lint         Run ruff lint"
	@echo "  make fmt          Auto-format + fix with ruff"
	@echo "  make compose-up   Build and start the full stack (Docker)"
	@echo "  make compose-down Stop the stack"

install:
	cd $(API_DIR) && python3 -m virtualenv .venv && . .venv/bin/activate && pip install -e ".[dev]"

run:
	cd $(API_DIR) && . .venv/bin/activate && uvicorn securai.main:app --reload --port 8000

test:
	cd $(API_DIR) && . .venv/bin/activate && python -m pytest -q

lint:
	cd $(API_DIR) && . .venv/bin/activate && ruff check src tests

fmt:
	cd $(API_DIR) && . .venv/bin/activate && ruff check --fix src tests && ruff format src tests

compose-up:
	docker compose -f deploy/compose/docker-compose.yml up --build

compose-down:
	docker compose -f deploy/compose/docker-compose.yml down
