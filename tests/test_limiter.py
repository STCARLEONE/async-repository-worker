import asyncio

import pytest

from async_repository_worker.limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_initial_capacity():
    limiter = RateLimiter(
        rate=10,
        capacity=2,
    )

    start = asyncio.get_running_loop().time()

    await limiter.acquire()
    await limiter.acquire()

    elapsed = asyncio.get_running_loop().time() - start

    assert elapsed < 0.2


@pytest.mark.asyncio
async def test_rate_limiter_delays_when_empty():
    limiter = RateLimiter(
        rate=10,
        capacity=1,
    )

    await limiter.acquire()

    start = asyncio.get_running_loop().time()

    await limiter.acquire()

    elapsed = asyncio.get_running_loop().time() - start

    assert elapsed >= 0.05


@pytest.mark.asyncio
async def test_rate_limiter_supports_context_manager():
    limiter = RateLimiter(
        rate=10,
        capacity=1,
    )

    async with limiter:
        pass
