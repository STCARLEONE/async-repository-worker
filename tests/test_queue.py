import pytest

from async_repository_worker.models import JobPriority, RepositoryJob
from async_repository_worker.queue import PriorityJobQueue


@pytest.mark.asyncio
async def test_priority_order():
    queue = PriorityJobQueue()

    await queue.put(
        RepositoryJob(
            repository="low/repository",
            priority=JobPriority.LOW,
        )
    )

    await queue.put(
        RepositoryJob(
            repository="critical/repository",
            priority=JobPriority.CRITICAL,
        )
    )

    await queue.put(
        RepositoryJob(
            repository="high/repository",
            priority=JobPriority.HIGH,
        )
    )

    first = await queue.get()
    second = await queue.get()
    third = await queue.get()

    assert first.repository == "critical/repository"
    assert second.repository == "high/repository"
    assert third.repository == "low/repository"

    queue.task_done()
    queue.task_done()
    queue.task_done()