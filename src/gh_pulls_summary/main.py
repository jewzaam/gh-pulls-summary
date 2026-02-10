#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argparse
import logging
import os
import re
import subprocess
import sys
import time
from typing import Any, cast
from urllib.parse import quote

import argcomplete
import requests

from gh_pulls_summary.jira_client import JiraClient, JiraClientError

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


# Custom Exception Classes
class MissingRepoError(Exception):
    """Raised when repository information cannot be determined."""


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


class FileOperationError(Exception):
    """Raised when file operations fail."""


def get_repo_and_owner_from_git():
    """
    Retrieves the repository and owner from the local Git configuration.
    Returns a tuple (owner, repo) or (None, None) if not found.
    """
    try:
        # Get the remote URL
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()

        # Parse the remote URL to extract owner and repo
        if remote_url.startswith("git@"):
            # SSH URL (e.g., git@github.com:owner/repo.git)
            _, path = remote_url.split(":", 1)
        elif remote_url.startswith("https://"):
            # HTTPS URL (e.g., https://github.com/owner/repo.git)
            parts = remote_url.split(
                "/", 5
            )  # Split into up to 6 parts: ["https:", "", "domain", "owner", "repo", "extra/path..."]
            if len(parts) >= 5:
                path = f"{parts[3]}/{parts[4]}"  # owner/repo
            else:
                path = remote_url.split("/", 3)[-1]
        else:
            return None, None

        # Remove the `.git` suffix if present
        if path.endswith(".git"):
            path = path[:-4]

        owner, repo = path.split("/", 1)
        return owner, repo
    except Exception:  # pragma: no cover
        return None, None


def parse_arguments():
    """
    Parses command-line arguments for the script.
    """
    # Get default owner and repo from Git metadata
    default_owner, default_repo = get_repo_and_owner_from_git()

    parser = argparse.ArgumentParser(
        description="Fetch and summarize GitHub pull requests."
    )
    parser.add_argument(
        "--owner",
        default=default_owner,
        help="The owner of the repository (e.g., 'microsoft'). If not specified, defaults to the owner from the current directory's Git config.",
    )
    parser.add_argument(
        "--repo",
        default=default_repo,
        help="The name of the repository (e.g., 'vscode'). If not specified, defaults to the repo name from the current directory's Git config.",
    )
    parser.add_argument(
        "--github-token",
        type=str,
        help="GitHub personal access token for authentication. Can also be set via GITHUB_TOKEN environment variable. Increases rate limit from 60 to 5000 requests/hour.",
    )
    parser.add_argument(
        "--pr-number", type=int, help="Specify a single pull request number to query."
    )
    parser.add_argument(
        "--draft-filter",
        choices=["only-drafts", "no-drafts"],
        help="Filter pull requests based on draft status. Use 'only-drafts' to include only drafts, or 'no-drafts' to exclude drafts.",
    )
    parser.add_argument(
        "--file-include",
        action="append",
        help="Regex pattern to include pull requests based on changed file paths. Can be specified multiple times.",
    )
    parser.add_argument(
        "--file-exclude",
        action="append",
        help="Regex pattern to exclude pull requests based on changed file paths. Can be specified multiple times.",
    )
    parser.add_argument(
        "--url-from-pr-content",
        type=str,
        help="Regex pattern to extract all unique URLs from added lines in the PR diff. If set, adds a column to the output table with the matched URLs.",
    )
    parser.add_argument(
        "--output-markdown",
        type=str,
        help="Path to write the generated Markdown output (with timestamp) to a file. If not set, output is printed to stdout only.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and show tracebacks on error.",
    )
    parser.add_argument(
        "--column-title",
        action="append",
        help="Override the title for any output column. Format: COLUMN=TITLE. Valid COLUMN values: date, title, author, changes, approvals, urls. Can be specified multiple times.",
    )
    parser.add_argument(
        "--sort-column",
        type=str,
        default="date",
        help="Specify which output column to sort by. Valid values: date, title, author, changes, approvals, urls, rank. Default is 'date'.",
    )
    parser.add_argument(
        "--jira-url",
        type=str,
        help="JIRA instance base URL (e.g., 'https://issues.redhat.com'). Can also be set via JIRA_BASE_URL environment variable.",
    )
    parser.add_argument(
        "--jira-token",
        type=str,
        help="JIRA API token for authentication. Can also be set via JIRA_TOKEN environment variable.",
    )
    parser.add_argument(
        "--jira-rank-field",
        type=str,
        help="Explicit JIRA Rank field ID (e.g., 'customfield_12311940'). If not provided, will attempt automatic discovery.",
    )
    parser.add_argument(
        "--include-rank",
        action="store_true",
        help="Include JIRA rank column in output. Requires JIRA configuration (--jira-url or JIRA_BASE_URL). Only includes ANSTRAT issues of type Feature and Initiative.",
    )
    parser.add_argument(
        "--jira-issue-pattern",
        type=str,
        action="append",
        help="Regex pattern to extract JIRA issue keys from file contents. Use parentheses to capture the issue key (e.g., '(ANSTRAT-\\d+)'). Can be specified multiple times to use multiple patterns. If not specified, defaults to '(ANSTRAT-\\d+)'.",
    )
    parser.add_argument(
        "--jira-include",
        type=str,
        action="append",
        help="Always include this JIRA issue in the output, regardless of filters. Useful for marker stories when looking at rankings. Can be specified multiple times.",
    )
    parser.add_argument(
        "--review-requested-for",
        type=str,
        help="Filter pull requests where review is requested for this GitHub username. Only shows PRs where the specified user is in the requested reviewers list.",
    )

    # Enable tab completion
    argcomplete.autocomplete(parser)
    return parser.parse_args()


