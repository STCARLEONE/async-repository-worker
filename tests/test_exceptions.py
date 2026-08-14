"""Tests for custom exceptions and error classification."""

import httpx
import pytest

from async_repository_worker.exceptions import (
    GitHubAPIError,  # <-- اضافه شد
    GitHubAuthenticationError,
    GitHubBadRequestError,
    GitHubClientError,
    GitHubConnectionError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubServerError,
    GitHubTimeoutError,
    is_retryable_error,
)

def test_is_retryable_error_with_rate_limit():
    """Test that rate limit errors are retryable."""
    error = GitHubRateLimitError("Rate limit exceeded", status_code=429)
    assert is_retryable_error(error) is True


def test_is_retryable_error_with_server_error():
    """Test that server errors are retryable."""
    error = GitHubServerError("Server error", status_code=500)
    assert is_retryable_error(error) is True


def test_is_retryable_error_with_timeout():
    """Test that timeout errors are retryable."""
    error = GitHubTimeoutError("Timeout")
    assert is_retryable_error(error) is True


def test_is_retryable_error_with_connection():
    """Test that connection errors are retryable."""
    error = GitHubConnectionError("Connection failed")
    assert is_retryable_error(error) is True


def test_is_retryable_error_with_httpx_timeout():
    """Test that httpx timeout errors are retryable."""
    error = httpx.TimeoutException("Timeout")
    assert is_retryable_error(error) is True


def test_is_retryable_error_with_httpx_connect():
    """Test that httpx connect errors are retryable."""
    error = httpx.ConnectError("Connection failed")
    assert is_retryable_error(error) is True


def test_is_retryable_error_with_bad_request():
    """Test that bad request errors are not retryable."""
    error = GitHubBadRequestError("Bad request", status_code=400)
    assert is_retryable_error(error) is False


def test_is_retryable_error_with_authentication():
    """Test that authentication errors are not retryable."""
    error = GitHubAuthenticationError("Auth failed", status_code=401)
    assert is_retryable_error(error) is False


def test_is_retryable_error_with_permission():
    """Test that permission errors are not retryable."""
    error = GitHubPermissionError("Permission denied", status_code=403)
    assert is_retryable_error(error) is False


def test_is_retryable_error_with_not_found():
    """Test that not found errors are not retryable."""
    error = GitHubNotFoundError("Not found", status_code=404)
    assert is_retryable_error(error) is False


def test_is_retryable_error_with_client_error():
    """Test that client errors are not retryable."""
    error = GitHubClientError("Client error", status_code=418)
    assert is_retryable_error(error) is False


def test_exception_inheritance():
    """Test exception hierarchy."""
    assert issubclass(GitHubRateLimitError, GitHubServerError)
    assert issubclass(GitHubServerError, GitHubAPIError)
    assert issubclass(GitHubClientError, GitHubAPIError)
    assert issubclass(GitHubAuthenticationError, GitHubClientError)
    assert issubclass(GitHubPermissionError, GitHubClientError)
    assert issubclass(GitHubNotFoundError, GitHubClientError)
    assert issubclass(GitHubBadRequestError, GitHubClientError)


def test_exception_attributes():
    """Test exception attributes."""
    error = GitHubRateLimitError(
        "Rate limit exceeded",
        status_code=429,
        response_data={"message": "Too many requests"},
    )
    assert error.status_code == 429
    assert error.response_data == {"message": "Too many requests"}
    assert str(error) == "Rate limit exceeded"