"""Events that are not lost when the process stops before delivering them.

`Outbox.add(event)` writes the event in the same transaction as the change it announces,
and the outbox module's relay publishes it afterwards, so either both happen or neither
does. Delivery is at least once: a handler may see an event twice and must not mind.

The application lists `OutboxModule()` among its modules and adds
`OutboxModule.table()` to one of its migrations; the table is `kernel_outbox`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import FastAPI
import msgspec
from tortoise import fields
from tortoise.migrations import operations as ops
from tortoise.models import Model

from .events import Events
from .periodic import Periodic
from .registry import Listener, Module

TABLE = "kernel_outbox"
RELAY_EVERY_SECONDS = 1.0
BATCH = 100


class OutboxModel(Model):
    id = fields.BigIntField(primary_key=True)
    name = fields.CharField(max_length=255)
    payload = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    delivered_at = fields.DatetimeField(null=True, db_index=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        table = TABLE


class Outbox:
    def __init__(self, events: Events) -> None:
        self.events = events

    async def add(self, event: object) -> None:
        await OutboxModel.create(name=Events.name_of(type(event)), payload=msgspec.json.encode(event).decode())

    async def relay(self) -> int:
        """Publish what is waiting, oldest first, and mark each as delivered once it is."""
        waiting = await OutboxModel.filter(delivered_at__isnull=True).order_by("id").limit(BATCH)
        for row in waiting:
            kind = self.events.kinds.get(row.name)
            if kind is not None:
                await self.events.publish(msgspec.json.decode(row.payload, type=kind))
            row.delivered_at = datetime.now(UTC)
            await row.save(update_fields=["delivered_at"])
        return len(waiting)


class OutboxModule(Module):
    name = "outbox"
    orm_model_modules = ("dooservice_kernel.outbox",)
    provides = (Outbox,)

    async def on_startup(self, app: FastAPI) -> None:
        app.state.ports.provide(Outbox, Outbox(app.state.events))

    def listeners(self, app: FastAPI) -> Sequence[Listener]:
        return (Periodic("outbox relay", app.state.ports.get(Outbox).relay, every=RELAY_EVERY_SECONDS),)

    @staticmethod
    def table() -> ops.CreateModel:
        """The migration operation that creates `kernel_outbox`, for the application's own."""
        return ops.CreateModel(
            name="OutboxModel",
            fields=[
                ("id", fields.BigIntField(primary_key=True)),
                ("name", fields.CharField(max_length=255)),
                ("payload", fields.TextField()),
                ("created_at", fields.DatetimeField(auto_now_add=True)),
                ("delivered_at", fields.DatetimeField(null=True, db_index=True)),
            ],
            options={"table": TABLE, "app": "models", "pk_attr": "id"},
        )
