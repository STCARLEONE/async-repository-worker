"""Tests for rate limiter."""

import asyncio
import time

import pytest

from async_repository_worker.rate_limiter import RateLimiter, RateLimiterManager, RateLimitStatus


def test_rate_limiter_initialization():
    """Test rate limiter initialization."""
    limiter = RateLimiter(rate=5.0, capacity=10)
    assert limiter.rate == 5.0
    assert limiter.capacity == 10
    assert limiter.available_tokens == 10


def test_rate_limiter_invalid_params():
    """Test rate limiter with invalid parameters."""
    with pytest.raises(ValueError, match="rate must be > 0"):
        RateLimiter(rate=0, capacity=5)

    with pytest.raises(ValueError, match="rate must be > 0"):
        RateLimiter(rate=-1, capacity=5)

    with pytest.raises(ValueError, match="capacity must be >= 1"):
        RateLimiter(rate=5.0, capacity=0)


def test_rate_limiter_acquire():
    """Test acquiring tokens."""
    limiter = RateLimiter(rate=10.0, capacity=5)

    # Should have 5 tokens initially
    assert limiter.available_tokens == 5

    # Acquire all tokens
    for _ in range(5):
        assert limiter.acquire(blocking=False) is True

    # No tokens left
    assert limiter.acquire(blocking=False) is False
    assert limiter.available_tokens < 1


def test_rate_limiter_refill():
    """Test token refill over time."""
    limiter = RateLimiter(rate=10.0, capacity=5)

    # Use all tokens
    for _ in range(5):
        limiter.acquire(blocking=False)

    # Wait for refill
    time.sleep(0.2)  # Should refill ~2 tokens

    # Should have some tokens
    assert limiter.available_tokens >= 2
    assert limiter.acquire(blocking=False) is True


def test_rate_limiter_blocking():
    """Test blocking acquisition."""
    limiter = RateLimiter(rate=10.0, capacity=1)

    # Use the only token
    assert limiter.acquire(blocking=False) is True

    # This should block until a token is available
    start = time.time()
    assert limiter.acquire(blocking=True) is True
    elapsed = time.time() - start

    # Should wait about 0.1 seconds (1/rate)
    assert 0.05 <= elapsed <= 0.3


def test_rate_limiter_timeout():
    """Test acquisition with timeout."""
    limiter = RateLimiter(rate=1.0, capacity=1)

    # Use the only token
    assert limiter.acquire(blocking=False) is True

    # Try to acquire with short timeout
    start = time.time()
    assert limiter.acquire(blocking=True, timeout=0.1) is False
    elapsed = time.time() - start

    # Should timeout after 0.1 seconds
    assert 0.05 <= elapsed <= 0.2


@pytest.mark.asyncio
async def test_rate_limiter_async_acquire():
    """Test async acquisition."""
    limiter = RateLimiter(rate=10.0, capacity=1)

    # Use the only token
    assert await limiter.acquire_async(blocking=False) is True

    # Async block until token available
    start = time.time()
    assert await limiter.acquire_async(blocking=True) is True
    elapsed = time.time() - start

    # Should wait about 0.1 seconds
    assert 0.05 <= elapsed <= 0.3


@pytest.mark.asyncio
async def test_rate_limiter_async_timeout():
    """Test async acquisition with timeout."""
    limiter = RateLimiter(rate=1.0, capacity=1)

    # Use the only token
    assert await limiter.acquire_async(blocking=False) is True

    # Try with timeout
    start = time.time()
    assert await limiter.acquire_async(blocking=True, timeout=0.1) is False
    elapsed = time.time() - start

    assert 0.05 <= elapsed <= 0.2


def test_rate_limiter_update_status():
    """Test updating rate limit status from headers."""
    limiter = RateLimiter(rate=5.0, capacity=5)

    # Initial status
    status = limiter.status
    assert status.remaining is None
    assert status.reset is None
    assert status.retry_after is None

    # Update with GitHub headers
    limiter.update_status(remaining=42, reset=1234567890, retry_after=60)

    status = limiter.status
    assert status.remaining == 42
    assert status.reset == 1234567890
    assert status.retry_after == 60


def test_rate_limiter_status_exhausted():
    """Test rate limit status exhaustion detection."""
    status = RateLimitStatus(remaining=0)
    assert status.is_exhausted is True

    status = RateLimitStatus(remaining=5)
    assert status.is_exhausted is False

    status = RateLimitStatus(remaining=None)
    assert status.is_exhausted is False


def test_rate_limiter_status_reset_in():
    """Test reset time calculation."""
    now = int(time.time())
    status = RateLimitStatus(reset=now + 60)
    assert 50 <= status.reset_in <= 70

    status = RateLimitStatus(reset=now - 10)
    assert status.reset_in == 0


def test_rate_limiter_manager_singleton():
    """Test RateLimiterManager is a singleton."""
    manager1 = RateLimiterManager()
    manager2 = RateLimiterManager()
    assert manager1 is manager2


def test_rate_limiter_manager_get_limiter():
    """Test getting global limiter."""
    limiter1 = RateLimiterManager.get_limiter(rate=10.0, capacity=10)
    limiter2 = RateLimiterManager.get_limiter(rate=20.0, capacity=20)

    # Should return the same limiter with original settings
    assert limiter1 is limiter2
    assert limiter1.rate == 10.0
    assert limiter1.capacity == 10


def test_rate_limiter_manager_reset():
    """Test resetting global limiter."""
    limiter1 = RateLimiterManager.get_limiter(rate=10.0, capacity=10)
    RateLimiterManager.reset()
    limiter2 = RateLimiterManager.get_limiter(rate=20.0, capacity=20)

    # Should be different instances
    assert limiter1 is not limiter2
    assert limiter2.rate == 20.0
    assert limiter2.capacity == 20


@pytest.mark.asyncio
async def test_rate_limiter_context_manager():
    """Test async context manager."""
    limiter = RateLimiter(rate=10.0, capacity=5)

    async with limiter:
        # Should acquire token on enter
        # (but our implementation doesn't auto-acquire on enter)
        pass

    # Should still work
    assert limiter.available_tokens == 5


def test_rate_limiter_repr():
    """Test string representation."""
    limiter = RateLimiter(rate=5.0, capacity=10)
    assert "RateLimiter(rate=5.0, capacity=10" in repr(limiter)


@pytest.mark.asyncio
async def test_concurrent_acquire():
    """Test concurrent acquisition."""
    limiter = RateLimiter(rate=100.0, capacity=10)

    async def acquire_token():
        return await limiter.acquire_async(blocking=False)

    # Try to acquire 20 tokens concurrently (only 10 available)
    tasks = [acquire_token() for _ in range(20)]
    results = await asyncio.gather(*tasks)

    # Should have exactly 10 successes
    assert sum(results) == 10


def test_rate_limiter_thread_safety():
    """Test thread safety (basic)."""
    import threading

    limiter = RateLimiter(rate=100.0, capacity=10)
    results = []
    lock = threading.Lock()

    def acquire():
        result = limiter.acquire(blocking=False)
        with lock:
            results.append(result)

    threads = [threading.Thread(target=acquire) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Should have exactly 10 successes
    assert sum(results) == 10