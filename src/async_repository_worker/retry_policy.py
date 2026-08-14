"""Smart retry policy with exponential backoff and jitter."""

import asyncio
import random
from dataclasses import dataclass
from typing import Optional, TypeVar

from .exceptions import is_retryable_error

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 0.5  # seconds
    max_delay: float = 30.0  # seconds
    jitter: bool = True

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter."""
        if attempt <= 0:
            return 0.0

        # Exponential backoff: base_delay * 2^(attempt-1)
        delay = self.base_delay * (2 ** (attempt - 1))

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter (random ±25%)
        if self.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay)  # Ensure positive delay

        return delay

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if a retry should be attempted."""
        # Check if max attempts exceeded
        if attempt >= self.max_attempts:
            return False

        # Check if error is retryable
        return is_retryable_error(error)


class RetryContext:
    """Context manager for retry operations."""

    def __init__(self, policy: RetryPolicy):
        self.policy = policy
        self.attempt = 0
        self.last_error: Optional[Exception] = None

    async def execute(self, func, *args, **kwargs):
        """Execute a function with retry logic."""
        while True:
            self.attempt += 1
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.last_error = e
                if not self.policy.should_retry(e, self.attempt):
                    raise

                delay = self.policy.calculate_delay(self.attempt)
                await asyncio.sleep(delay)

    def __repr__(self) -> str:
        return f"RetryContext(attempt={self.attempt}, last_error={self.last_error})"