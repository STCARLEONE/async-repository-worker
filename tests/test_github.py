import os

import pytest

from async_repository_worker.github import GitHubClient


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN is not configured",
)
async def test_get_repository():
    async with GitHubClient() as client:
        repository = await client.get_repository(
            "STCARLEONE",
            "async-repository-worker",
        )

    assert repository["name"] == "async-repository-worker"
    assert repository["owner"]["login"].lower() == "stcarleone"
