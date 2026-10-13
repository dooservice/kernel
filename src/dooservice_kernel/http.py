from __future__ import annotations

from contextvars import ContextVar
import uuid

from pydantic import BaseModel, ConfigDict, Field
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .constants import REQUEST_ID_HEADER

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
job_id_var: ContextVar[str] = ContextVar("job_id", default="-")


class Schema(BaseModel):
    """Base for every HTTP request/response model."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class FieldProblem(Schema):
    """One field a request got wrong: where it is, as `email` or `window.start_hour`, and
    the code the panel words it with, as `invalid_email` or `string_too_short`."""

    field: str
    code: str


class ProblemDetails(Schema):
    """RFC 9457 problem document, extended with a machine `code`, the `params` the panel
    words it with, the request id, and for a 422 each field that was wrong."""

    type: str = "about:blank"
    title: str
    status: int
    code: str
    detail: str = ""
    params: dict[str, str | int] = Field(default_factory=dict)
    request_id: str = "-"
    fields: list[FieldProblem] = Field(default_factory=list)


class RequestContextMiddleware:
    """Assigns a request id to every request and echoes it back as a response header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex[:16]
        request_id_var.set(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)
