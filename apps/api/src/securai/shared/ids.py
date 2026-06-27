"""Identifier helpers.

We use UUIDv4 strings as primary keys for portability across SQLite/Postgres.
(The SAD specifies UUIDv7 for time-sortability; that is a drop-in change once
the platform standardises on Postgres.)
"""

from __future__ import annotations

import uuid


def new_id() -> str:
    return str(uuid.uuid4())


def new_request_id() -> str:
    return "req_" + uuid.uuid4().hex
