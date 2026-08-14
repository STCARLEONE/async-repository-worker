"""Custom exceptions for the async repository worker."""

from typing import Optional

import httpx


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class GitHubClientError(GitHubAPIError):
    """Client-side errors (4xx)."""
    pass


class GitHubServerError(GitHubAPIError):
    """Server-side errors (5xx)."""
    pass


class GitHubRateLimitError(GitHubServerError):
    """Rate limit exceeded (429)."""
    pass


class GitHubAuthenticationError(GitHubClientError):
    """Authentication errors (401)."""
    pass


class GitHubPermissionError(GitHubClientError):
    """Permission errors (403)."""
    pass


class GitHubNotFoundError(GitHubClientError):
    """Resource not found (404)."""
    pass


class GitHubBadRequestError(GitHubClientError):
    """Bad request (400)."""
    pass


class GitHubTimeoutError(GitHubAPIError):
    """Request timeout."""
    pass


class GitHubConnectionError(GitHubAPIError):
    """Connection error."""
    pass


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error should be retried."""
    if isinstance(error, (GitHubRateLimitError, GitHubServerError, GitHubTimeoutError, GitHubConnectionError)):
        return True
    if isinstance(error, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
        return True
    return False