from __future__ import annotations

from collections.abc import Callable
import time

from fastapi import Request

from .errors import RateLimitedError


class TooManyAttemptsError(RateLimitedError):
    """Too many attempts at something guessable, from one address or at one account."""

    code = "too_many_attempts"

    def __init__(self) -> None:
        super().__init__("too many attempts; wait a few minutes and try again")


class Throttle:
    """How many times something may be tried in a window, per key.

    Kept in memory: one process serves the API, and what this stops is somebody trying
    passwords or codes by the thousand, which a restart does not help them with. A key is
    an address or an account, so a slow guesser from many addresses still meets the
    account's limit, and one address cannot walk through many accounts.
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self.clock = clock or time.monotonic
        self.hits: dict[str, list[float]] = {}

    def admit(self, key: str, limit: int, window: float) -> None:
        now = self.clock()
        recent = [moment for moment in self.hits.get(key, []) if now - moment < window]
        if len(recent) >= limit:
            self.hits[key] = recent
            raise TooManyAttemptsError()
        self.hits[key] = [*recent, now]
        if len(self.hits) > 50_000:
            self.forget_older_than(now - window)

    def forget_older_than(self, cutoff: float) -> None:
        self.hits = {key: moments for key, moments in self.hits.items() if moments and moments[-1] >= cutoff}


class ClientAddress:
    """Who is asking, as far as a throttle can tell."""

    @staticmethod
    def client_address(request: Request) -> str:
        """The address a request came from. Behind the proxy, the one it put first in
        `X-Forwarded-For`; the proxy replaces whatever the client sent there."""
        forwarded = request.headers.get("x-forwarded-for", "")
        return forwarded.split(",")[0].strip() or (request.client.host if request.client else "")
