"""Rate limiter with token bucket algorithm for GitHub API."""

import asyncio
import time
from dataclasses import dataclass
from threading import Lock
from typing import Optional


@dataclass
class RateLimitStatus:
    """Current rate limit status."""

    remaining: Optional[int] = None
    reset: Optional[int] = None  # Unix timestamp
    retry_after: Optional[int] = None  # seconds

    @property
    def is_exhausted(self) -> bool:
        """Check if rate limit is exhausted."""
        if self.remaining is not None:
            return self.remaining <= 0
        return False

    @property
    def reset_in(self) -> Optional[float]:
        """Seconds until rate limit resets."""
        if self.reset is not None:
            return max(0, self.reset - time.time())
        return None


class RateLimiter:
    """
    Token bucket rate limiter with GitHub-specific support.

    This limiter is thread-safe and async-safe.
    """

    def __init__(self, rate: float, capacity: int):
        """
        Initialize rate limiter.

        Args:
            rate: Tokens added per second (e.g., 5.0 for 5 requests/sec)
            capacity: Maximum tokens in bucket (burst capacity)
        """
        if rate <= 0:
            raise ValueError("rate must be > 0")
        if capacity < 1:
            raise ValueError("capacity must be >= 1")

        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = Lock()

        # GitHub-specific tracking
        self._status = RateLimitStatus()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last_refill = now

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token from the bucket.

        Args:
            blocking: If True, block until token available
            timeout: Maximum time to wait in seconds

        Returns:
            True if token acquired, False if timeout or non-blocking
        """
        with self._lock:
            self._refill()

            if self._tokens >= 1:
                self._tokens -= 1
                return True

            if not blocking:
                return False

            if timeout is not None and timeout <= 0:
                return False

        # Wait for token (outside lock to allow refills)
        start = time.monotonic()
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True

                # Calculate wait time for next token
                wait_time = (1 - self._tokens) / self.rate if self._tokens < 1 else 0.1

                if timeout is not None:
                    elapsed = time.monotonic() - start
                    if elapsed >= timeout:
                        return False
                    wait_time = min(wait_time, timeout - elapsed)

                # Sleep outside lock to allow other threads
                if wait_time > 0:
                    time.sleep(max(0.001, wait_time * 0.9))  # Small sleep to avoid busy waiting

    async def acquire_async(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Async version of acquire.

        Args:
            blocking: If True, block until token available
            timeout: Maximum time to wait in seconds

        Returns:
            True if token acquired, False if timeout or non-blocking
        """
        with self._lock:
            self._refill()
            if self._tokens >= 1:
                self._tokens -= 1
                return True

            if not blocking:
                return False

            if timeout is not None and timeout <= 0:
                return False

        # Wait for token (outside lock to allow refills)
        start = time.monotonic()
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True

                wait_time = (1 - self._tokens) / self.rate if self._tokens < 1 else 0.1

                if timeout is not None:
                    elapsed = time.monotonic() - start
                    if elapsed >= timeout:
                        return False
                    wait_time = min(wait_time, timeout - elapsed)

                if wait_time > 0:
                    await asyncio.sleep(max(0.001, wait_time * 0.9))

    def update_status(self, remaining: Optional[int], reset: Optional[int], retry_after: Optional[int] = None) -> None:
        """Update rate limit status from GitHub headers."""
        with self._lock:
            if remaining is not None:
                self._status.remaining = remaining
            if reset is not None:
                self._status.reset = reset
            if retry_after is not None:
                self._status.retry_after = retry_after

    @property
    def status(self) -> RateLimitStatus:
        """Get current rate limit status."""
        with self._lock:
            return RateLimitStatus(
                remaining=self._status.remaining,
                reset=self._status.reset,
                retry_after=self._status.retry_after,
            )

    @property
    def available_tokens(self) -> float:
        """Get number of available tokens."""
        with self._lock:
            self._refill()
            return self._tokens

    async def __aenter__(self) -> "RateLimiter":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        pass

    def __repr__(self) -> str:
        return f"RateLimiter(rate={self.rate}, capacity={self.capacity}, tokens={self.available_tokens:.2f})"


class RateLimiterManager:
    """
    Manager for rate limiters that can be shared across workers.

    This provides a global rate limiter that can be used by all workers.
    """

    _instance: Optional["RateLimiterManager"] = None
    _limiter: Optional[RateLimiter] = None
    _lock = Lock()

    def __new__(cls) -> "RateLimiterManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_limiter(cls, rate: float = 5.0, capacity: int = 5) -> RateLimiter:
        """Get or create the global rate limiter."""
        if cls._limiter is None:
            with cls._lock:
                if cls._limiter is None:
                    cls._limiter = RateLimiter(rate=rate, capacity=capacity)
        return cls._limiter

    @classmethod
    def reset(cls) -> None:
        """Reset the global rate limiter (for testing)."""
        with cls._lock:
            cls._limiter = None