import pytest

from async_repository_worker.limiter import RateLimiter
from async_repository_worker.models import JobPriority, JobStatus, RepositoryJob
from async_repository_worker.queue import PriorityJobQueue
from async_repository_worker.worker import WorkerPool


@pytest.mark.asyncio
async def test_worker_pipeline():
    queue = PriorityJobQueue()
    limiter = RateLimiter(rate=100, capacity=100)

    processed: list[str] = []

    async def handler(job: RepositoryJob) -> None:
        async with limiter:
            processed.append(job.repository)

    jobs = [
        RepositoryJob(
            repository="repo-low",
            priority=JobPriority.LOW,
        ),
        RepositoryJob(
            repository="repo-critical",
            priority=JobPriority.CRITICAL,
        ),
        RepositoryJob(
            repository="repo-high",
            priority=JobPriority.HIGH,
        ),
    ]

    pool = WorkerPool(
        queue=queue,
        handler=handler,
        workers=1,
    )

    await pool.start()

    for job in jobs:
        await queue.put(job)

    await pool.wait()
    await pool.stop()

    assert processed == [
        "repo-critical",
        "repo-high",
        "repo-low",
    ]

    assert all(job.status == JobStatus.SUCCESS for job in jobs)
