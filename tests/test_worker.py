import asyncio

import pytest

from async_repository_worker.models import JobPriority, JobStatus, RepositoryJob
from async_repository_worker.queue import PriorityJobQueue
from async_repository_worker.worker import WorkerPool


@pytest.mark.asyncio
async def test_worker_processes_jobs():
    queue = PriorityJobQueue()
    processed = []

    async def handler(job: RepositoryJob):
        processed.append(job.repository)

    pool = WorkerPool(
        queue=queue,
        handler=handler,
        workers=2,
    )

    await pool.start()

    await queue.put(
        RepositoryJob(
            repository="test/repository",
            priority=JobPriority.HIGH,
        )
    )

    await pool.wait()
    await pool.stop()

    assert processed == ["test/repository"]


@pytest.mark.asyncio
async def test_worker_marks_success():
    queue = PriorityJobQueue()

    async def handler(job: RepositoryJob):
        await asyncio.sleep(0)

    pool = WorkerPool(
        queue=queue,
        handler=handler,
        workers=1,
    )

    job = RepositoryJob(repository="test/repository")

    await pool.start()
    await queue.put(job)

    await pool.wait()
    await pool.stop()

    assert job.status == JobStatus.SUCCESS
    assert job.started_at is not None
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_worker_marks_failed_job():
    queue = PriorityJobQueue()

    async def handler(job: RepositoryJob):
        raise RuntimeError("test failure")

    pool = WorkerPool(
        queue=queue,
        handler=handler,
        workers=1,
    )

    job = RepositoryJob(repository="test/repository")

    await pool.start()
    await queue.put(job)

    await pool.wait()
    await pool.stop()

    assert job.status == JobStatus.FAILED
    assert job.error == "test failure"
