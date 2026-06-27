"""Prometheus metrics for the gateway control plane."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "securai_requests_total",
    "Total inference requests processed by the gateway.",
    ["endpoint", "provider", "model", "status"],
)

REQUEST_LATENCY = Histogram(
    "securai_request_latency_seconds",
    "End-to-end gateway request latency in seconds.",
    ["endpoint", "provider"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)

TOKENS_TOTAL = Counter(
    "securai_tokens_total",
    "Total tokens processed.",
    ["model", "kind"],  # kind = prompt|completion
)

RATE_LIMITED = Counter(
    "securai_rate_limited_total",
    "Requests rejected by rate limiting.",
    ["project"],
)
