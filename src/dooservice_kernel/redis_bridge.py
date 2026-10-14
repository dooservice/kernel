"""Events between processes over Redis pub/sub (the `redis` extra), as a boundary and
an event bridge at once:

    bridge = RedisEventBridge("redis://cache:6379/0")
    ApplicationBuilder(config, modules, boundaries=[bridge], bridge=bridge)

Every process subscribes to one channel. Each message carries the process it came from,
so a process does not deliver its own events twice; delivery is at most once, as pub/sub
is: for events that must not be lost, publish them through the outbox.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import contextlib
import logging
import uuid

import msgspec
from redis.asyncio import Redis

from .constants import CHANNEL
from .errors import DomainError, UnavailableError

log = logging.getLogger(__name__)


class BridgeDownError(UnavailableError):
    code = "event_bridge_down"
    title = "Event Bridge Down"


class Envelope(msgspec.Struct, frozen=True):
    origin: str
    name: str
    payload: bytes


class RedisEventBridge:
    name = "redis events"

    def __init__(self, url: str, channel: str = CHANNEL) -> None:
        self.url = url
        self.channel = channel
        self.origin = uuid.uuid4().hex
        self.redis: Redis | None = None
        self.receiver: Callable[[str, bytes], Awaitable[None]] | None = None
        self.task: asyncio.Task | None = None

    def receive_with(self, receiver: Callable[[str, bytes], Awaitable[None]]) -> None:
        self.receiver = receiver

    async def connect(self) -> None:
        self.redis = Redis.from_url(self.url)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.channel)
        self.task = asyncio.create_task(self.listen(pubsub))

    async def listen(self, pubsub) -> None:
        async for message in pubsub.listen():
            if message["type"] != "message" or self.receiver is None:
                continue
            envelope = msgspec.msgpack.decode(message["data"], type=Envelope)
            if envelope.origin == self.origin:
                continue
            try:
                await self.receiver(envelope.name, envelope.payload)
            except Exception:
                log.exception("an event from another process could not be delivered")

    async def send(self, name: str, payload: bytes) -> None:
        if self.redis is not None:
            await self.redis.publish(self.channel, msgspec.msgpack.encode(Envelope(self.origin, name, payload)))

    async def close(self) -> None:
        if self.task is not None:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        if self.redis is not None:
            await self.redis.aclose()

    def ready(self) -> bool:
        return self.task is not None and not self.task.done()

    def unavailable(self) -> DomainError:
        return BridgeDownError("events cannot reach the other processes")
