"""What one module announces and others act on, without it knowing who listens.

A module subscribes in `Module.subscriptions`; whoever publishes waits for every handler,
in boot order. A handler that fails is logged and does not stop the others: one module
leaving its rows behind is no reason for the rest to keep theirs.

With a bridge, an event published in one process also reaches the handlers of every
other process sharing it; an event arriving from the bridge is delivered here only.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
import logging
from typing import Any, Protocol

import msgspec

log = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


class EventBridge(Protocol):
    """Carries events between processes: `send` hands one over, and the bridge calls the
    receiver it was given for each one another process sent."""

    def receive_with(self, receiver: Callable[[str, bytes], Awaitable[None]]) -> None: ...

    async def send(self, name: str, payload: bytes) -> None: ...


class Events:
    def __init__(
        self, handlers: Mapping[type, Sequence[tuple[str, Handler]]], bridge: EventBridge | None = None
    ) -> None:
        self.handlers = handlers
        self.kinds = {self.name_of(kind): kind for kind in handlers}
        self.bridge = bridge
        if bridge is not None:
            bridge.receive_with(self.received)

    @staticmethod
    def name_of(kind: type) -> str:
        return f"{kind.__module__}.{kind.__qualname__}"

    async def publish(self, event: object) -> None:
        await self.deliver(event)
        if self.bridge is not None:
            await self.bridge.send(self.name_of(type(event)), msgspec.json.encode(event))

    async def deliver(self, event: object) -> None:
        for module, handler in self.handlers.get(type(event), ()):
            try:
                await handler(event)
            except Exception:
                log.exception("%s could not handle %s", module, type(event).__name__)

    async def received(self, name: str, payload: bytes) -> None:
        """An event another process published; one nobody here subscribes to is dropped."""
        kind = self.kinds.get(name)
        if kind is not None:
            await self.deliver(msgspec.json.decode(payload, type=kind))
