from __future__ import annotations


class DomainError(Exception):
    """Base for every domain failure. Carries its HTTP mapping so no per-error handler exists.

    `detail` is for whoever reads a log, in English. What a person reads is written by the
    panel from `code`, in their language, with `params` filling in what the sentence needs
    — the figures of a limit, the reason a card was refused — so the server never writes
    a sentence a person sees.
    """

    status: int = 500
    code: str = "internal_error"
    title: str = "Internal Error"

    def __init__(self, detail: str, params: dict[str, str | int] | None = None) -> None:
        self.detail = detail
        self.params = params or {}
        super().__init__(detail)


class BadRequestError(DomainError):
    status = 400
    code = "bad_request"
    title = "Bad Request"


class UnauthorizedError(DomainError):
    status = 401
    code = "unauthorized"
    title = "Unauthorized"


class ForbiddenError(DomainError):
    status = 403
    code = "forbidden"
    title = "Forbidden"


class NotFoundError(DomainError):
    status = 404
    code = "not_found"
    title = "Not Found"


class ConflictError(DomainError):
    status = 409
    code = "conflict"
    title = "Conflict"


class LockedError(DomainError):
    status = 423
    code = "locked"
    title = "Locked"


class RateLimitedError(DomainError):
    status = 429
    code = "rate_limited"
    title = "Too Many Requests"


class UpstreamError(DomainError):
    status = 502
    code = "upstream_error"
    title = "Upstream Error"


class UnavailableError(DomainError):
    status = 503
    code = "unavailable"
    title = "Service Unavailable"
