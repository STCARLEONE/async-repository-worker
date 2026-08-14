from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar


P = ParamSpec("P")
T = TypeVar("T")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have failed."""


def retry(
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[
    [Callable[P, Awaitable[T]]],
    Callable[P, Awaitable[T]],
]:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    if base_delay < 0:
        raise ValueError("base_delay cannot be negative")

    if max_delay < base_delay:
        raise ValueError("max_delay must be >= base_delay")

    if jitter < 0:
        raise ValueError("jitter cannot be negative")

    def decorator(
        func: Callable[P, Awaitable[T]],
    ) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: Exception | None = None

            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)

                except exceptions as exc:
                    last_error = exc

                    if attempt == attempts - 1:
                        break

                    delay = min(
                        base_delay * (2**attempt),
                        max_delay,
                    )

                    if jitter:
                        delay += random.uniform(0, jitter)

                    await asyncio.sleep(delay)

            raise RetryExhaustedError(
                f"{func.__name__} failed after {attempts} attempts"
            ) from last_error

        return wrapper

    return decorator