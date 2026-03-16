"""
GitHub API interaction functions.
"""

import logging
import time
from urllib.parse import quote

import requests

from gh_pulls_summary.common import (
    GITHUB_API_BASE,
    GitHubAPIError,
    NetworkError,
    RateLimitError,
    get_github_headers,
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
            params.setdefault("per_page", 100)
        url = f"{GITHUB_API_BASE}{endpoint}"
        logging.debug(f"Making API request to {url} with params {params}")

        # Retry loop for rate limiting
        retry_count = 0
        while retry_count <= max_retries:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
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
    endpoint = f"/users/{username}"
    headers = get_github_headers(github_token)
    logging.debug(f"Fetching user details for {username}")
    try:
        return github_api_request(endpoint, use_paging=False, headers=headers)
    except GitHubAPIError as e:
        if e.status_code == 404:
            logging.debug(f"User {username} not found (404), returning None")
            return None
        raise


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
        response = requests.get(url, headers=headers, timeout=30)
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
