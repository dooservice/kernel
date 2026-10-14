from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .constants import PROBLEM_CONTENT_TYPE
from .errors import DomainError
from .http import FieldProblem, ProblemDetails, request_id_var

log = logging.getLogger(__name__)


class ProblemRenderer:
    """Renders every failure as an RFC 9457 problem document.
    The kernel's three handlers are here; an application adds those of its own
    boundaries with `render`. Individual errors never register their own."""

    def register(self, app: FastAPI) -> None:
        app.add_exception_handler(DomainError, self.handle_domain_error)
        app.add_exception_handler(RequestValidationError, self.handle_validation_error)
        app.add_exception_handler(Exception, self.handle_unexpected_error)

    def render(
        self,
        status: int,
        code: str,
        title: str,
        detail: str,
        params: dict[str, str | int] | None = None,
        fields: list[FieldProblem] | None = None,
    ) -> JSONResponse:
        problem = ProblemDetails(
            title=title,
            status=status,
            code=code,
            detail=detail,
            params=params or {},
            request_id=request_id_var.get(),
            fields=fields or [],
        )
        return JSONResponse(status_code=status, content=problem.model_dump(), media_type=PROBLEM_CONTENT_TYPE)

    async def handle_domain_error(self, request: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, DomainError)
        return self.render(error.status, error.code, error.title, error.detail, error.params)

    async def handle_validation_error(self, request: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, RequestValidationError)
        detail = "; ".join(
            f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}" for issue in error.errors()
        )
        fields = [
            FieldProblem(field=".".join(str(part) for part in issue["loc"][1:]), code=issue["type"])
            for issue in error.errors()
        ]
        return self.render(422, "validation_error", "Validation Error", detail, fields=fields)

    async def handle_unexpected_error(self, request: Request, error: Exception) -> JSONResponse:
        log.exception("unhandled error on %s", request.url.path, exc_info=error)
        return self.render(500, "internal_error", "Internal Error", "An unexpected error occurred")
