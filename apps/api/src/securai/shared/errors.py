"""Domain error hierarchy mapped to RFC 9457 (problem+json) at the API edge."""

from __future__ import annotations


class SecurAIError(Exception):
    """Base class for all domain/application errors."""

    status_code: int = 500
    error_type: str = "internal_error"

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFoundError(SecurAIError):
    status_code = 404
    error_type = "not_found"


class ValidationError(SecurAIError):
    status_code = 422
    error_type = "validation_error"


class ConflictError(SecurAIError):
    status_code = 409
    error_type = "conflict"


class AuthenticationError(SecurAIError):
    status_code = 401
    error_type = "authentication_error"


class AuthorizationError(SecurAIError):
    status_code = 403
    error_type = "authorization_error"


class RateLimitError(SecurAIError):
    status_code = 429
    error_type = "rate_limit_exceeded"


class ProviderError(SecurAIError):
    status_code = 502
    error_type = "provider_error"
