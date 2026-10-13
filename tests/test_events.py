from __future__ import annotations

from collections.abc import Mapping

import msgspec

from dooservice_kernel.events import Handler
from dooservice_kernel.registry import Module, ModuleRegistry


class OrderPlaced(msgspec.Struct, frozen=True):
    number: int


class Broken(Module):
    name = "broken"

    def subscriptions(self) -> Mapping[type, Handler]:
        return {OrderPlaced: self.fail}

    async def fail(self, event: OrderPlaced) -> None:
        raise RuntimeError("down")


class Ledger(Module):
    name = "ledger"

    def __init__(self) -> None:
        self.seen: list[int] = []

    def subscriptions(self) -> Mapping[type, Handler]:
        return {OrderPlaced: self.record}

    async def record(self, event: OrderPlaced) -> None:
        self.seen.append(event.number)


async def test_every_subscriber_hears_an_event_even_after_one_fails() -> None:
    ledger = Ledger()
    events = ModuleRegistry([Broken(), ledger]).events()

    await events.publish(OrderPlaced(7))

    assert ledger.seen == [7]


async def test_an_event_nobody_subscribed_to_goes_nowhere() -> None:
    await ModuleRegistry([]).events().publish(OrderPlaced(1))
