from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()


class GitHubClient:
    def __init__(self) -> None:
        self.base_url = os.getenv(
            "GITHUB_API_URL",
            "https://api.github.com",
        )
        self.token = os.getenv("GITHUB_TOKEN")

        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not configured")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def get_repository(self, owner: str, repo: str) -> dict:
        response = await self._client.get(f"/repos/{owner}/{repo}")

        response.raise_for_status()

        return response.json()

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        await self.close()
