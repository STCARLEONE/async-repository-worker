from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """
    Asynchronous token-bucket rate limiter.

    Controls the rate at which callers are allowed to acquire
    permission to perform an operation.
    """

    def __init__(
        self,
        rate: float,
        capacity: int | None = None,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be greater than zero")

        if capacity is not None and capacity <= 0:
            raise ValueError("capacity must be greater than zero")

        self._rate = rate
        self._capacity = capacity or max(1, int(rate))

        self._tokens = float(self._capacity)
        self._updated_at = time.monotonic()

        self._lock = asyncio.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self._updated_at

        if elapsed <= 0:
            return

        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._rate,
        )

        self._updated_at = now

    async def acquire(self) -> None:
        """
        Wait until one token is available.
        """

        while True:
            async with self._lock:
                now = time.monotonic()
                self._refill(now)

                if self._tokens >= 1:
                    self._tokens -= 1
                    return

                wait_time = (1 - self._tokens) / self._rate

            await asyncio.sleep(wait_time)

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        return None