def configure_logging(debug):
    """
    Configures logging for the script.
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr)  # Log to stderr
        ],
    )


def github_api_request(
    endpoint, params=None, use_paging=True, max_retries=3, headers=None
):
    """
    Makes a GitHub API request and optionally handles pagination.
    Returns all results across all pages if pagination is enabled.
    Returns None if no results are found or an error occurs.
    Automatically handles rate limiting by waiting and retrying.

    Args:
        endpoint: GitHub API endpoint path
        params: Query parameters for the request
        use_paging: Whether to handle pagination automatically
        max_retries: Maximum number of retries for rate limiting
        headers: HTTP headers to use for the request
    """
    if params is None:
        params = {}

    if headers is None:
        headers = get_github_headers()

    all_results = []
    page = 1
    last_results = None  # Fail-safe to detect duplicate results

    while True:
        if use_paging:
            params["page"] = page
        url = f"{GITHUB_API_BASE}{endpoint}"
        logging.debug(f"Making API request to {url} with params {params}")

        # Retry loop for rate limiting
        retry_count = 0
        while retry_count <= max_retries:
            try:
                response = requests.get(url, headers=headers, params=params)
            except requests.exceptions.ConnectionError as e:
                raise NetworkError(
                    f"Network connection failed. Please check your internet connection and try again. Details: {e}"
                )
            except requests.exceptions.Timeout as e:
                raise NetworkError(
                    f"Request timed out. The GitHub API may be slow. Please try again. Details: {e}"
                )
            except requests.exceptions.RequestException as e:
                raise NetworkError(
                    f"Network error occurred while contacting GitHub API. Details: {e}"
                )

            # Handle rate limiting with automatic retry
            if (
                response.status_code == 403
                and "X-RateLimit-Remaining" in response.headers
                and response.headers["X-RateLimit-Remaining"] == "0"
            ):
                if retry_count >= max_retries:
                    reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
                    raise RateLimitError(
                        f"GitHub API rate limit exceeded after {max_retries} retries. "
                        f"Rate limit will reset at {reset_time}. "
                        f"Consider using a GitHub token to increase your rate limit (5000 requests/hour vs 60 requests/hour). "
                        f"Use --github-token or set GITHUB_TOKEN environment variable with a personal access token."
                    )

                # Parse reset time and calculate wait duration
                reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
                current_timestamp = int(time.time())
                wait_seconds = max(
                    reset_timestamp - current_timestamp + 1, 1
                )  # Add 1 second buffer

                # Convert timestamps to human-readable format for logging
                from datetime import datetime

                reset_datetime = datetime.fromtimestamp(reset_timestamp)
                current_datetime = datetime.fromtimestamp(current_timestamp)

                logging.warning(
                    f"Rate limit exceeded. "
                    f"Current time: {current_timestamp} ({current_datetime.isoformat()}), "
                    f"Reset time: {reset_timestamp} ({reset_datetime.isoformat()}), "
                    f"Wait duration: {wait_seconds} seconds ({wait_seconds / 60:.1f} minutes) "
                    f"(retry {retry_count + 1}/{max_retries})..."
                )
                time.sleep(wait_seconds)
                retry_count += 1
                continue  # Retry the request

            # If we got here, we didn't hit rate limit, so break out of retry loop
            break

        if response.status_code == 401:
            raise GitHubAPIError(
                "GitHub API authentication failed. Please check your --github-token or GITHUB_TOKEN if set. "
                "You may need to generate a new personal access token from GitHub Settings.",
                status_code=401,
                response_text=response.text,
            )

        if response.status_code == 404:
            raise GitHubAPIError(
                f"GitHub API endpoint not found: {endpoint}. "
                f"Please verify the repository owner and name are correct.",
                status_code=404,
                response_text=response.text,
            )

        if response.status_code != 200:
            raise GitHubAPIError(
                f"GitHub API request failed with status {response.status_code}. "
                f"Endpoint: {endpoint}. "
                f"Response: {response.text}",
                status_code=response.status_code,
                response_text=response.text,
            )

        try:
            results = response.json()
        except ValueError as e:
            raise GitHubAPIError(
                f"Invalid JSON response from GitHub API. The service may be experiencing issues. Details: {e}"
            )

        if results == last_results:  # pragma: no cover
            logging.warning(
                f"Duplicate results detected for pages {page - 1} and {page}. This may indicate a GitHub API issue."
            )
            break

        # Handle cases where the response is a dictionary
        if isinstance(results, dict):
            logging.debug(f"Response is a dictionary: {results}")
            return results

        # Handle cases where the response is a list
        if not results or not use_paging:
            all_results.extend(results)
            break

        all_results.extend(results)
        last_results = results

        page += 1

    logging.debug(f"Fetched {len(all_results)} items from {endpoint}")
    return all_results


def fetch_pull_requests(owner, repo, github_token=None, review_requested_for=None):
    """
    Fetches all open pull requests for the specified repository.
    If review_requested_for is specified, fetches all PRs and filters using Search API intersection.
    This ensures consistent full PR objects regardless of filtering.
    """
    headers = get_github_headers(github_token)

    # Always fetch all open PRs for consistent data structure
    endpoint = f"/repos/{owner}/{repo}/pulls"
    params = {"state": "open"}
    logging.debug(f"Fetching pull requests for {owner}/{repo}")
    all_prs = github_api_request(endpoint, params, headers=headers)

    if not all_prs:
        return []

    # If review_requested_for specified, use Search API to filter
    if review_requested_for:
        # Use Search API to get PR numbers where review is requested
        search_endpoint = "/search/issues"
        query = (
            f"is:pr is:open repo:{owner}/{repo} review-requested:{review_requested_for}"
        )
        search_params = {"q": query, "per_page": 100}
        logging.debug(
            f"Filtering pull requests for {owner}/{repo} with review-requested:{review_requested_for}"
        )

        # Collect all matching PR numbers from Search API
        matching_pr_numbers = set()
        page = 1
        while True:
            search_params["page"] = page
            search_results = github_api_request(
                search_endpoint, search_params, use_paging=False, headers=headers
            )
            if not search_results or "items" not in search_results:
                break

            items = search_results.get("items", [])
            if not items:
                break

            for item in items:
                matching_pr_numbers.add(item["number"])
            page += 1

        # Return intersection: PRs that are in both /pulls and search results
        filtered_prs = [pr for pr in all_prs if pr["number"] in matching_pr_numbers]
        logging.debug(
            f"Filtered {len(all_prs)} PRs to {len(filtered_prs)} matching review-requested:{review_requested_for}"
        )
        return filtered_prs

    return all_prs


def fetch_single_pull_request(owner, repo, pr_number, github_token=None):
    """
    Fetches a single pull request by its number.
    """
    endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = get_github_headers(github_token)
    logging.debug(f"Fetching single pull request #{pr_number} for {owner}/{repo}")
    return github_api_request(endpoint, use_paging=False, headers=headers)


def fetch_issue_events(owner, repo, pr_number, github_token=None):
    """
    Fetches all issue events for a specific pull request.
    """
    endpoint = f"/repos/{owner}/{repo}/issues/{pr_number}/events"
    headers = get_github_headers(github_token)
    logging.debug(f"Fetching issue events for PR #{pr_number}")
    return github_api_request(endpoint, headers=headers)


def fetch_reviews(owner, repo, pr_number, github_token=None):
    """
    Fetches all reviews for a specific pull request.
    """
    endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    headers = get_github_headers(github_token)
    logging.debug(f"Fetching reviews for PR #{pr_number}")
    return github_api_request(endpoint, headers=headers)


def fetch_user_details(username, github_token=None):
    """
    Fetches details for a specific GitHub user.
    Returns None if user is not found (404 error).
    """
    url = f"{GITHUB_API_BASE}/users/{username}"
    headers = get_github_headers(github_token)
    logging.debug(f"Fetching user details for {username}")

    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError:
        raise NetworkError(
            f"Network connection failed while fetching user details for {username}. Please check your internet connection and try again."
        )
    except requests.exceptions.Timeout:
        raise NetworkError(
            f"Request timed out while fetching user details for {username}. The GitHub API may be slow. Please try again."
        )
    except requests.exceptions.RequestException as e:
        raise NetworkError(
            f"Network error occurred while fetching user details for {username}. Details: {e}"
        )

    if response.status_code == 404:
        logging.debug(f"User {username} not found (404), returning None")
        return None
    if (
        response.status_code == 403
        and "X-RateLimit-Remaining" in response.headers
        and response.headers["X-RateLimit-Remaining"] == "0"
    ):
        reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
        raise RateLimitError(
            f"GitHub API rate limit exceeded while fetching user {username}. "
            f"Rate limit will reset at {reset_time}. "
            f"Consider using a GitHub token to increase your rate limit."
        )
    if response.status_code != 200:
        raise GitHubAPIError(
            f"Failed to fetch user details for {username}. "
            f"GitHub API returned status {response.status_code}. "
            f"Response: {response.text}",
            status_code=response.status_code,
            response_text=response.text,
        )

    try:
        return response.json()
    except ValueError as e:
        raise GitHubAPIError(
            f"Invalid JSON response when fetching user details for {username}. The GitHub API may be experiencing issues. Details: {e}"
        )


def fetch_pr_files(owner, repo, pr_number, github_token=None):
    """
    Fetches the list of files changed in a specific pull request.
    """
    endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
    headers = get_github_headers(github_token)
    logging.debug(f"Fetching files for PR #{pr_number}")
    files = github_api_request(endpoint, use_paging=True, headers=headers)
    logging.debug(f"Files fetched for PR #{pr_number}: {files}")
    return files


def fetch_file_content(owner, repo, file_path, ref, github_token=None):
    """
    Fetches the raw content of a file from GitHub at a specific ref (branch/commit).

    Args:
        owner: Repository owner
        repo: Repository name
        file_path: Path to the file in the repository
        ref: Branch name or commit SHA
        github_token: GitHub authentication token

    Returns:
        File content as string, or None if fetch fails
    """
    # URL-encode the file path to handle special characters like ?
    # Keep forward slashes unencoded as they are path separators
    encoded_file_path = quote(file_path, safe="/")
    endpoint = f"/repos/{owner}/{repo}/contents/{encoded_file_path}"
    headers = get_github_headers(github_token)
    headers["Accept"] = "application/vnd.github.raw"
    params = {"ref": ref}

    logging.debug(f"Fetching content for {file_path} at ref {ref}")

    try:
        url = f"{GITHUB_API_BASE}{endpoint}"
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            return response.text
        if response.status_code == 404:
            logging.warning(f"File not found: {file_path} at ref {ref}")
            return None
        if response.status_code == 403:
            logging.warning(f"Access denied or rate limit when fetching {file_path}")
            return None
        logging.warning(f"Failed to fetch {file_path}: status {response.status_code}")
        return None

    except Exception as e:
        logging.warning(f"Error fetching file content for {file_path}: {e}")
        return None


def create_jira_client(args) -> JiraClient | None:
    """
    Create a JIRA client if JIRA configuration is provided.

    Args:
        args: Command line arguments

    Returns:
        JiraClient instance or None if JIRA is not configured

    Raises:
        ValueError: If --include-rank is specified but JIRA configuration is invalid
        JiraClientError: If --include-rank is specified but JIRA connection fails
    """
    if not args.include_rank:
        return None

    # If rank is requested, JIRA must be properly configured
    try:
        client = JiraClient(
            base_url=args.jira_url,
            token=args.jira_token,
            rank_field_id=args.jira_rank_field,
        )
        # Test the connection
        client.test_connection()
        logging.info("JIRA client initialized successfully")
        return client
    except ValueError as e:
        raise ValueError(
            f"JIRA configuration error: {e}\n"
            f"Rank column requested (--include-rank) but JIRA is not properly configured."
        )
    except JiraClientError as e:
        raise JiraClientError(
            f"JIRA connection failed: {e}\n"
            f"Rank column requested (--include-rank) but cannot connect to JIRA."
        )


def extract_jira_issue_keys(url_dict: dict, pattern: str) -> list[str]:
    """
    Extract JIRA issue keys from URLs dictionary.

    Args:
        url_dict: Dictionary of URL text to URL
        pattern: Regex pattern to match issue keys

    Returns:
        List of unique issue keys found
    """
    if not url_dict:
        return []

    issue_keys = set()
    try:
        regex = re.compile(pattern)
        for url in url_dict.values():
            matches = regex.findall(url)
            issue_keys.update(matches)
    except re.error as e:
        logging.warning(f"Invalid JIRA issue pattern: {e}")
        return []

    return sorted(issue_keys)


def extract_primary_jira_from_metadata(pr_body: str, patterns: list[str]) -> list[str]:
    """
    Extract primary JIRA issues from PR metadata table.

    Looks for a markdown table in the first 50 lines with a row like:
    | **Feature / Initiative** | [ANSTRAT-1586](url) |

    Args:
        pr_body: The PR body/description text
        patterns: List of regex patterns to extract issue keys (e.g., [r"(ANSTRAT-\\d+)"])

    Returns:
        List of JIRA issue keys found in metadata table, or empty list if none found
    """
    if not pr_body or not patterns:
        return []

    # Look only at first 50 lines
    lines = pr_body.split("\n")[:50]

    # Look for the "Feature / Initiative" row in a markdown table (case-insensitive)
    feature_initiative_pattern = re.compile(r"feature\s*/?\s*initiative", re.IGNORECASE)

    for line in lines:
        # Check if this line contains the Feature/Initiative marker
        if feature_initiative_pattern.search(line):
            # Collect all unique matches from all patterns
            all_matches = []
            for pattern in patterns:
                try:
                    regex = re.compile(pattern)
                    matches = regex.findall(line)
                    if matches:
                        all_matches.extend([str(m) for m in matches])
                except re.error as e:
                    logging.warning(f"Invalid JIRA issue pattern '{pattern}': {e}")
                    continue

            if all_matches:
                # Remove duplicates while preserving order
                unique_issues = list(dict.fromkeys(all_matches))
                logging.info(
                    f"Found primary JIRA issues in metadata table: {', '.join(unique_issues)}"
                )
                return unique_issues

    logging.debug("No primary JIRA issues found in PR metadata table")
    return []


def extract_jira_from_file_contents(
    file_contents: list[str], patterns: list[str]
) -> list[str]:
    """
    Extract JIRA issue keys from full file contents using multiple patterns.

    Searches the complete content of all files (not limited to first 50 lines).
    Each pattern should contain a single capture group that extracts the issue identifier.

    Args:
        file_contents: List of file content strings to search (full file contents)
        patterns: List of regex patterns to extract issue keys (e.g., [r"(ANSTRAT-\\d+)", r"(OTHERJIRA-\\d+)"])

    Returns:
        Sorted list of unique JIRA issue keys found across all patterns
    """
    if not file_contents or not patterns:
        return []

    issue_keys: set[str] = set()

    for pattern in patterns:
        try:
            regex = re.compile(pattern)
            for content in file_contents:
                if content:
                    matches = regex.findall(content)
                    # Add all matches to the set (duplicates automatically filtered)
                    issue_keys.update(str(match) for match in matches)
        except re.error as e:
            logging.warning(f"Invalid JIRA issue pattern '{pattern}': {e}")
            continue

    return sorted(issue_keys)


def extract_issue_keys_from_pr(
    file_contents: list[str],
    issue_patterns: list[str],
    pr_body: str | None = None,
) -> list[str]:
    """
    Extract JIRA issue keys from a PR without fetching metadata.

    Extraction strategy:
    1. First checks PR metadata table (first 50 lines, "Feature / Initiative" row)
    2. Falls back to searching full file contents if metadata extraction fails

    Args:
        file_contents: List of file content strings to search for JIRA issues
        issue_patterns: List of regex patterns to extract issue keys
        pr_body: PR body/description text (optional)

    Returns:
        List of JIRA issue keys found
    """
    if not issue_patterns:
        return []

    # First, try to extract primary issues from PR metadata table
    issue_keys = []
    if pr_body:
        primary_issues = extract_primary_jira_from_metadata(pr_body, issue_patterns)
        if primary_issues:
            issue_keys = primary_issues
            logging.debug(f"Found JIRA issues in metadata: {', '.join(primary_issues)}")

    # Fall back to extracting from full file contents if no metadata found
    if not issue_keys:
        issue_keys = extract_jira_from_file_contents(file_contents, issue_patterns)
        if issue_keys:
            logging.debug(f"Found JIRA issues in file contents: {issue_keys}")

    return issue_keys


def get_rank_for_pr(
    jira_client: JiraClient | None,
    issue_keys: list[str],
    jira_metadata_cache: dict[str, dict[str, Any]],
) -> tuple[str | None, set[str]]:
    """
    Get the highest priority rank for a PR based on its JIRA issues.

    Uses pre-fetched JIRA metadata to avoid redundant API calls.

    Filtering rules:
    - Only include Feature and Initiative issue types
    - If referenced issue is not Feature/Initiative, traverse hierarchy to find ancestor
    - Prefer open issues (New, Backlog, In Progress, Refinement)
    - Fall back to closed issues if no open issues with ranks are found
    - For multiple issues, select the highest priority (lowest lexicographic rank)
    - Replace pipe characters with underscores for markdown safety

    Args:
        jira_client: JIRA client instance
        issue_keys: List of JIRA issue keys for this PR
        jira_metadata_cache: Pre-fetched metadata for all issues (must include parent fields)

    Returns:
        Tuple of (rank_string, closed_issue_keys):
        - rank_string: Rank value with issue key appended, or None
        - closed_issue_keys: Set of JIRA keys that are in Closed status
    """
    if not jira_client or not issue_keys:
        return None, set()

    # Get metadata for this PR's issues from cache
    metadata = {
        key: jira_metadata_cache[key]
        for key in issue_keys
        if key in jira_metadata_cache
    }

    if not metadata:
        return None, set()

    # Status definitions
    open_statuses = {"New", "Backlog", "In Progress", "Refinement"}
    closed_statuses = {"Closed"}

    # Track closed issues and separate rank tuples by status
    closed_issue_keys = set()
    open_rank_tuples = []
    closed_rank_tuples = []

    for issue_key, issue_data in metadata.items():
        issue_type = jira_client.get_issue_type(issue_data)
        issue_status = jira_client.get_issue_status(issue_data)
        rank_value = jira_client.extract_rank_value(issue_data)

        logging.debug(
            f"{issue_key}: type={issue_type}, status={issue_status}, rank={rank_value}"
        )

        # Track if this issue is closed
        if issue_status in closed_statuses:
            closed_issue_keys.add(issue_key)

        # Check if this is a Feature or Initiative
        if issue_type in ["Feature", "Initiative"]:
            if rank_value:
                if issue_status in open_statuses:
                    open_rank_tuples.append((rank_value, issue_key))
                elif issue_status in closed_statuses:
                    closed_rank_tuples.append((rank_value, issue_key))
        else:
            # Not a Feature/Initiative - traverse hierarchy using cache to find ancestor
            logging.info(
                f"{issue_key} is type '{issue_type}' (not Feature/Initiative), traversing hierarchy to find ancestor"
            )
            try:
                ancestors = jira_client.get_ancestors(
                    issue_key, metadata_cache=jira_metadata_cache
                )
                for ancestor in ancestors:
                    ancestor_key = ancestor.get("key")
                    if not ancestor_key:
                        continue

                    ancestor_type = jira_client.get_issue_type(ancestor)
                    ancestor_status = jira_client.get_issue_status(ancestor)
                    ancestor_rank = jira_client.extract_rank_value(ancestor)

                    logging.debug(
                        f"  Ancestor {ancestor_key}: type={ancestor_type}, status={ancestor_status}, rank={ancestor_rank}"
                    )

                    # Track if ancestor is closed
                    if ancestor_status in closed_statuses:
                        closed_issue_keys.add(ancestor_key)

                    if ancestor_type in ["Feature", "Initiative"] and ancestor_rank:
                        if ancestor_status in open_statuses:
                            logging.info(
                                f"  Found open {ancestor_type} ancestor {ancestor_key} with rank {ancestor_rank}"
                            )
                            open_rank_tuples.append((ancestor_rank, ancestor_key))
                            break
                        if ancestor_status in closed_statuses:
                            logging.info(
                                f"  Found closed {ancestor_type} ancestor {ancestor_key} with rank {ancestor_rank}"
                            )
                            closed_rank_tuples.append((ancestor_rank, ancestor_key))
                            break
            except Exception as e:
                logging.warning(f"Failed to traverse hierarchy for {issue_key}: {e}")

    # Prefer open issues, fall back to closed issues
    valid_rank_tuples = open_rank_tuples if open_rank_tuples else closed_rank_tuples

    if not valid_rank_tuples:
        return None, closed_issue_keys

    # Select highest priority (lowest lexicographic value)
    # Empty ranks should be treated as lowest priority
    def rank_sort_key(rank_tuple):
        rank_value = rank_tuple[0]
        if not rank_value or rank_value == "":
            return "z" * 100  # Push empty to end
        return rank_value

    valid_rank_tuples.sort(key=rank_sort_key)
    highest_priority_rank, issue_key = valid_rank_tuples[0]

    # Replace pipe characters with underscores for markdown safety
    # Append issue key for transparency
    rank_string = f"{highest_priority_rank.replace('|', '_')} {issue_key}"

    return rank_string, closed_issue_keys


def fetch_pr_diff(owner, repo, pr_number, github_token=None):
    """
    Fetches the diff for a specific pull request using the GitHub API.
    Returns the diff as a string.
    """
    if not pr_number:
        return None

    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = get_github_headers(github_token)
    headers["Accept"] = "application/vnd.github.v3.diff"

    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError:
        raise NetworkError(
            f"Network connection failed while fetching diff for PR #{pr_number}. Please check your internet connection and try again."
        )
    except requests.exceptions.Timeout:
        raise NetworkError(
            f"Request timed out while fetching diff for PR #{pr_number}. The GitHub API may be slow. Please try again."
        )
    except requests.exceptions.RequestException as e:
        raise NetworkError(
            f"Network error occurred while fetching diff for PR #{pr_number}. Details: {e}"
        )

    if response.status_code == 404:
        raise GitHubAPIError(
            f"Pull request #{pr_number} not found in repository {owner}/{repo}. "
            f"Please verify the PR number and repository are correct.",
            status_code=404,
            response_text=response.text,
        )
    if response.status_code == 403:
        raise GitHubAPIError(
            f"Access denied when fetching diff for PR #{pr_number}. "
            f"The repository may be private or you may have exceeded rate limits. "
            f"Consider using a GitHub token with appropriate permissions.",
            status_code=403,
            response_text=response.text,
        )
    if response.status_code != 200:
        raise GitHubAPIError(
            f"Failed to fetch diff for PR #{pr_number}. "
            f"GitHub API returned status {response.status_code}. "
            f"Response: {response.text}",
            status_code=response.status_code,
            response_text=response.text,
        )

    return response.text


def fetch_and_process_pull_requests(
    owner,
    repo,
    draft_filter=None,
    file_include=None,
    file_exclude=None,
    pr_number=None,
    url_from_pr_content=None,
    jira_client=None,
    jira_issue_patterns=None,
    jira_include=None,
    review_requested_for=None,
    github_token=None,
):
    """
    Fetches and processes pull requests for the specified repository.
    If a single PR number is specified, only that PR is fetched and processed.
    Returns a tuple of (pull_requests, jira_issues).

    Args:
        jira_issue_patterns: List of regex patterns to extract JIRA issue keys from file contents
        jira_include: List of JIRA issue keys to always include in the output
        review_requested_for: GitHub username to filter PRs by requested reviewer

    Returns:
        Tuple of (pull_requests, jira_issues) where:
        - pull_requests: List of processed pull request data
        - jira_issues: Dict mapping JIRA issue keys to their metadata
    """
    logging.info(f"Fetching pull requests for repository {owner}/{repo}")
    pull_requests = []
    logging.info("Loading pull request data...")

    if pr_number:
        # Fetch a single PR
        pr = fetch_single_pull_request(owner, repo, pr_number, github_token)
        if pr is None:
            logging.error(f"Failed to fetch PR #{pr_number}")
            return []
        prs = [pr]  # Wrap in a list for consistent processing
    else:
        # Fetch all PRs (filtered by review_requested_for if specified)
        # Always returns full PR objects with consistent structure
        prs = fetch_pull_requests(owner, repo, github_token, review_requested_for)
        if prs is None:
            logging.error("Failed to fetch pull requests")
            return []

    url_regex_compiled = None
    if url_from_pr_content:
        try:
            url_regex_compiled = re.compile(url_from_pr_content)
        except re.error as e:
            raise ValidationError(
                f"Invalid regular expression in --url-from-pr-content: '{url_from_pr_content}'. "
                f"Error: {e}. "
                f"Please provide a valid regular expression pattern."
            )

    # Preprocessing: Collect all JIRA issue keys and batch fetch metadata
    jira_metadata_cache: dict[str, dict[str, Any]] = {}
    pr_issue_keys_map: dict[int, list[str]] = {}

    if jira_client and jira_issue_patterns:
        logging.info(
            "Preprocessing: Collecting JIRA issues from all PRs for batch fetch..."
        )
        all_issue_keys: set[str] = set()

        # Add jira-include issues to the set
        if jira_include:
            all_issue_keys.update(jira_include)
            logging.info(
                f"Adding {len(jira_include)} jira-include issues: {', '.join(jira_include)}"
            )

        for pr in prs:
            pr = cast(dict[str, Any], pr)
            pr_number = pr["number"]
            pr_body = pr.get("body", "")
            file_contents_list = []

            # Fetch file contents if needed (same logic as main loop)
            if file_include:
                pr_ref = pr.get("head", {}).get("sha")
                if pr_ref:
                    files = fetch_pr_files(owner, repo, pr_number, github_token)
                    if files:
                        matching_files = []
                        for file in files:
                            file_path = file.get("filename", "")
                            if any(
                                pattern.search(file_path) for pattern in file_include
                            ):
                                matching_files.append(file_path)

                        for file_path in matching_files:
                            content = fetch_file_content(
                                owner, repo, file_path, pr_ref, github_token
                            )
                            if content:
                                file_contents_list.append(content)

            # Extract issue keys for this PR
            issue_keys = extract_issue_keys_from_pr(
                file_contents_list, jira_issue_patterns, pr_body
            )
            if issue_keys:
                pr_issue_keys_map[pr_number] = issue_keys
                all_issue_keys.update(issue_keys)
                logging.debug(f"PR #{pr_number}: found {len(issue_keys)} JIRA issues")

        # Batch fetch all metadata at once
        if all_issue_keys:
            unique_keys = sorted(all_issue_keys)
            logging.info(
                f"Batch fetching metadata for {len(unique_keys)} unique JIRA issues..."
            )
            try:
                # Fetch metadata with parent fields for hierarchy traversal
                jira_metadata_cache = jira_client.get_issues_metadata(
                    unique_keys, include_parent_fields=True
                )
                logging.info(
                    f"Successfully fetched metadata for {len(jira_metadata_cache)} issues with parent fields"
                )
            except JiraClientError as e:
                logging.error(f"Failed to batch fetch JIRA metadata: {e}")

    for pr in prs:
        pr = cast(dict[str, Any], pr)  # Type cast to fix linter errors
        logging.info(f"Processing PR #{pr['number']} - {pr['title']}")

        # Apply draft filter if specified
        if draft_filter == "no-drafts" and pr.get("draft", False):
            logging.debug(f"Excluding draft PR #{pr['number']}")
            continue
        if draft_filter == "only-drafts" and not pr.get("draft", False):
            logging.debug(f"Excluding non-draft PR #{pr['number']}")
            continue

        pr_number = pr["number"]

        # Apply file filters if specified
        if file_include or file_exclude:
            # Fetch files changed in the PR
            files = fetch_pr_files(owner, repo, pr_number, github_token)
            if files is None:
                logging.warning(
                    f"Failed to fetch files for PR #{pr_number}. File filters will be ignored for this PR. This may be due to network issues or API rate limits."
                )
                files = []
            file_paths = [file["filename"] for file in files]

            # Check file-exclude filters first
            if file_exclude and any(
                pattern.search(file_path)
                for pattern in file_exclude
                for file_path in file_paths
            ):
                logging.debug(
                    f"Excluding PR #{pr_number} due to file-exclude filter match"
                )
                continue

            # Check file-include filters
            if file_include and not any(
                pattern.search(file_path)
                for pattern in file_include
                for file_path in file_paths
            ):
                logging.debug(
                    f"Excluding PR #{pr_number} due to no file-include filter match"
                )
                continue

        pr_title = pr["title"]
        pr_author = pr["user"]["login"]
        pr_url = pr["html_url"]

        # Determine when the PR was last marked as ready for review
        pr_ready_date = None
        events = fetch_issue_events(owner, repo, pr_number, github_token)
        if events is not None:
            for event in events:
                if event["event"] == "ready_for_review":
                    event_date = event["created_at"]
                    logging.debug(
                        f"PR #{pr_number} marked ready for review on {event_date}"
                    )
                    if not pr_ready_date or event_date > pr_ready_date:
                        pr_ready_date = event_date

        if not pr_ready_date:
            pr_ready_date = pr["created_at"]

        pr_ready_date = pr_ready_date.split("T")[0]

        # Fetch author details
        author_details = fetch_user_details(pr_author, github_token)
        if author_details is not None:
            author_details = cast(
                dict[str, Any], author_details
            )  # Type cast to fix linter errors
            pr_author_name = (
                author_details.get("name") or pr_author
            )  # Fallback to username if name is None
            pr_author_url = author_details.get("html_url")
        else:
            logging.warning(
                f"Failed to fetch author details for {pr_author}. Using username as fallback. This may be due to network issues, API rate limits, or the user account being unavailable."
            )
            pr_author_name = pr_author
            pr_author_url = f"https://github.com/{pr_author}"

        # Fetch reviews and approvals
        reviews = fetch_reviews(owner, repo, pr_number, github_token)
        if reviews is None:
            logging.warning(
                f"Failed to fetch reviews for PR #{pr_number}. Review counts will be set to 0. This may be due to network issues or API rate limits."
            )
            reviews = []

        # Map to most recent review state per user
        user_latest_review: dict[str, dict[str, Any]] = {}
        for review in reviews:
            user = review["user"]["login"]
            submitted_at = review.get("submitted_at")
            state = review["state"]
            # Only consider reviews with a submitted_at timestamp (ignore pending, etc)
            if not submitted_at:
                continue
            # If user not seen or this review is newer, update
            if (
                user not in user_latest_review
                or submitted_at > user_latest_review[user]["submitted_at"]
            ):
                # If the new state is "COMMENTED" but the existing state is not "COMMENTED", ignore this review
                if (
                    user in user_latest_review
                    and user_latest_review[user]["state"] != "COMMENTED"
                    and state == "COMMENTED"
                ):
                    continue
                user_latest_review[user] = {
                    "state": state,
                    "submitted_at": submitted_at,
                }

        states = [data["state"] for data in user_latest_review.values()]
        pr_reviews = len(user_latest_review)
        pr_approvals = sum(1 for s in states if s == "APPROVED")
        pr_changes = sum(1 for s in states if s == "CHANGES_REQUESTED")

        # Optionally extract all unique URLs from the PR diff (added lines only), sorted by display text
        pr_body_urls_dict = {}
        if url_regex_compiled:
            diff = fetch_pr_diff(owner, repo, pr_number, github_token)
            if diff is not None:
                for line in diff.splitlines():
                    if line.startswith("+") and not line.startswith("+++"):
                        matches = url_regex_compiled.findall(line)
                        for match in matches:
                            url_text = (
                                match.rstrip("/").split("/")[-1]
                                if "/" in match
                                else match
                            )
                            pr_body_urls_dict[url_text] = (
                                match  # last occurrence wins if duplicate text
                            )
                # Sort the dict by url_text
                pr_body_urls_dict = dict(
                    sorted(pr_body_urls_dict.items(), key=lambda x: x[0])
                )
            else:
                logging.warning(
                    f"Failed to fetch diff for PR #{pr_number}. URL extraction will be skipped for this PR. This may be due to network issues or API rate limits."
                )

        # Get rank if JIRA client is configured (using pre-fetched metadata)
        pr_rank = None
        pr_closed_issue_keys: set[str] = set()
        if jira_client and pr_number in pr_issue_keys_map:
            issue_keys = pr_issue_keys_map[pr_number]
            pr_rank, pr_closed_issue_keys = get_rank_for_pr(
                jira_client, issue_keys, jira_metadata_cache
            )
            if pr_rank:
                logging.debug(f"PR #{pr_number} rank: {pr_rank}")

        pull_requests.append(
            {
                "date": pr_ready_date,
                "title": pr_title,
                "number": pr_number,
                "url": pr_url,
                "author_name": pr_author_name,
                "author_url": pr_author_url,
                "reviews": pr_reviews,
                "approvals": pr_approvals,
                "changes": pr_changes,
                "pr_body_urls_dict": pr_body_urls_dict,
                "rank": pr_rank or "",
                "closed_issue_keys": pr_closed_issue_keys,
            }
        )

    # Build JIRA issues dictionary from metadata cache
    jira_issues = {}
    if jira_client and jira_metadata_cache:
        for issue_key, issue_data in jira_metadata_cache.items():
            # Extract rank for this issue
            pr_rank, closed_keys = get_rank_for_pr(
                jira_client, [issue_key], jira_metadata_cache
            )

            # Get JIRA summary
            jira_summary = issue_data.get("fields", {}).get("summary", issue_key)

            jira_issues[issue_key] = {
                "title": jira_summary,
                "url": f"{jira_client.base_url}/browse/{issue_key}",
                "rank": pr_rank or "",
                "closed": issue_key in closed_keys,
            }

    logging.info("Done loading PR data.")

    return pull_requests, jira_issues


def parse_column_titles(args):
    """
    Parses custom column titles from command line arguments.
    Returns a dictionary with the final column titles to use.
    """
    default_titles = {
        "date": "Date",
        "title": "Title",
        "author": "Author",
        "changes": "Change Requested",
        "approvals": "Approvals",
        "urls": "URLs",
        "rank": "RANK",
    }
    custom_titles = {}
    if hasattr(args, "column_title") and args.column_title:
        for entry in args.column_title:
            if "=" in entry:
                col, val = entry.split("=", 1)
                col = col.strip().lower()
                if col in default_titles:
                    custom_titles[col] = val.strip()
                else:
                    logging.warning(
                        f"Invalid column name '{col}' in --column-title. Valid columns: {', '.join(default_titles.keys())}"
                    )
    return {**default_titles, **custom_titles}


def validate_sort_column(sort_column):
    """
    Validates the sort column and returns it in lowercase.
    Raises ValidationError if invalid.
    """
    allowed_columns = [
        "date",
        "title",
        "author",
        "changes",
        "approvals",
        "urls",
        "rank",
    ]
    sort_column = sort_column.lower()
    if sort_column not in allowed_columns:
        raise ValidationError(
            f"Invalid sort column: '{sort_column}'. "
            f"Valid options are: {', '.join(allowed_columns)}. "
            f"Use --sort-column to specify a valid column name."
        )
    return sort_column


def create_markdown_table_header(titles, url_column, rank_column):
    """
    Creates the markdown table header and separator rows.
    Returns a tuple of (header_row, separator_row).
    """
    header = f"| {titles['date']} | {titles['title']} | {titles['author']} | {titles['changes']} | {titles['approvals']} |"
    separator = "| --- | --- | --- | --- | --- |"

    if url_column:
        header = header + f" {titles['urls']} |"
        separator = separator + " --- |"

    if rank_column:
        header = header + f" {titles['rank']} |"
        separator = separator + " --- |"

    return header, separator


def create_markdown_table_row(pr, url_column, rank_column, jira_issues=None):
    """
    Creates a single markdown table row for a pull request.

    Args:
        pr: Pull request data dictionary
        url_column: Whether to include URLs column
        rank_column: Whether to include rank column
        jira_issues: Dictionary mapping JIRA keys to their data (for synthetic entries)
    """
    # Handle synthetic JIRA entries (no PR number)
    if pr["number"] is None and "jira_key" in pr:
        # Synthetic JIRA entry: lookup JIRA data
        jira_key = pr["jira_key"]
        if jira_issues and jira_key in jira_issues:
            jira_data = jira_issues[jira_key]
            title_link = f"[{jira_data['title']}]({jira_data['url']})"
        else:
            title_link = f"[{jira_key}]()"
        author_link = ""
        approvals_text = ""
        changes_text = ""
    else:
        # Regular PR entry
        title_link = f"{pr['title']} #[{pr['number']}]({pr['url']})"

        # Handle author
        if pr["author_name"]:
            author_link = f"[{pr['author_name']}]({pr['author_url']})"
        else:
            author_link = ""

        # Handle reviews/approvals
        if pr["reviews"] > 0:
            approvals_text = f"{pr['approvals']} of {pr['reviews']}"
        else:
            approvals_text = ""

        # Handle changes (always show for regular PRs, even if 0)
        changes_text = str(pr["changes"])

    row = f"| {pr['date']} | {title_link} | {author_link} | {changes_text} | {approvals_text} |"

    if url_column:
        if pr.get("pr_body_urls_dict") and pr["pr_body_urls_dict"]:
            closed_keys = pr.get("closed_issue_keys", set())
            url_links = []
            for text, url in pr["pr_body_urls_dict"].items():
                # Apply strikethrough to closed JIRA issues
                if text in closed_keys:
                    url_links.append(f"[~~{text}~~]({url})")
                else:
                    url_links.append(f"[{text}]({url})")
            row = row + f" {' '.join(url_links)} |"
        else:
            row = row + " |"

    if rank_column:
        rank_value = pr.get("rank", "")
        row = row + f" {rank_value} |"

    return row


def generate_markdown_output(args):
    """
    Generates Markdown output for the given list of pull requests.
    Takes `args` as the only argument.
    """
    # Compile regex patterns for file filters
    file_include = None
    file_exclude = None

    if args.file_include:
        file_include = []
        for pattern in args.file_include:
            try:
                file_include.append(re.compile(pattern))
            except re.error as e:
                raise ValidationError(
                    f"Invalid regular expression in --file-include: '{pattern}'. "
                    f"Error: {e}. "
                    f"Please provide a valid regular expression pattern."
                )

    if args.file_exclude:
        file_exclude = []
        for pattern in args.file_exclude:
            try:
                file_exclude.append(re.compile(pattern))
            except re.error as e:
                raise ValidationError(
                    f"Invalid regular expression in --file-exclude: '{pattern}'. "
                    f"Error: {e}. "
                    f"Please provide a valid regular expression pattern."
                )

    # Create JIRA client if rank is requested
    # Note: create_jira_client will raise an exception if --include-rank is specified
    # but JIRA is not properly configured, causing execution to fail
    jira_client = create_jira_client(args)

    # Get GitHub token from args or environment
    github_token = args.github_token or os.getenv("GITHUB_TOKEN")

    # Handle JIRA issue patterns - ensure it's always a list
    jira_issue_patterns = args.jira_issue_pattern
    if not jira_issue_patterns:
        # No patterns specified, use default
        jira_issue_patterns = [r"(ANSTRAT-\d+)"]
    elif isinstance(jira_issue_patterns, str):
        # Single pattern as string (e.g., from tests), convert to list
        jira_issue_patterns = [jira_issue_patterns]
    # else: already a list from argparse action="append"

    # Fetch and process pull requests
    pull_requests, jira_issues = fetch_and_process_pull_requests(
        args.owner,
        args.repo,
        args.draft_filter,
        file_include,
        file_exclude,
        args.pr_number,
        args.url_from_pr_content,
        jira_client=jira_client,
        jira_issue_patterns=jira_issue_patterns,
        jira_include=args.jira_include,
        review_requested_for=args.review_requested_for,
        github_token=github_token,
    )

    # Add synthetic entries for jira-include issues that weren't found in any PRs
    if args.jira_include and jira_issues:
        # Collect all issue keys already present in pull_requests
        existing_issue_keys = set()
        for pr in pull_requests:
            if pr.get("rank"):
                # Extract issue key from rank (format: "rank_value ISSUE-123")
                rank_parts = pr["rank"].split()
                if rank_parts:
                    issue_key = rank_parts[-1]
                    existing_issue_keys.add(issue_key)

        # Create synthetic entries for missing issues
        for issue_key in args.jira_include:
            if issue_key not in existing_issue_keys and issue_key in jira_issues:
                jira_data = jira_issues[issue_key]
                if jira_data.get("rank"):  # Only include if has valid rank
                    logging.info(
                        f"Creating synthetic entry for jira-include issue {issue_key}"
                    )
                    pull_requests.append(
                        {
                            "date": "",
                            "title": None,  # No PR title
                            "number": None,  # No PR number - marker for synthetic entry
                            "url": None,  # No PR URL
                            "jira_key": issue_key,  # Reference to jira_issues dict
                            "author_name": "",
                            "author_url": "",
                            "reviews": 0,
                            "approvals": 0,
                            "changes": "",
                            "pr_body_urls_dict": {},
                            "rank": jira_data["rank"],
                            "closed_issue_keys": set(),
                        }
                    )
                else:
                    logging.warning(
                        f"Could not get rank for jira-include issue {issue_key} - skipping"
                    )

    # Determine if we need to add URL and rank columns
    url_column = bool(args.url_from_pr_content)
    rank_column = bool(args.include_rank)

    # Handle custom column titles
    titles = parse_column_titles(args)

    # Validate sort column
    sort_column = validate_sort_column(getattr(args, "sort_column", "date"))

    # Add down arrow to sorted column
    for col in titles.keys():
        if col == sort_column:
            titles[col] = titles[col] + " 🔽"
            break

    # Generate Markdown output
    output = []
    header, separator = create_markdown_table_header(titles, url_column, rank_column)
    output.append(header)
    output.append(separator)

    # Sort by the selected column
    def sort_key(pr):
        key = sort_column
        if key == "urls":
            return (
                ",".join(pr.get("pr_body_urls_dict", {}).keys())
                if pr.get("pr_body_urls_dict")
                else ""
            )
        if key == "rank":
            # Empty ranks should sort to the end
            rank_value = pr.get("rank", "")
            if not rank_value:
                return "z" * 100
            return rank_value
        return pr.get(key, "")

    sorted_prs = sorted(pull_requests, key=sort_key)

    # Add data rows
    for pr in sorted_prs:
        row = create_markdown_table_row(pr, url_column, rank_column, jira_issues)
        output.append(row)

    return "\n".join(output)


def generate_timestamp(current_time=None, generator_name=None, generator_url=None):
    """
    Returns the current timestamp in Markdown syntax, including the generator's name and link if provided.
    """
    from datetime import datetime, timezone

    if current_time is None:
        current_time = datetime.now(timezone.utc)
    timestamp = current_time.strftime("**Generated at %Y-%m-%d %H:%MZ**")
    if generator_name and generator_url:
        timestamp += f" by [{generator_name}]({generator_url})"
    elif generator_name:
        timestamp += f" by {generator_name}"
    timestamp += "\n"
    return timestamp


def get_authenticated_user_info(github_token=None):
    """
    Fetch the authenticated user's info from the GitHub API.
    Returns (name, html_url) or (None, None) if not available.
    """
    headers = get_github_headers(github_token)
    try:
        resp = requests.get("https://api.github.com/user", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            name = data.get("name") or data.get("login")
            html_url = data.get("html_url")
            return name, html_url
    except Exception:  # pragma: no cover
        pass
    return None, None


def main():
    """
    Main function to fetch and summarize GitHub pull requests.
    """
    try:
        args = parse_arguments()
    except Exception as e:
        print(f"ERROR: Failed to parse command line arguments. {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure owner and repo are provided
    if not args.owner or not args.repo:
        print("ERROR: Repository owner and name must be specified.", file=sys.stderr)
        print(
            "Either provide --owner and --repo arguments, or run the command",
            file=sys.stderr,
        )
        print("from within a Git repository with a GitHub remote.", file=sys.stderr)
        sys.exit(1)

    configure_logging(args.debug)

    try:
        # Generate Markdown output
        markdown_output = generate_markdown_output(args)
    except ValidationError as e:
        print(f"ERROR: Input validation failed. {e}", file=sys.stderr)
        sys.exit(1)
    except JiraClientError as e:
        print(f"ERROR: JIRA error. {e}", file=sys.stderr)
        sys.exit(1)
    except RateLimitError as e:
        print(f"ERROR: GitHub API rate limit exceeded. {e}", file=sys.stderr)
        sys.exit(1)
    except GitHubAPIError as e:
        print(f"ERROR: GitHub API error. {e}", file=sys.stderr)
        if args.debug and hasattr(e, "status_code"):
            print(f"Status Code: {e.status_code}", file=sys.stderr)
            print(f"Response: {e.response_text}", file=sys.stderr)
        sys.exit(1)
    except NetworkError as e:
        print(f"ERROR: Network error. {e}", file=sys.stderr)
        sys.exit(1)

    # Get GitHub token from args or environment
    github_token = args.github_token or os.getenv("GITHUB_TOKEN")

    # Determine user info using GitHub API /user if possible
    name, url = get_authenticated_user_info(github_token)

    # Print timestamp and Markdown output, and capture their values
    timestamp_output = generate_timestamp(generator_name=name, generator_url=url)

    # Write Markdown output (with timestamp) to file, else write to stdout
    if args.output_markdown:
        try:
            with open(args.output_markdown, "w", encoding="utf-8") as f:
                f.write(f"{timestamp_output}\n{markdown_output}\n")
            print(
                f"Markdown output written to: {args.output_markdown}", file=sys.stderr
            )
        except PermissionError:
            print(
                f"ERROR: Permission denied writing to file: {args.output_markdown}",
                file=sys.stderr,
            )
            print("Please check file permissions and try again.", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(
                f"ERROR: Directory not found for output file: {args.output_markdown}",
                file=sys.stderr,
            )
            print("Please ensure the directory exists and try again.", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(
                f"ERROR: Failed to write to file {args.output_markdown}. {e}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        try:
            print(f"{timestamp_output}\n{markdown_output}\n")
        except BrokenPipeError:
            # Handle case where output is piped to another command that exits early
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: Failed to write output. {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT
    except ValidationError as e:
        print(f"ERROR: Input validation failed. {e}", file=sys.stderr)
        sys.exit(1)
    except JiraClientError as e:
        print(f"ERROR: JIRA error. {e}", file=sys.stderr)
        sys.exit(1)
    except RateLimitError as e:
        print(f"ERROR: GitHub API rate limit exceeded. {e}", file=sys.stderr)
        sys.exit(1)
    except GitHubAPIError as e:
        print(f"ERROR: GitHub API error. {e}", file=sys.stderr)
        sys.exit(1)
    except NetworkError as e:
        print(f"ERROR: Network error. {e}", file=sys.stderr)
        sys.exit(1)
    except FileOperationError as e:
        print(f"ERROR: File operation failed. {e}", file=sys.stderr)
        sys.exit(1)
    except MissingRepoError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print(
            "Either provide --owner and --repo arguments, or run the command",
            file=sys.stderr,
        )
        print("from within a Git repository with a GitHub remote.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred. {e}", file=sys.stderr)
        print("If this error persists, please report it as a bug.", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
