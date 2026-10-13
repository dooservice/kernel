"""Work a module does on a timer, as a listener the kernel starts and stops.

Every sweep was the same loop: sleep, try the work, log what failed, sleep again. Here
it is once. `first_after` is the wait before the first run, so a sweep that touches
everything does not run on top of the boot; `jitter` spreads the runs, so two processes
started together do not hit the same rows at the same instant.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import contextlib
import logging
import random

log = logging.getLogger(__name__)


class Periodic:
    def __init__(
        self,
        name: str,
        work: Callable[[], Awaitable[object]],
        every: float,
        first_after: float = 0.0,
        jitter: float = 0.1,
    ) -> None:
        self.name = name
        self.work = work
        self.every = every
        self.first_after = first_after
        self.jitter = jitter
        self.task: asyncio.Task | None = None
        self.runs = 0
        self.failures = 0

    async def start(self) -> None:
        self.task = asyncio.create_task(self.loop(), name=self.name)

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
            self.task = None

    def pause(self) -> float:
        return self.every * (1 + random.uniform(-self.jitter, self.jitter))

    async def loop(self) -> None:
        await asyncio.sleep(self.first_after)
        while True:
            await self.run_once()
            await asyncio.sleep(self.pause())

    async def run_once(self) -> None:
        try:
            await self.work()
        except Exception:
            self.failures += 1
            log.exception("%s failed", self.name)
        finally:
            self.runs += 1
