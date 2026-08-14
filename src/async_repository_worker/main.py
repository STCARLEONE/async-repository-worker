from __future__ import annotations

import asyncio
import logging

from .config import Settings
from .database import Database
from .github import GitHubClient
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
    github = GitHubClient()
    db = Database()
    await db.connect()

    @retry(
        attempts=settings.retry_attempts,
        base_delay=settings.retry_base_delay,
        max_delay=settings.retry_max_delay,
    )
    async def process_repository(job: RepositoryJob) -> None:
        async with limiter:
            logger.info("Fetching repository: %s", job.repository)

            owner, repo = job.repository.split("/", 1)
            data = await github.get_repository(owner, repo)

            repo_id = await db.insert_or_update(data)

            logger.info(
                "Repository: %s | Stars: %s | Forks: %s | ID: %s",
                data["full_name"],
                data["stargazers_count"],
                data["forks_count"],
                repo_id,
            )

    pool = WorkerPool(
        queue=queue,
        handler=process_repository,
        workers=settings.worker_count,
    )

    await pool.start()

    jobs = [
        RepositoryJob(repository="STCARLEONE/async-repository-worker"),
        RepositoryJob(repository="python/cpython"),
        RepositoryJob(repository="psf/requests"),
    ]

    for job in jobs:
        job.timeout = settings.job_timeout
        await queue.put(job)

    await pool.wait()
    await pool.stop()

    await github.close()
    await db.close()
    logger.info("All jobs completed")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
