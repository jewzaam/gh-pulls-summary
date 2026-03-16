"""
Shared constants, exceptions, data models, and utilities used across modules.
"""

from dataclasses import dataclass, field

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


# Data Models


@dataclass
class PullRequestData:
    """Data for a single pull request or synthetic JIRA entry in the output table."""

    date: str
    title: str | None
    number: int | None
    url: str | None
    author_name: str
    author_url: str
    reviews: int
    approvals: int
    changes: int | str
    pr_body_urls_dict: dict[str, str] = field(default_factory=dict)
    rank: str = ""
    closed_issue_keys: set[str] = field(default_factory=set)
    jira_key: str | None = None


@dataclass
class JiraIssueData:
    """Metadata for a JIRA issue used in the output table."""

    title: str
    url: str
    rank: str = ""
    closed: bool = False
