from __future__ import annotations

from tortoise.backends.base.client import TransactionContext
from tortoise.transactions import in_transaction


class UnitOfWork:
    """Wraps multi-table writes in a single database transaction. Single-row writes skip it."""

    @staticmethod
    def atomic() -> TransactionContext:
        return in_transaction()
