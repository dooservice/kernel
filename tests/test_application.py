from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from typing import ClassVar

from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
import msgspec
import pytest

from dooservice_kernel.application import ApplicationBuilder
from dooservice_kernel.config import Config, SessionConfig
from dooservice_kernel.errors import DomainError, UnavailableError
from dooservice_kernel.profile import Profile
from dooservice_kernel.registry import Module


class GreetingConfig(msgspec.Struct, forbid_unknown_fields=True):
    section: ClassVar[str] = "greeting"

    word: str = "hello"


class Greeter(Module):
    name = "greeter"
    config_sections = (GreetingConfig,)

    def __init__(self) -> None:
        router = APIRouter()
        router.add_api_route("/greet", self.greet, methods=["GET"])
        self.routers = (router,)

    async def greet(self) -> dict[str, str]:
        return {"word": "hello"}


class QueueDown(UnavailableError):
    code = "queue_down"
    title = "Queue Down"


class Queue:
    def __init__(self) -> None:
        self.opened = False
        self.up = True

    async def connect(self) -> None:
        self.opened = True

    async def close(self) -> None:
        self.opened = False

    def ready(self) -> bool:
        return self.up

    def unavailable(self) -> DomainError:
        return QueueDown("the queue is gone")


@pytest.fixture
async def running() -> AsyncIterator[tuple[FastAPI, Queue]]:
    queue = Queue()
    config = Config(session=SessionConfig(secret="s"))
    config.database.url = "sqlite://:memory:"
    builder = ApplicationBuilder(
        config,
        [Greeter()],
        profile=Profile(title="shop", api_prefix="/api/v1"),
        boundaries=[queue],
        state={"clock": "utc"},
        use_generated_schemas=True,
    )
    app = builder.build()
    async with builder.lifespan(app):
        yield app, queue


async def test_modules_are_mounted_under_the_profile_prefix(running: tuple[FastAPI, Queue]) -> None:
    app, queue = running
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        greeted = await client.get("/api/v1/greet")

    assert greeted.json() == {"word": "hello"}
    assert app.title == "shop"
    assert app.state.clock == "utc"
    assert queue.opened


async def test_readiness_answers_with_the_boundary_that_is_down(running: tuple[FastAPI, Queue]) -> None:
    app, queue = running
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ready = await client.get("/health/ready")
        queue.up = False
        down = await client.get("/health/ready")

    assert ready.status_code == 200
    assert down.status_code == 503
    assert down.json()["code"] == "queue_down"


class Ledger(Module):
    name = "ledger"

    def __init__(self) -> None:
        self.balanced = True

    def health_checks(self) -> Mapping[str, Callable[[], Awaitable[bool]]]:
        return {"balance": self.balance}

    async def balance(self) -> bool:
        return self.balanced


async def test_readiness_names_each_check_and_which_one_fails() -> None:
    ledger = Ledger()
    config = Config(session=SessionConfig(secret="s"))
    config.database.url = "sqlite://:memory:"
    builder = ApplicationBuilder(config, [ledger], use_generated_schemas=True)
    app = builder.build()
    async with builder.lifespan(app), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ready = await client.get("/health/ready")
        ledger.balanced = False
        failing = await client.get("/health/ready")

    assert ready.json()["checks"] == {"database": "ok", "ledger.balance": "ok"}
    assert failing.status_code == 503
    assert (failing.json()["code"], failing.json()["params"]) == ("not_ready", {"failing": "ledger.balance"})
