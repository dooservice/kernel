"""Prometheus metrics, as an extension: `ApplicationBuilder(extensions=[Metrics()])`,
with the `metrics` extra installed.

`/metrics` answers how many requests each route took, by method and status, how long
they took, and whether each boundary is ready. A route is counted by its template
(`/api/orders/{order_id}`), never by the path asked for, so ids do not make one series each.
"""

from __future__ import annotations

from collections.abc import Sequence
import time

from fastapi import APIRouter, FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .health import Boundary


class Metrics:
    def __init__(self) -> None:
        self.boundaries: Sequence[Boundary] = ()
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "http_requests", "Requests answered", ["method", "route", "status"], registry=self.registry
        )
        self.seconds = Histogram("http_request_seconds", "Time to answer", ["method", "route"], registry=self.registry)
        self.ready = Gauge("boundary_ready", "Whether a boundary is ready", ["boundary"], registry=self.registry)

    def install(self, app: FastAPI, boundaries: Sequence[Boundary]) -> None:
        self.boundaries = boundaries
        router = APIRouter(tags=["metrics"])
        router.add_api_route("/metrics", self.scrape, methods=["GET"], include_in_schema=False)
        app.include_router(router)
        app.add_middleware(MetricsMiddleware, metrics=self)

    async def scrape(self) -> Response:
        for boundary in self.boundaries:
            self.ready.labels(getattr(boundary, "name", type(boundary).__name__)).set(1 if boundary.ready() else 0)
        return Response(generate_latest(self.registry), media_type=CONTENT_TYPE_LATEST)


class MetricsMiddleware:
    def __init__(self, app: ASGIApp, metrics: Metrics) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return
        status = {"code": 500}
        started = time.perf_counter()

        async def recorded(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, recorded)
        finally:
            route = self.template(scope)
            self.metrics.requests.labels(scope["method"], route, str(status["code"])).inc()
            self.metrics.seconds.labels(scope["method"], route).observe(time.perf_counter() - started)

    @staticmethod
    def template(scope: Scope) -> str:
        """The route as written, its prefix included: an included router keeps its own
        path, so the prefix is what the request path has before the part the route matched."""
        route = scope.get("route")
        if route is None:
            return "unmatched"
        path = scope["path"]
        for start in range(len(path) + 1):
            if route.path_regex.fullmatch(path[start:]):
                return path[:start] + route.path
        return route.path
