"""Events kept in the outbox until delivered, carried between processes over Redis, and
attempts counted across processes; the Redis ones run when `KERNEL_TEST_REDIS` names one."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import os
import uuid

from fastapi import FastAPI
import msgspec
import pytest
from redis.asyncio import Redis
from tortoise import Tortoise

from dooservice_kernel.events import Events, Handler
from dooservice_kernel.outbox import Outbox, OutboxModel, OutboxModule
from dooservice_kernel.ports import Ports
from dooservice_kernel.redis_bridge import RedisEventBridge
from dooservice_kernel.redis_throttle import RedisThrottle
from dooservice_kernel.registry import Module, ModuleRegistry
from dooservice_kernel.throttle import TooManyAttemptsError

REDIS = os.environ.get("KERNEL_TEST_REDIS", "")
needs_redis = pytest.mark.skipif(not REDIS, reason="set KERNEL_TEST_REDIS to run against Redis")


class Shipped(msgspec.Struct, frozen=True):
    order: int


class Warehouse(Module):
    name = "warehouse"

    def __init__(self) -> None:
        self.shipped: list[int] = []

    def subscriptions(self) -> Mapping[type, Handler]:
        return {Shipped: self.note}

    async def note(self, event: Shipped) -> None:
        self.shipped.append(event.order)


async def test_an_event_in_the_outbox_is_published_once_by_the_relay() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["dooservice_kernel.outbox"]})
    await Tortoise.generate_schemas()
    try:
        warehouse = Warehouse()
        registry = ModuleRegistry([OutboxModule(), warehouse])
        app = FastAPI()
        app.state.events, app.state.ports = registry.events(), Ports()
        await registry.run_startup(app)
        outbox = app.state.ports.get(Outbox)

        await outbox.add(Shipped(7))
        first, second = await outbox.relay(), await outbox.relay()

        assert (first, second, warehouse.shipped) == (1, 0, [7])
        assert await OutboxModel.filter(delivered_at__isnull=True).count() == 0
    finally:
        await Tortoise.close_connections()


@needs_redis
async def test_an_event_published_in_one_process_reaches_the_other_and_not_itself_twice() -> None:
    channel = f"test.{uuid.uuid4().hex}"
    here, there = Warehouse(), Warehouse()
    bridges = [RedisEventBridge(REDIS, channel), RedisEventBridge(REDIS, channel)]
    sender = ModuleRegistry([here]).events(bridges[0])
    ModuleRegistry([there]).events(bridges[1])
    for bridge in bridges:
        await bridge.connect()
    try:
        await asyncio.sleep(0.1)
        await sender.publish(Shipped(3))
        await asyncio.sleep(0.2)
        assert (here.shipped, there.shipped) == ([3], [3])
        assert all(bridge.ready() for bridge in bridges)
    finally:
        for bridge in bridges:
            await bridge.close()


@needs_redis
async def test_attempts_are_counted_across_processes() -> None:
    key = f"login:{uuid.uuid4().hex}"
    one, two = Redis.from_url(REDIS), Redis.from_url(REDIS)
    try:
        await RedisThrottle(one).admit(key, limit=2, window=60)
        await RedisThrottle(two).admit(key, limit=2, window=60)
        with pytest.raises(TooManyAttemptsError):
            await RedisThrottle(one).admit(key, limit=2, window=60)
    finally:
        await one.aclose()
        await two.aclose()


def test_events_know_the_kinds_they_can_receive() -> None:
    events = ModuleRegistry([Warehouse()]).events()

    assert events.kinds == {Events.name_of(Shipped): Shipped}
