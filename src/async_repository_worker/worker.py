from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from .models import RepositoryJob
from .queue import PriorityJobQueue


logger = logging.getLogger(__name__)

JobHandler = Callable[[RepositoryJob], Awaitable[None]]


class WorkerPool:
    def __init__(
        self,
        queue: PriorityJobQueue,
        handler: JobHandler,
        workers: int = 4,
    ) -> None:
        if workers < 1:
            raise ValueError("workers must be at least 1")

        self._queue = queue
        self._handler = handler
        self._worker_count = workers
        self._tasks: list[asyncio.Task[None]] = []
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._tasks:
            raise RuntimeError("worker pool is already running")

        self._stopping.clear()

        self._tasks = [
            asyncio.create_task(
                self._worker(index),
                name=f"repository-worker-{index}",
            )
            for index in range(self._worker_count)
        ]

    async def stop(self) -> None:
        self._stopping.set()

        if not self._tasks:
            return

        await self._queue.join()

        await asyncio.gather(
            *self._tasks,
            return_exceptions=True,
        )

        self._tasks.clear()

    async def wait(self) -> None:
        await self._queue.join()

    async def _worker(self, worker_id: int) -> None:
        while not self._stopping.is_set():
            try:
                job = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=0.5,
                )
            except asyncio.TimeoutError:
                continue

            try:
                job.mark_running()

                await asyncio.wait_for(
                    self._handler(job),
                    timeout=job.timeout,
                )

                job.mark_success()

            except asyncio.CancelledError:
                raise

            except Exception as exc:
                logger.exception(
                    "Worker %s failed processing %s",
                    worker_id,
                    job.repository,
                )

                job.mark_failed(str(exc))

            finally:
                self._queue.task_done()