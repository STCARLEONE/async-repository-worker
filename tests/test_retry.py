import pytest

from async_repository_worker.retry import (
    RetryExhaustedError,
    retry,
)


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    calls = 0

    @retry(
        attempts=3,
        base_delay=0,
        jitter=0,
    )
    async def operation():
        nonlocal calls
        calls += 1

        if calls < 3:
            raise RuntimeError("temporary failure")

        return "success"

    result = await operation()

    assert result == "success"
    assert calls == 3


@pytest.mark.asyncio
async def test_retry_exhausts_attempts():
    calls = 0

    @retry(
        attempts=3,
        base_delay=0,
        jitter=0,
    )
    async def operation():
        nonlocal calls
        calls += 1
        raise RuntimeError("permanent failure")

    with pytest.raises(RetryExhaustedError):
        await operation()

    assert calls == 3


@pytest.mark.asyncio
async def test_retry_preserves_return_value():
    @retry(
        attempts=2,
        base_delay=0,
        jitter=0,
    )
    async def operation():
        return {"status": "ok"}

    result = await operation()

    assert result == {"status": "ok"}