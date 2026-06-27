"""Structured logging setup using structlog.

All logs carry the correlation id so logs can be joined to traces.
"""

from __future__ import annotations

import logging
import sys

import structlog

from securai.shared.context import get_request_id


def _add_request_id(_logger, _name, event_dict):
    event_dict.setdefault("request_id", get_request_id())
    return event_dict


def configure_logging(*, level: str = "INFO", json: bool = True) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_id,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if json
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "securai"):
    return structlog.get_logger(name)
