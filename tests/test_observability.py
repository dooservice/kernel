from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from dooservice_kernel.application import ApplicationBuilder
from dooservice_kernel.config import Config
from dooservice_kernel.logging import ContextInjectionFilter, JsonFormatter
from dooservice_kernel.metrics import Metrics
from dooservice_kernel.registry import Module
from dooservice_kernel.tracing import Tracing


class Orders(Module):
    name = "orders"

    def __init__(self) -> None:
        router = APIRouter()
        router.add_api_route("/orders/{order_id}", self.show, methods=["GET"])
        self.routers = (router,)

    async def show(self, order_id: int) -> dict[str, int]:
        return {"id": order_id}


def observed(**server: object) -> Config:
    config = Config.read({"session": {"secret": "s"}, "server": server}, [])
    config.database.url = "sqlite://:memory:"
    return config


async def test_metrics_count_each_route_by_its_template() -> None:
    builder = ApplicationBuilder(observed(), [Orders()], use_generated_schemas=True, extensions=[Metrics()])
    app = builder.build()
    async with builder.lifespan(app), AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        await client.get("/api/orders/1")
        await client.get("/api/orders/2")
        scraped = (await client.get("/metrics")).text

    assert 'http_requests_total{method="GET",route="/api/orders/{order_id}",status="200"} 2.0' in scraped


async def test_without_metrics_there_is_no_metrics_route() -> None:
    builder = ApplicationBuilder(observed(), [Orders()], use_generated_schemas=True)
    app = builder.build()
    async with builder.lifespan(app), AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        assert (await client.get("/metrics")).status_code == 404


async def test_tracing_instruments_the_app() -> None:
    builder = ApplicationBuilder(observed(), [Orders()], use_generated_schemas=True, extensions=[Tracing()])
    app = builder.build()

    assert getattr(app, "_is_instrumented_by_opentelemetry", False)


def test_a_json_log_line_carries_the_request_id() -> None:
    record = logging.LogRecord("shop", logging.INFO, __file__, 1, "placed %s", ("o-1",), None)
    ContextInjectionFilter().filter(record)

    line = json.loads(JsonFormatter().format(record))

    assert (line["message"], line["level"], line["request_id"]) == ("placed o-1", "info", "-")
