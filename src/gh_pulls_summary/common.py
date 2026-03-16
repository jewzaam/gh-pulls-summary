"""
Shared constants, exceptions, and utilities used across modules.
"""

# Configuration
GITHUB_API_BASE = "https://api.github.com"


def get_github_headers(token: str | None = None) -> dict:
    """
    Get GitHub API headers, optionally with authentication.

    Args:
        token: GitHub personal access token (optional)

    Returns:
        Dictionary of headers for GitHub API requests
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


# Exception Classes


class GitHubAPIError(Exception):
    """Raised when GitHub API requests fail."""

    def __init__(self, message, status_code=None, response_text=None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class RateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""


class NetworkError(Exception):
    """Raised when network-related errors occur."""


class ValidationError(Exception):
    """Raised when input validation fails."""
