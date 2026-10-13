"""What one module announces and others act on, without it knowing who listens.

A module subscribes in `Module.subscriptions`; whoever publishes waits for every handler,
in boot order. A handler that fails is logged and does not stop the others: one module
leaving its rows behind is no reason for the rest to keep theirs.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
import logging
from typing import Any

log = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


class Events:
    def __init__(self, handlers: Mapping[type, Sequence[tuple[str, Handler]]]) -> None:
        self.handlers = handlers

    async def publish(self, event: object) -> None:
        for module, handler in self.handlers.get(type(event), ()):
            try:
                await handler(event)
            except Exception:
                log.exception("%s could not handle %s", module, type(event).__name__)
