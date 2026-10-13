from __future__ import annotations

import asyncio

from dooservice_kernel.periodic import Periodic


async def test_it_runs_on_its_timer_and_keeps_going_after_a_failure() -> None:
    calls: list[int] = []

    async def work() -> None:
        calls.append(len(calls))
        if len(calls) == 1:
            raise RuntimeError("first run fails")

    periodic = Periodic("sweep", work, every=0.01, jitter=0)
    await periodic.start()
    await asyncio.sleep(0.08)
    await periodic.stop()

    assert len(calls) >= 3
    assert periodic.failures == 1
    assert periodic.task is None


async def test_the_first_run_waits_for_first_after() -> None:
    calls: list[int] = []

    async def work() -> None:
        calls.append(1)

    periodic = Periodic("late", work, every=10, first_after=10)
    await periodic.start()
    await asyncio.sleep(0.02)
    await periodic.stop()

    assert calls == []
