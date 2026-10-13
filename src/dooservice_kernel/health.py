"""Whether the app is alive, and whether it can do its work: its database and every
boundary it was given answer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from fastapi import APIRouter
from tortoise import connections

from .errors import DomainError
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


class HealthStatus(Schema):
    status: str


class HealthController:
    def __init__(self, boundaries: Sequence[Boundary]) -> None:
        self.boundaries = boundaries
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
        connection = connections.get("default")
        await connection.execute_query("SELECT 1")
        for boundary in self.boundaries:
            if not boundary.ready():
                raise boundary.unavailable()
        return HealthStatus(status="ready")
