"""`Throttle` with its counts in Redis (the `redis` extra), so that every process of the
service shares them: an attempt counted by one is counted by all.

Same rule as the in-memory one: at most `limit` attempts per key in any `window` of
seconds, the oldest falling out as time passes.
"""

from __future__ import annotations

import time
import uuid

from redis.asyncio import Redis

from .constants import PREFIX
from .throttle import TooManyAttemptsError


class RedisThrottle:
    def __init__(self, redis: Redis, prefix: str = PREFIX) -> None:
        self.redis = redis
        self.prefix = prefix

    async def admit(self, key: str, limit: int, window: float) -> None:
        name = self.prefix + key
        now = time.time()
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(name, 0, now - window)
            pipe.zcard(name)
            _, recent = await pipe.execute()
        if recent >= limit:
            raise TooManyAttemptsError()
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zadd(name, {uuid.uuid4().hex: now})
            pipe.expire(name, int(window) + 1)
            await pipe.execute()
