#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import os
import requests
import sys
import argparse
import logging
import argcomplete
import subprocess
import re
from typing import Dict, Any, cast

# Configuration
GITHUB_API_BASE = "https://api.github.com"

# Optional GitHub token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set this in your environment variables

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

if GITHUB_TOKEN: # pragma: no cover
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


# Custom Exception Classes
class MissingRepoError(Exception):
    """Raised when repository information cannot be determined."""
    pass


class GitHubAPIError(Exception):
    """Raised when GitHub API requests fail."""
    def __init__(self, message, status_code=None, response_text=None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class RateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""
    pass


class NetworkError(Exception):
    """Raised when network-related errors occur."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class FileOperationError(Exception):
    """Raised when file operations fail."""
    pass


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
            text=True
        ).strip()

        # Parse the remote URL to extract owner and repo
        if remote_url.startswith("git@"):
            # SSH URL (e.g., git@github.com:owner/repo.git)
            _, path = remote_url.split(":", 1)
        elif remote_url.startswith("https://"):
            # HTTPS URL (e.g., https://github.com/owner/repo.git)
            parts = remote_url.split("/", 5)  # Split into up to 6 parts: ["https:", "", "domain", "owner", "repo", "extra/path..."]
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

    parser = argparse.ArgumentParser(description="Fetch and summarize GitHub pull requests.")
    parser.add_argument("--owner", default=default_owner, help="The owner of the repository (e.g., 'microsoft'). If not specified, defaults to the owner from the current directory's Git config.")
    parser.add_argument("--repo", default=default_repo, help="The name of the repository (e.g., 'vscode'). If not specified, defaults to the repo name from the current directory's Git config.")
    parser.add_argument(
        "--pr-number",
        type=int,
        help="Specify a single pull request number to query."
    )
    parser.add_argument(
        "--draft-filter",
        choices=["only-drafts", "no-drafts"],
        help="Filter pull requests based on draft status. Use 'only-drafts' to include only drafts, or 'no-drafts' to exclude drafts."
    )
    parser.add_argument(
        "--file-include",
        action="append",
        help="Regex pattern to include pull requests based on changed file paths. Can be specified multiple times."
    )
    parser.add_argument(
        "--file-exclude",
        action="append",
        help="Regex pattern to exclude pull requests based on changed file paths. Can be specified multiple times."
    )
    parser.add_argument(
        "--url-from-pr-content",
        type=str,
        help="Regex pattern to extract all unique URLs from added lines in the PR diff. If set, adds a column to the output table with the matched URLs."
    )
    parser.add_argument(
        "--output-markdown",
        type=str,
        help="Path to write the generated Markdown output (with timestamp) to a file. If not set, output is printed to stdout only."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and show tracebacks on error."
    )
    parser.add_argument(
        "--column-title",
        action="append",
        help="Override the title for any output column. Format: COLUMN=TITLE. Valid COLUMN values: date, title, author, changes, approvals, urls. Can be specified multiple times."
    )
    parser.add_argument(
        "--sort-column",
        type=str,
        default="date",
        help="Specify which output column to sort by. Valid values: date, title, author, changes, approvals, urls. Default is 'date'."
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
        ]
    )


def github_api_request(endpoint, params=None, use_paging=True):
    """
    Makes a GitHub API request and optionally handles pagination.
    Returns all results across all pages if pagination is enabled.
    Returns None if no results are found or an error occurs.
    """
    if params is None:
        params = {}

    all_results = []
    page = 1
    last_results = None  # Fail-safe to detect duplicate results

    while True:
        if use_paging:
            params["page"] = page
        url = f"{GITHUB_API_BASE}{endpoint}"
        logging.debug(f"Making API request to {url} with params {params}")
        
        try:
            response = requests.get(url, headers=HEADERS, params=params)
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Network connection failed. Please check your internet connection and try again. Details: {e}")
        except requests.exceptions.Timeout as e:
            raise NetworkError(f"Request timed out. The GitHub API may be slow. Please try again. Details: {e}")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error occurred while contacting GitHub API. Details: {e}")

        if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers and response.headers["X-RateLimit-Remaining"] == "0":
            reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
            raise RateLimitError(
                f"GitHub API rate limit exceeded. "
                f"Rate limit will reset at {reset_time}. "
                f"Consider using a GitHub token to increase your rate limit (5000 requests/hour vs 60 requests/hour). "
                f"Set the GITHUB_TOKEN environment variable with a personal access token."
            )
        
        if response.status_code == 401:
            raise GitHubAPIError(
                "GitHub API authentication failed. Please check your GITHUB_TOKEN if set. "
                "You may need to generate a new personal access token from GitHub Settings.",
                status_code=401,
                response_text=response.text
            )
        
        if response.status_code == 404:
            raise GitHubAPIError(
                f"GitHub API endpoint not found: {endpoint}. "
                f"Please verify the repository owner and name are correct.",
                status_code=404,
                response_text=response.text
            )
        
        if response.status_code != 200:
            raise GitHubAPIError(
                f"GitHub API request failed with status {response.status_code}. "
                f"Endpoint: {endpoint}. "
                f"Response: {response.text}",
                status_code=response.status_code,
                response_text=response.text
            )

        try:
            results = response.json()
        except ValueError as e:
            raise GitHubAPIError(f"Invalid JSON response from GitHub API. The service may be experiencing issues. Details: {e}")

        if results == last_results: # pragma: no cover
            logging.warning(f"Duplicate results detected for pages {page-1} and {page}. This may indicate a GitHub API issue.")
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


def fetch_pull_requests(owner, repo):
    """
    Fetches all open pull requests for the specified repository.
    """
    endpoint = f"/repos/{owner}/{repo}/pulls"
    params = {"state": "open"}
    logging.debug(f"Fetching pull requests for {owner}/{repo}")
    return github_api_request(endpoint, params)


def fetch_single_pull_request(owner, repo, pr_number):
    """
    Fetches a single pull request by its number.
    """
    endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
    logging.debug(f"Fetching single pull request #{pr_number} for {owner}/{repo}")
    return github_api_request(endpoint, use_paging=False)


def fetch_issue_events(owner, repo, pr_number):
    """
    Fetches all issue events for a specific pull request.
    """
    endpoint = f"/repos/{owner}/{repo}/issues/{pr_number}/events"
    logging.debug(f"Fetching issue events for PR #{pr_number}")
    return github_api_request(endpoint)


def fetch_reviews(owner, repo, pr_number):
    """
    Fetches all reviews for a specific pull request.
    """
    endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    logging.debug(f"Fetching reviews for PR #{pr_number}")
    return github_api_request(endpoint)


def fetch_user_details(username):
    """
    Fetches details for a specific GitHub user.
    Returns None if user is not found (404 error).
    """
    url = f"{GITHUB_API_BASE}/users/{username}"
    logging.debug(f"Fetching user details for {username}")
    
    try:
        response = requests.get(url, headers=HEADERS)
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(f"Network connection failed while fetching user details for {username}. Please check your internet connection and try again.")
    except requests.exceptions.Timeout as e:
        raise NetworkError(f"Request timed out while fetching user details for {username}. The GitHub API may be slow. Please try again.")
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error occurred while fetching user details for {username}. Details: {e}")
    
    if response.status_code == 404:
        logging.debug(f"User {username} not found (404), returning None")
        return None
    elif response.status_code == 403 and "X-RateLimit-Remaining" in response.headers and response.headers["X-RateLimit-Remaining"] == "0":
        reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
        raise RateLimitError(
            f"GitHub API rate limit exceeded while fetching user {username}. "
            f"Rate limit will reset at {reset_time}. "
            f"Consider using a GitHub token to increase your rate limit."
        )
    elif response.status_code != 200:
        raise GitHubAPIError(
            f"Failed to fetch user details for {username}. "
            f"GitHub API returned status {response.status_code}. "
            f"Response: {response.text}",
            status_code=response.status_code,
            response_text=response.text
        )
    
    try:
        return response.json()
    except ValueError as e:
        raise GitHubAPIError(f"Invalid JSON response when fetching user details for {username}. The GitHub API may be experiencing issues. Details: {e}")


def fetch_pr_files(owner, repo, pr_number):
    """
    Fetches the list of files changed in a specific pull request.
    """
    endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
    logging.debug(f"Fetching files for PR #{pr_number}")
    files = github_api_request(endpoint, use_paging=True)
    logging.debug(f"Files fetched for PR #{pr_number}: {files}")
    return files


def fetch_pr_diff(owner, repo, pr_number):
    """
    Fetches the diff for a specific pull request using the GitHub API.
    Returns the diff as a string.
    """
    if not pr_number:
        return None

    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = HEADERS.copy()
    headers["Accept"] = "application/vnd.github.v3.diff"
    
    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(f"Network connection failed while fetching diff for PR #{pr_number}. Please check your internet connection and try again.")
    except requests.exceptions.Timeout as e:
        raise NetworkError(f"Request timed out while fetching diff for PR #{pr_number}. The GitHub API may be slow. Please try again.")
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network error occurred while fetching diff for PR #{pr_number}. Details: {e}")
    
    if response.status_code == 404:
        raise GitHubAPIError(
            f"Pull request #{pr_number} not found in repository {owner}/{repo}. "
            f"Please verify the PR number and repository are correct.",
            status_code=404,
            response_text=response.text
        )
    elif response.status_code == 403:
        raise GitHubAPIError(
            f"Access denied when fetching diff for PR #{pr_number}. "
            f"The repository may be private or you may have exceeded rate limits. "
            f"Consider using a GitHub token with appropriate permissions.",
            status_code=403,
            response_text=response.text
        )
    elif response.status_code != 200:
        raise GitHubAPIError(
            f"Failed to fetch diff for PR #{pr_number}. "
            f"GitHub API returned status {response.status_code}. "
            f"Response: {response.text}",
            status_code=response.status_code,
            response_text=response.text
        )
    
    return response.text


def fetch_and_process_pull_requests(owner, repo, draft_filter=None, file_include=None, file_exclude=None, pr_number=None, url_from_pr_content=None):
    """
    Fetches and processes pull requests for the specified repository.
    If a single PR number is specified, only that PR is fetched and processed.
    Returns a list of processed pull request data.
    """
    logging.info(f"Fetching pull requests for repository {owner}/{repo}")
    pull_requests = []
    logging.info("Loading pull request data...")

    if pr_number:
        # Fetch a single PR
        pr = fetch_single_pull_request(owner, repo, pr_number)
        if pr is None:
            logging.error(f"Failed to fetch PR #{pr_number}")
            return []
        prs = [pr]  # Wrap in a list for consistent processing
    else:
        # Fetch all PRs
        prs = fetch_pull_requests(owner, repo)
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

    for pr in prs:
        pr = cast(Dict[str, Any], pr)  # Type cast to fix linter errors
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
            files = fetch_pr_files(owner, repo, pr_number)
            if files is None:
                logging.warning(f"Failed to fetch files for PR #{pr_number}. File filters will be ignored for this PR. This may be due to network issues or API rate limits.")
                files = []
            file_paths = [file["filename"] for file in files]

            # Check file-exclude filters first
            if file_exclude and any(pattern.search(file_path) for pattern in file_exclude for file_path in file_paths):
                logging.debug(f"Excluding PR #{pr_number} due to file-exclude filter match")
                continue

            # Check file-include filters
            if file_include and not any(pattern.search(file_path) for pattern in file_include for file_path in file_paths):
                logging.debug(f"Excluding PR #{pr_number} due to no file-include filter match")
                continue

        pr_title = pr["title"]
        pr_author = pr["user"]["login"]
        pr_url = pr["html_url"]

        # Determine when the PR was last marked as ready for review
        pr_ready_date = None
        events = fetch_issue_events(owner, repo, pr_number)
        if events is not None:
            for event in events:
                if event["event"] == "ready_for_review":
                    event_date = event["created_at"]
                    logging.debug(f"PR #{pr_number} marked ready for review on {event_date}")
                    if not pr_ready_date or event_date > pr_ready_date:
                        pr_ready_date = event_date

        if not pr_ready_date:
            pr_ready_date = pr["created_at"]

        pr_ready_date = pr_ready_date.split("T")[0]

        # Fetch author details
        author_details = fetch_user_details(pr_author)
        if author_details is not None:
            author_details = cast(Dict[str, Any], author_details)  # Type cast to fix linter errors
            pr_author_name = author_details.get("name") or pr_author  # Fallback to username if name is None
            pr_author_url = author_details.get("html_url")
        else:
            logging.warning(f"Failed to fetch author details for {pr_author}. Using username as fallback. This may be due to network issues, API rate limits, or the user account being unavailable.")
            pr_author_name = pr_author
            pr_author_url = f"https://github.com/{pr_author}"

        # Fetch reviews and approvals
        reviews = fetch_reviews(owner, repo, pr_number)
        if reviews is None:
            logging.warning(f"Failed to fetch reviews for PR #{pr_number}. Review counts will be set to 0. This may be due to network issues or API rate limits.")
            reviews = []
            
        # Map to most recent review state per user
        user_latest_review = {}
        for review in reviews:
            user = review["user"]["login"]
            submitted_at = review.get("submitted_at")
            state = review["state"]
            # Only consider reviews with a submitted_at timestamp (ignore pending, etc)
            if not submitted_at:
                continue
            # If user not seen or this review is newer, update
            if user not in user_latest_review or submitted_at > user_latest_review[user]["submitted_at"]:
                # If the new state is "COMMENTED" but the existing state is not "COMMENTED", ignore this review
                if user in user_latest_review and user_latest_review[user]["state"] != "COMMENTED" and state == "COMMENTED":
                    continue
                user_latest_review[user] = {"state": state, "submitted_at": submitted_at}

        states = [data["state"] for data in user_latest_review.values()]
        pr_reviews = len(user_latest_review)
        pr_approvals = sum(1 for s in states if s == "APPROVED")
        pr_changes = sum(1 for s in states if s == "CHANGES_REQUESTED")

        # Optionally extract all unique URLs from the PR diff (added lines only), sorted by display text
        pr_body_urls_dict = {}
        if url_regex_compiled:
            diff = fetch_pr_diff(owner, repo, pr_number)
            if diff is not None:
                for line in diff.splitlines():
                    if line.startswith('+') and not line.startswith('+++'):
                        matches = url_regex_compiled.findall(line)
                        for match in matches:
                            url_text = match.rstrip("/").split("/")[-1] if "/" in match else match
                            pr_body_urls_dict[url_text] = match  # last occurrence wins if duplicate text
                # Sort the dict by url_text
                pr_body_urls_dict = dict(sorted(pr_body_urls_dict.items(), key=lambda x: x[0]))
            else:
                logging.warning(f"Failed to fetch diff for PR #{pr_number}. URL extraction will be skipped for this PR. This may be due to network issues or API rate limits.")

        pull_requests.append({
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
        })

    logging.info("Done loading PR data.")    

    return pull_requests


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
        "urls": "URLs"
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
                    logging.warning(f"Invalid column name '{col}' in --column-title. Valid columns: {', '.join(default_titles.keys())}")
    return {**default_titles, **custom_titles}


def validate_sort_column(sort_column):
    """
    Validates the sort column and returns it in lowercase.
    Raises ValidationError if invalid.
    """
    allowed_columns = ["date", "title", "author", "changes", "approvals", "urls"]
    sort_column = sort_column.lower()
    if sort_column not in allowed_columns:
        raise ValidationError(
            f"Invalid sort column: '{sort_column}'. "
            f"Valid options are: {', '.join(allowed_columns)}. "
            f"Use --sort-column to specify a valid column name."
        )
    return sort_column


def create_markdown_table_header(titles, url_column):
    """
    Creates the markdown table header and separator rows.
    Returns a tuple of (header_row, separator_row).
    """
    header = f"| {titles['date']} | {titles['title']} | {titles['author']} | {titles['changes']} | {titles['approvals']} |"
    if url_column:
        header = header + f" {titles['urls']} |"
    
    separator = "| --- | --- | --- | --- | --- |"
    if url_column:
        separator = separator + " --- |"
    
    return header, separator


def create_markdown_table_row(pr, url_column):
    """
    Creates a single markdown table row for a pull request.
    """
    row = f"| {pr['date']} | {pr['title']} #[{pr['number']}]({pr['url']}) | [{pr['author_name']}]({pr['author_url']}) | {pr['changes']} | {pr['approvals']} of {pr['reviews']} |"
    if url_column:
        if pr.get("pr_body_urls_dict") and pr["pr_body_urls_dict"]:
            url_links = " ".join(f"[{text}]({url})" for text, url in pr["pr_body_urls_dict"].items())
            row = row + f" {url_links} |"
        else:
            row = row + " |"
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

    # Fetch and process pull requests
    pull_requests = fetch_and_process_pull_requests(
        args.owner, args.repo, args.draft_filter, file_include, file_exclude, args.pr_number, args.url_from_pr_content
    )

    # Determine if we need to add a URL column
    url_column = bool(args.url_from_pr_content)

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
    header, separator = create_markdown_table_header(titles, url_column)
    output.append(header)
    output.append(separator)
    
    # Sort by the selected column
    def sort_key(pr):
        key = sort_column
        if key == "urls":
            return ",".join(pr.get("pr_body_urls_dict", {}).keys()) if pr.get("pr_body_urls_dict") else ""
        return pr.get(key, "")
    
    sorted_prs = sorted(pull_requests, key=sort_key)
    
    # Add data rows
    for pr in sorted_prs:
        row = create_markdown_table_row(pr, url_column)
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


def get_authenticated_user_info():
    """
    Fetch the authenticated user's info from the GitHub API.
    Returns (name, html_url) or (None, None) if not available.
    """
    try:
        resp = requests.get("https://api.github.com/user", headers=HEADERS, timeout=5)
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
        print("Either provide --owner and --repo arguments, or run the command", file=sys.stderr)
        print("from within a Git repository with a GitHub remote.", file=sys.stderr)
        sys.exit(1)

    configure_logging(args.debug)

    try:
        # Generate Markdown output
        markdown_output = generate_markdown_output(args)
    except ValidationError as e:
        print(f"ERROR: Input validation failed. {e}", file=sys.stderr)
        sys.exit(1)
    except RateLimitError as e:
        print(f"ERROR: GitHub API rate limit exceeded. {e}", file=sys.stderr)
        sys.exit(1)
    except GitHubAPIError as e:
        print(f"ERROR: GitHub API error. {e}", file=sys.stderr)
        if args.debug and hasattr(e, 'status_code'):
            print(f"Status Code: {e.status_code}", file=sys.stderr)
            print(f"Response: {e.response_text}", file=sys.stderr)
        sys.exit(1)
    except NetworkError as e:
        print(f"ERROR: Network error. {e}", file=sys.stderr)
        sys.exit(1)

    # Determine user info using GitHub API /user if possible
    name, url = get_authenticated_user_info()

    # Print timestamp and Markdown output, and capture their values
    timestamp_output = generate_timestamp(generator_name=name, generator_url=url)

    # Write Markdown output (with timestamp) to file, else write to stdout
    if args.output_markdown:
        try:
            with open(args.output_markdown, "w", encoding="utf-8") as f:
                f.write(f"{timestamp_output}\n{markdown_output}\n")
            print(f"Markdown output written to: {args.output_markdown}", file=sys.stderr)
        except PermissionError:
            print(f"ERROR: Permission denied writing to file: {args.output_markdown}", file=sys.stderr)
            print("Please check file permissions and try again.", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"ERROR: Directory not found for output file: {args.output_markdown}", file=sys.stderr)
            print("Please ensure the directory exists and try again.", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"ERROR: Failed to write to file {args.output_markdown}. {e}", file=sys.stderr)
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
        print("Either provide --owner and --repo arguments, or run the command", file=sys.stderr)
        print("from within a Git repository with a GitHub remote.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred. {e}", file=sys.stderr)
        print("If this error persists, please report it as a bug.", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
