"""Domain errors — mapped to HTTP only in presentation layer (see PROJECT_CONTEXT §8)."""


class DomainError(Exception):
    code: str = "DOMAIN_ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    status_code = 400


class UnauthorizedError(DomainError):
    code = "UNAUTHORIZED"
    status_code = 401


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(DomainError):
    code = "CONFLICT"
    status_code = 409


class ForbiddenError(DomainError):
    code = "FORBIDDEN"
    status_code = 403
