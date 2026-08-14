import asyncio

import pytest

from async_repository_worker.models import JobStatus, RepositoryJob
from async_repository_worker.queue import PriorityJobQueue
from async_repository_worker.worker import WorkerPool


@pytest.mark.asyncio
async def test_worker_shutdown_waits_for_active_job():
    queue = PriorityJobQueue()

    started = asyncio.Event()
    finished = asyncio.Event()

    async def handler(job: RepositoryJob) -> None:
        started.set()
        await asyncio.sleep(0.1)
        finished.set()

    pool = WorkerPool(
        queue=queue,
        handler=handler,
        workers=1,
    )

    job = RepositoryJob(repository="shutdown/test")

    await pool.start()
    await queue.put(job)

    await started.wait()

    await pool.stop()

    assert finished.is_set()
    assert job.status == JobStatus.SUCCESS