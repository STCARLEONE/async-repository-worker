"""Tests for GitHub API client with comprehensive error scenarios."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

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
    """Test successful repository retrieval."""
    github_client._client.get.return_value = mock_response

    result = await github_client.get_repository("test-user", "test-repo")

    assert result == {"name": "test-repo", "owner": {"login": "test-user"}}
    github_client._client.get.assert_called_once_with("/repos/test-user/test-repo")


@pytest.mark.asyncio
async def test_get_repository_http_400(github_client):
    """Test HTTP 400 Bad Request."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 400
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 400


@pytest.mark.asyncio
async def test_get_repository_http_401(github_client):
    """Test HTTP 401 Unauthorized."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 401
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 401


@pytest.mark.asyncio
async def test_get_repository_http_403(github_client):
    """Test HTTP 403 Forbidden."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 403
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Forbidden",
            request=MagicMock(),
            response=MagicMock(status_code=403),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 403


@pytest.mark.asyncio
async def test_get_repository_http_404(github_client):
    """Test HTTP 404 Not Found."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 404
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 404


@pytest.mark.asyncio
async def test_get_repository_http_429(github_client):
    """Test HTTP 429 Too Many Requests."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 429
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Too Many Requests",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 429


@pytest.mark.asyncio
async def test_get_repository_http_500(github_client):
    """Test HTTP 500 Internal Server Error."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 500
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 500


@pytest.mark.asyncio
async def test_get_repository_http_502(github_client):
    """Test HTTP 502 Bad Gateway."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 502
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Bad Gateway",
            request=MagicMock(),
            response=MagicMock(status_code=502),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 502


@pytest.mark.asyncio
async def test_get_repository_http_503(github_client):
    """Test HTTP 503 Service Unavailable."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 503
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Service Unavailable",
            request=MagicMock(),
            response=MagicMock(status_code=503),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 503


@pytest.mark.asyncio
async def test_get_repository_http_504(github_client):
    """Test HTTP 504 Gateway Timeout."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 504
    mock.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Gateway Timeout",
            request=MagicMock(),
            response=MagicMock(status_code=504),
        )
    )
    github_client._client.get.return_value = mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 504


@pytest.mark.asyncio
async def test_get_repository_timeout(github_client):
    """Test request timeout."""
    github_client._client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with pytest.raises(httpx.TimeoutException):
        await github_client.get_repository("test-user", "test-repo")


@pytest.mark.asyncio
async def test_get_repository_connection_error(github_client):
    """Test connection error."""
    github_client._client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

    with pytest.raises(httpx.ConnectError):
        await github_client.get_repository("test-user", "test-repo")


@pytest.mark.asyncio
async def test_get_repository_invalid_json(github_client):
    """Test invalid JSON response."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.raise_for_status = MagicMock(return_value=None)
    mock.json = MagicMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    github_client._client.get.return_value = mock

    with pytest.raises(json.JSONDecodeError):
        await github_client.get_repository("test-user", "test-repo")


@pytest.mark.asyncio
async def test_get_repository_missing_token():
    """Test missing GitHub token."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN is not configured"):
            GitHubClient()


@pytest.mark.asyncio
async def test_client_context_manager(github_client):
    """Test client works as context manager."""
    async with github_client as client:
        assert client is github_client
    github_client._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_client_close(github_client):
    """Test explicit client close."""
    await github_client.close()
    github_client._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_get_repository_rate_limit_headers(github_client):
    """Test rate limit headers are accessible."""
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
    # Headers are accessible via the mock response
    assert mock.headers["X-RateLimit-Remaining"] == "42"


@pytest.mark.asyncio
async def test_concurrent_requests(github_client, mock_response):
    """Test concurrent requests don't interfere."""
    github_client._client.get.return_value = mock_response

    # Make 10 concurrent requests
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
    """Test client can be reused for multiple requests."""
    github_client._client.get.return_value = mock_response

    # First request
    result1 = await github_client.get_repository("user1", "repo1")
    # Second request
    result2 = await github_client.get_repository("user2", "repo2")

    assert result1["name"] == "test-repo"
    assert result2["name"] == "test-repo"
    assert github_client._client.get.call_count == 2


@pytest.mark.asyncio
async def test_get_repository_http_400_with_message(github_client):
    """Test HTTP 400 with error message in body."""
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

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await github_client.get_repository("test-user", "test-repo")
    assert exc_info.value.response.status_code == 400