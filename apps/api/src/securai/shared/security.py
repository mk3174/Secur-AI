"""Security primitives: API key generation/hashing, password hashing, JWT.

API keys are high-entropy random tokens, so SHA-256 is the appropriate
(fast, standard) hash for lookup. Passwords are low-entropy human secrets,
so they use Argon2id.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


# --- API keys ---

def generate_api_key(prefix: str) -> tuple[str, str, str]:
    """Return (full_key, lookup_prefix, sha256_hash).

    The full key is shown to the user exactly once. We persist only the
    hash plus a short non-secret lookup prefix.
    """
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}_{secret}"
    lookup_prefix = full_key[: len(prefix) + 9]  # prefix + "_" + 8 chars
    return full_key, lookup_prefix, hash_api_key(full_key)


def hash_api_key(full_key: str) -> str:
    return hashlib.sha256(full_key.encode("utf-8")).hexdigest()


def lookup_prefix_for(full_key: str, prefix: str) -> str:
    return full_key[: len(prefix) + 9]


# --- Passwords ---

def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# --- JWT ---

def create_access_token(
    *, subject: str, secret: str, algorithm: str, ttl_seconds: int, claims: dict | None = None
) -> str:
    now = dt.datetime.now(tz=dt.UTC)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(seconds=ttl_seconds)).timestamp()),
        **(claims or {}),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, *, secret: str, algorithm: str) -> dict:
    return jwt.decode(token, secret, algorithms=[algorithm])
