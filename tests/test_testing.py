from __future__ import annotations

from fastapi import APIRouter

from dooservice_kernel.registry import Module
from dooservice_kernel.testing import FakeBoundary, KernelHarness


class Pinger(Module):
    name = "pinger"

    def __init__(self) -> None:
        router = APIRouter()
        router.add_api_route("/ping", self.ping, methods=["GET"])
        self.routers = (router,)

    async def ping(self) -> dict[str, str]:
        return {"pong": "yes"}


async def test_a_module_is_tested_in_a_few_lines(kernel_harness: type[KernelHarness]) -> None:
    bus = FakeBoundary("bus")
    async with kernel_harness([Pinger()], boundaries=[bus]) as app:
        pong = await app.client.get("/api/ping")
        bus.up = False
        down = await app.client.get("/health/ready")

    assert pong.json() == {"pong": "yes"}
    assert (down.status_code, down.json()["code"]) == (503, "fake_boundary_down")
