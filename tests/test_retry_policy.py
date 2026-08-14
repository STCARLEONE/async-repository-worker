"""Tests for retry policy."""

import asyncio

import httpx
import pytest

from async_repository_worker.exceptions import (
    GitHubBadRequestError,
    GitHubRateLimitError,
    GitHubServerError,
    GitHubTimeoutError,
)
from async_repository_worker.retry_policy import RetryPolicy, RetryContext


def test_retry_policy_calculate_delay():
    """Test exponential backoff with jitter."""
    policy = RetryPolicy(base_delay=0.5, max_delay=10.0, jitter=False)

    # attempt 1: 0.5 * 2^0 = 0.5
    assert policy.calculate_delay(1) == 0.5

    # attempt 2: 0.5 * 2^1 = 1.0
    assert policy.calculate_delay(2) == 1.0

    # attempt 3: 0.5 * 2^2 = 2.0
    assert policy.calculate_delay(3) == 2.0

    # attempt 4: 0.5 * 2^3 = 4.0
    assert policy.calculate_delay(4) == 4.0


def test_retry_policy_calculate_delay_with_jitter():
    """Test delay calculation with jitter."""
    policy = RetryPolicy(base_delay=0.5, max_delay=10.0, jitter=True)

    for _ in range(10):
        delay = policy.calculate_delay(2)
        # Should be around 1.0 with ±25% jitter (0.75 to 1.25)
        assert 0.5 <= delay <= 1.5


def test_retry_policy_calculate_delay_max():
    """Test delay cap at max_delay."""
    policy = RetryPolicy(base_delay=0.5, max_delay=10.0, jitter=False)

    # attempt 5: 0.5 * 2^4 = 8.0
    assert policy.calculate_delay(5) == 8.0

    # attempt 6: 0.5 * 2^5 = 16.0 -> capped at 10.0
    assert policy.calculate_delay(6) == 10.0

    # attempt 10: capped at 10.0
    assert policy.calculate_delay(10) == 10.0


def test_retry_policy_should_retry():
    """Test retry decision logic."""
    policy = RetryPolicy(max_attempts=3)

    # Retryable errors
    assert policy.should_retry(GitHubRateLimitError("Rate limit"), attempt=1) is True
    assert policy.should_retry(GitHubServerError("Server error"), attempt=1) is True
    assert policy.should_retry(GitHubTimeoutError("Timeout"), attempt=1) is True
    assert policy.should_retry(httpx.TimeoutException("Timeout"), attempt=1) is True
    assert policy.should_retry(httpx.ConnectError("Connect"), attempt=1) is True

    # Non-retryable errors
    assert policy.should_retry(GitHubBadRequestError("Bad request"), attempt=1) is False


def test_retry_policy_should_retry_max_attempts():
    """Test max attempts limit."""
    policy = RetryPolicy(max_attempts=3)

    # Within limit
    assert policy.should_retry(GitHubRateLimitError("Rate limit"), attempt=1) is True
    assert policy.should_retry(GitHubRateLimitError("Rate limit"), attempt=2) is True

    # Exceeded limit
    assert policy.should_retry(GitHubRateLimitError("Rate limit"), attempt=3) is False
    assert policy.should_retry(GitHubRateLimitError("Rate limit"), attempt=4) is False


@pytest.mark.asyncio
async def test_retry_context_success_first_attempt():
    """Test retry context with successful first attempt."""
    policy = RetryPolicy(max_attempts=3)
    context = RetryContext(policy)

    call_count = 0

    async def success_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await context.execute(success_func)

    assert result == "success"
    assert call_count == 1
    assert context.attempt == 1
    assert context.last_error is None


@pytest.mark.asyncio
async def test_retry_context_retry_on_retryable_error():
    """Test retry context retries on retryable errors."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.1)
    context = RetryContext(policy)

    call_count = 0

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise GitHubRateLimitError("Rate limit")
        return "success"

    result = await context.execute(flaky_func)

    assert result == "success"
    assert call_count == 3
    assert context.attempt == 3
    assert isinstance(context.last_error, GitHubRateLimitError)


@pytest.mark.asyncio
async def test_retry_context_no_retry_on_non_retryable():
    """Test retry context does not retry on non-retryable errors."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.1)
    context = RetryContext(policy)

    call_count = 0

    async def failing_func():
        nonlocal call_count
        call_count += 1
        raise GitHubBadRequestError("Bad request")

    with pytest.raises(GitHubBadRequestError):
        await context.execute(failing_func)

    assert call_count == 1  # Only one attempt
    assert context.attempt == 1


@pytest.mark.asyncio
async def test_retry_context_exhaust_attempts():
    """Test retry context exhausts all attempts."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.1)
    context = RetryContext(policy)

    call_count = 0

    async def always_fail():
        nonlocal call_count
        call_count += 1
        raise GitHubRateLimitError("Rate limit")

    with pytest.raises(GitHubRateLimitError):
        await context.execute(always_fail)

    assert call_count == 3  # max_attempts
    assert context.attempt == 3
    assert isinstance(context.last_error, GitHubRateLimitError)


@pytest.mark.asyncio
async def test_retry_context_delays():
    """Test that retry context actually sleeps between attempts."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.1, max_delay=1.0, jitter=False)
    context = RetryContext(policy)

    call_count = 0
    start_time = asyncio.get_event_loop().time()

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise GitHubRateLimitError("Rate limit")
        return "success"

    await context.execute(flaky_func)

    elapsed = asyncio.get_event_loop().time() - start_time
    assert elapsed >= 0.25
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_context_with_different_errors():
    """Test retry context handles different error types."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.1)
    context = RetryContext(policy)

    call_count = 0

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.TimeoutException("Timeout")
        if call_count == 2:
            raise GitHubServerError("Server error", status_code=500)
        return "success"

    result = await context.execute(flaky_func)

    assert result == "success"
    assert call_count == 3
    assert isinstance(context.last_error, GitHubServerError)


@pytest.mark.asyncio
async def test_retry_context_representation():
    """Test retry context string representation."""
    policy = RetryPolicy(max_attempts=3)
    context = RetryContext(policy)

    assert "RetryContext(attempt=0, last_error=None)" in repr(context)

    try:
        async def fail():
            raise ValueError("test")
        await context.execute(fail)
    except ValueError:
        pass

    assert "attempt=1" in repr(context)
    assert "last_error=test" in repr(context)