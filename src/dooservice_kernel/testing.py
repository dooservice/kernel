"""Testing a module in a few lines (the `testing` extra): the app built with its modules,
an in-memory database with the schema generated, its lifespan running, and a client:

    async with KernelHarness([ShopModule()], sections=[ShopConfig(currency="PEN")]) as shop:
        answer = await shop.client.get("/api/orders")

`FakeBoundary` stands in for a bus or a queue; set `up = False` to see what readiness
answers without it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Any, Self

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from .application import ApplicationBuilder
from .config import Config
from .errors import DomainError, UnavailableError
from .extensions import Extension
from .health import Boundary
from .profile import Profile
from .registry import Module
from .sections import SessionConfig


class FakeBoundaryDownError(UnavailableError):
    code = "fake_boundary_down"
    title = "Fake Boundary Down"


class FakeBoundary:
    def __init__(self, name: str = "fake") -> None:
        self.name = name
        self.up = True
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.connected = False

    def ready(self) -> bool:
        return self.up

    def unavailable(self) -> DomainError:
        return FakeBoundaryDownError(f"{self.name} is down")


class KernelHarness:
    def __init__(
        self,
        modules: Sequence[Module],
        sections: Sequence[Any] = (),
        profile: Profile | None = None,
        boundaries: Sequence[Boundary] = (),
        state: Mapping[str, object] | None = None,
        extensions: Sequence[Extension] = (),
    ) -> None:
        self.config = Config(session=SessionConfig(secret="test"), sections=sections)
        self.config.database.url = "sqlite://:memory:"
        self.builder = ApplicationBuilder(
            self.config,
            modules,
            profile=profile,
            boundaries=boundaries,
            state=state,
            use_generated_schemas=True,
            extensions=extensions,
        )
        self.app: FastAPI = self.builder.build()
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")
        self.lifespan = self.builder.lifespan(self.app)

    async def __aenter__(self) -> Self:
        await self.lifespan.__aenter__()
        return self

    async def __aexit__(
        self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None
    ) -> None:
        await self.client.aclose()
        await self.lifespan.__aexit__(kind, error, trace)
