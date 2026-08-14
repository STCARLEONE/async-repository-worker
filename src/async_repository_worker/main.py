from __future__ import annotations

import asyncio
import logging

from .config import Settings
from .limiter import RateLimiter
from .models import RepositoryJob
from .queue import PriorityJobQueue
from .retry import retry
from .worker import WorkerPool


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = Settings.from_env()

    limiter = RateLimiter(
        rate=settings.rate_limit,
        capacity=settings.rate_capacity,
    )

    queue = PriorityJobQueue()

    @retry(
        attempts=settings.retry_attempts,
        base_delay=settings.retry_base_delay,
        max_delay=settings.retry_max_delay,
    )
    async def process_repository(job: RepositoryJob) -> None:
        async with limiter:
            logger.info(
                "Processing repository: %s",
                job.repository,
            )
            await asyncio.sleep(0.1)

    pool = WorkerPool(
        queue=queue,
        handler=process_repository,
        workers=settings.worker_count,
    )

    await pool.start()

    jobs = [
        RepositoryJob(repository="STCARLEONE/repository-1"),
        RepositoryJob(repository="STCARLEONE/repository-2"),
        RepositoryJob(repository="STCARLEONE/repository-3"),
    ]

    for job in jobs:
        job.timeout = settings.job_timeout
        await queue.put(job)

    await pool.wait()
    await pool.stop()

    logger.info("All jobs completed")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()