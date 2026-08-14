from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from itertools import count

from .models import JobPriority, RepositoryJob


_PRIORITY_WEIGHT = {
    JobPriority.CRITICAL: 0,
    JobPriority.HIGH: 1,
    JobPriority.NORMAL: 2,
    JobPriority.LOW: 3,
}


@dataclass(order=True, slots=True)
class _QueueItem:
    priority: int
    sequence: int
    job: RepositoryJob = field(compare=False)


class PriorityJobQueue:
    """Concurrency-safe priority queue for repository jobs."""

    def __init__(self, maxsize: int = 0) -> None:
        if maxsize < 0:
            raise ValueError("maxsize cannot be negative")

        self._queue: asyncio.PriorityQueue[_QueueItem] = (
            asyncio.PriorityQueue(maxsize=maxsize)
        )
        self._sequence = count()

    async def put(self, job: RepositoryJob) -> None:
        item = _QueueItem(
            priority=_PRIORITY_WEIGHT[job.priority],
            sequence=next(self._sequence),
            job=job,
        )

        await self._queue.put(item)

    async def get(self) -> RepositoryJob:
        item = await self._queue.get()
        return item.job

    def task_done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    def qsize(self) -> int:
        return self._queue.qsize()

    def empty(self) -> bool:
        return self._queue.empty()

    def full(self) -> bool:
        return self._queue.full()