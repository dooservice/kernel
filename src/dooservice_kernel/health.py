"""Whether the app is alive, and whether it can do its work: its database, every boundary
it was given and every check its modules declare answer.

`/health/ready` names each check and whether it holds, so a monitor sees which one fails
and not only that one does. While a boundary is down it answers with that boundary's own
error; while only a module's check fails, with `not_ready` and the checks that fail.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Protocol

from fastapi import APIRouter
from pydantic import Field
from tortoise import connections

from .errors import DomainError, UnavailableError
from .http import Schema


class Boundary(Protocol):
    """Something outside the process the app cannot work without: opened before the
    database, closed after it, and asked whether it is still there by the readiness check."""

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    def ready(self) -> bool: ...

    def unavailable(self) -> DomainError:
        """What the readiness check answers while this boundary is not ready."""
        ...


Check = Callable[[], Awaitable[bool]]


class NotReadyError(UnavailableError):
    code = "not_ready"
    title = "Not Ready"

    def __init__(self, failing: Sequence[str]) -> None:
        super().__init__(f"failing: {', '.join(failing)}", {"failing": ", ".join(failing)})


class HealthStatus(Schema):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)


class HealthController:
    def __init__(self, boundaries: Sequence[Boundary], checks: Mapping[str, Check] | None = None) -> None:
        self.boundaries = boundaries
        self.checks = dict(checks or {})
        self.router = APIRouter(tags=["health"])
        self.router.add_api_route("/health", self.liveness, methods=["GET"], response_model=HealthStatus)
        self.router.add_api_route("/health/ready", self.readiness, methods=["GET"], response_model=HealthStatus)

    async def liveness(self) -> HealthStatus:
        return HealthStatus(status="ok")

    async def readiness(self) -> HealthStatus:
        """Ready when the database answers and every boundary is there.

        An app that answers HTTP while what it works through is gone looks healthy and
        does nothing; asking each boundary lets a monitor see it.
        """
        await connections.get("default").execute_query("SELECT 1")
        results = {"database": "ok"}
        for boundary in self.boundaries:
            results[getattr(boundary, "name", type(boundary).__name__)] = "ok" if boundary.ready() else "failing"
        for name, check in self.checks.items():
            results[name] = "ok" if await self.holds(check) else "failing"
        for boundary in self.boundaries:
            if not boundary.ready():
                raise boundary.unavailable()
        failing = [name for name, result in results.items() if result != "ok"]
        if failing:
            raise NotReadyError(failing)
        return HealthStatus(status="ready", checks=results)

    @staticmethod
    async def holds(check: Check) -> bool:
        try:
            return await check()
        except Exception:
            return False
