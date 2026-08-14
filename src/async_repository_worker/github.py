"""GitHub API client with proper error handling."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

from .exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubBadRequestError,
    GitHubClientError,
    GitHubConnectionError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubServerError,
    GitHubTimeoutError,
)

load_dotenv()

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async client for GitHub API with comprehensive error handling."""

    def __init__(self, token: Optional[str] = None, timeout: Optional[float] = None) -> None:
        self.base_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.timeout = timeout or float(os.getenv("GITHUB_API_TIMEOUT", "30.0"))

        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not configured")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=self.timeout,
        )

    async def get_repository(self, owner: str, repo: str) -> dict:
        """Fetch repository information with proper error handling."""
        try:
            response = await self._client.get(f"/repos/{owner}/{repo}")
            return await self._handle_response(response)
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching {owner}/{repo}: {e}")
            raise GitHubTimeoutError(f"Request timed out: {e}") from e
        except httpx.ConnectError as e:
            logger.error(f"Connection error fetching {owner}/{repo}: {e}")
            raise GitHubConnectionError(f"Connection failed: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response for {owner}/{repo}: {e}")
            raise GitHubAPIError(f"Invalid JSON response: {e}") from e

    async def _handle_response(self, response: httpx.Response) -> dict:
        """Handle HTTP response and convert to appropriate exceptions."""
        status_code = response.status_code

        # Success
        if 200 <= status_code < 300:
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in successful response: {e}")
                raise GitHubAPIError(f"Invalid JSON response: {e}") from e

        # Client errors (4xx)
        if 400 <= status_code < 500:
            error_data = self._get_error_data(response)
            logger.warning(f"Client error {status_code}: {error_data}")

            # Rate limit must be checked first (429 is retryable)
            if status_code == 429:
                raise GitHubRateLimitError(
                    f"Rate limit exceeded: {error_data.get('message', 'Too many requests')}",
                    status_code=status_code,
                    response_data=error_data,
                )
            if status_code == 400:
                raise GitHubBadRequestError(
                    f"Bad request: {error_data.get('message', 'Unknown error')}",
                    status_code=status_code,
                    response_data=error_data,
                )
            if status_code == 401:
                raise GitHubAuthenticationError(
                    f"Authentication failed: {error_data.get('message', 'Invalid token')}",
                    status_code=status_code,
                    response_data=error_data,
                )
            if status_code == 403:
                raise GitHubPermissionError(
                    f"Permission denied: {error_data.get('message', 'Insufficient permissions')}",
                    status_code=status_code,
                    response_data=error_data,
                )
            if status_code == 404:
                raise GitHubNotFoundError(
                    f"Resource not found: {error_data.get('message', 'Repository not found')}",
                    status_code=status_code,
                    response_data=error_data,
                )
            # Other 4xx
            raise GitHubClientError(
                f"Client error {status_code}: {error_data.get('message', 'Unknown error')}",
                status_code=status_code,
                response_data=error_data,
            )

        # Server errors (5xx)
        if 500 <= status_code < 600:
            error_data = self._get_error_data(response)
            logger.error(f"Server error {status_code}: {error_data}")

            raise GitHubServerError(
                f"Server error {status_code}: {error_data.get('message', 'Internal server error')}",
                status_code=status_code,
                response_data=error_data,
            )

        # Unknown status
        error_data = self._get_error_data(response)
        raise GitHubAPIError(
            f"Unexpected status {status_code}: {error_data.get('message', 'Unknown error')}",
            status_code=status_code,
            response_data=error_data,
        )

    def _get_error_data(self, response: httpx.Response) -> dict:
        """Extract error data from response."""
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError):
            return {"message": response.text or "Unknown error"}

    async def get_rate_limit_headers(self, owner: str, repo: str) -> dict:
        """Fetch rate limit headers without raising for status."""
        try:
            response = await self._client.get(f"/repos/{owner}/{repo}")
            return {
                "remaining": response.headers.get("X-RateLimit-Remaining"),
                "reset": response.headers.get("X-RateLimit-Reset"),
                "retry_after": response.headers.get("Retry-After"),
            }
        except Exception as e:
            logger.warning(f"Failed to get rate limit headers: {e}")
            return {}

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.close()