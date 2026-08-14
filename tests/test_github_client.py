"""Tests for GitHub API client with comprehensive error scenarios."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from async_repository_worker.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubBadRequestError,
    GitHubConnectionError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubServerError,
    GitHubTimeoutError,
)
from async_repository_worker.github import GitHubClient


@pytest.fixture
def mock_response():
    """Create a mock HTTP response with synchronous methods."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.json = MagicMock(return_value={"name": "test-repo", "owner": {"login": "test-user"}})
    mock.raise_for_status = MagicMock(return_value=None)
    mock.headers = {}
    return mock


@pytest.fixture
def github_client():
    """Create GitHub client with mocked HTTP client."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock()
        mock_client.aclose = AsyncMock()
        mock_client_class.return_value = mock_client
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
            client = GitHubClient()
            client._client = mock_client
            yield client


@pytest.mark.asyncio
async def test_get_repository_success(github_client, mock_response):
    github_client._client.get.return_value = mock_response
    result = await github_client.get_repository("test-user", "test-repo")
    assert result == {"name": "test-repo", "owner": {"login": "test-user"}}
    github_client._client.get.assert_called_once_with("/repos/test-user/test-repo")


@pytest.mark.asyncio
async def test_get_repository_http_400(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 400
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )
    )
    mock.json = MagicMock(return_value={"message": "Validation failed"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubBadRequestError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 400
    assert "Validation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_repository_http_401(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 401
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401),
        )
    )
    mock.json = MagicMock(return_value={"message": "Bad credentials"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubAuthenticationError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_repository_http_403(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 403
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Forbidden",
            request=MagicMock(),
            response=MagicMock(status_code=403),
        )
    )
    mock.json = MagicMock(return_value={"message": "Insufficient permissions"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubPermissionError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_repository_http_404(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 404
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
    )
    mock.json = MagicMock(return_value={"message": "Repository not found"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubNotFoundError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_repository_http_429(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 429
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Too Many Requests",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )
    )
    mock.json = MagicMock(return_value={"message": "Rate limit exceeded"})
    mock.headers = {"Retry-After": "60"}
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubRateLimitError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_get_repository_http_500(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 500
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
    )
    mock.json = MagicMock(return_value={"message": "Internal error"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubServerError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_get_repository_http_502(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 502
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Bad Gateway",
            request=MagicMock(),
            response=MagicMock(status_code=502),
        )
    )
    mock.json = MagicMock(return_value={"message": "Bad gateway"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubServerError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_get_repository_http_503(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 503
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Service Unavailable",
            request=MagicMock(),
            response=MagicMock(status_code=503),
        )
    )
    mock.json = MagicMock(return_value={"message": "Service unavailable"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubServerError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_get_repository_http_504(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 504
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Gateway Timeout",
            request=MagicMock(),
            response=MagicMock(status_code=504),
        )
    )
    mock.json = MagicMock(return_value={"message": "Gateway timeout"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubServerError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_get_repository_timeout(github_client):
    github_client._client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with pytest.raises(GitHubTimeoutError):
        await github_client.get_repository("test-user", "test-repo")


@pytest.mark.asyncio
async def test_get_repository_connection_error(github_client):
    github_client._client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

    with pytest.raises(GitHubConnectionError):
        await github_client.get_repository("test-user", "test-repo")


@pytest.mark.asyncio
async def test_get_repository_invalid_json(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.raise_for_status = MagicMock(return_value=None)
    mock.json = MagicMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubAPIError):
        await github_client.get_repository("test-user", "test-repo")


@pytest.mark.asyncio
async def test_get_repository_missing_token():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN is not configured"):
            GitHubClient()


@pytest.mark.asyncio
async def test_client_context_manager(github_client):
    async with github_client as client:
        assert client is github_client
    github_client._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_client_close(github_client):
    await github_client.close()
    github_client._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_get_repository_rate_limit_headers(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.json = MagicMock(return_value={"name": "test-repo", "owner": {"login": "test-user"}})
    mock.raise_for_status = MagicMock(return_value=None)
    mock.headers = {
        "X-RateLimit-Remaining": "42",
        "X-RateLimit-Reset": "1234567890",
        "Retry-After": "60",
    }
    github_client._client.get.return_value = mock

    result = await github_client.get_repository("test-user", "test-repo")
    assert result == {"name": "test-repo", "owner": {"login": "test-user"}}
    assert mock.headers["X-RateLimit-Remaining"] == "42"


@pytest.mark.asyncio
async def test_concurrent_requests(github_client, mock_response):
    github_client._client.get.return_value = mock_response
    tasks = [
        github_client.get_repository(f"user{i}", f"repo{i}")
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 10
    assert all(r["name"] == "test-repo" for r in results)
    assert github_client._client.get.call_count == 10


@pytest.mark.asyncio
async def test_client_reuse(github_client, mock_response):
    github_client._client.get.return_value = mock_response
    result1 = await github_client.get_repository("user1", "repo1")
    result2 = await github_client.get_repository("user2", "repo2")
    assert result1["name"] == "test-repo"
    assert result2["name"] == "test-repo"
    assert github_client._client.get.call_count == 2


@pytest.mark.asyncio
async def test_get_repository_http_400_with_message(github_client):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 400
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )
    )
    mock.json = MagicMock(return_value={"message": "Validation failed"})
    github_client._client.get.return_value = mock

    with pytest.raises(GitHubBadRequestError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.status_code == 400
    assert "Validation failed" in str(exc_info.value)