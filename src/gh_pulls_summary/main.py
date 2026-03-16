#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argparse
import logging
import os
import re
import subprocess
import sys
from typing import Any, cast

import argcomplete

from gh_pulls_summary.common import (  # noqa: F401
    GitHubAPIError,
    JiraIssueData,
    NetworkError,
    PullRequestData,
    RateLimitError,
    ValidationError,
    get_github_headers,
)
from gh_pulls_summary.github_api import (  # noqa: F401
    fetch_file_content,
    fetch_issue_events,
    fetch_pr_diff,
    fetch_pr_files,
    fetch_pull_requests,
    fetch_reviews,
    fetch_single_pull_request,
    fetch_user_details,
    get_authenticated_user_info,
    github_api_request,
)
from gh_pulls_summary.jira_client import JiraClient, JiraClientError  # noqa: F401
from gh_pulls_summary.jira_processing import (  # noqa: F401
    create_jira_client,
    extract_issue_keys_from_pr,
    extract_jira_from_file_contents,
    extract_jira_issue_keys,
    extract_primary_jira_from_file_contents,
    extract_primary_jira_from_metadata,
    get_rank_for_pr,
)
from gh_pulls_summary.output import (
    create_markdown_table_header,
    create_markdown_table_row,
    generate_timestamp,
    parse_column_titles,
    validate_sort_column,
)


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
        help="JIRA instance base URL (e.g., 'https://yourorg.atlassian.net'). Can also be set via JIRA_BASE_URL environment variable.",
    )
    parser.add_argument(
        "--jira-user",
        type=str,
        help="JIRA user email for Atlassian Cloud authentication. Can also be set via JIRA_USER environment variable.",
    )
    parser.add_argument(
        "--jira-token",
        type=str,
        help="JIRA API token for Atlassian Cloud authentication. Can also be set via JIRA_TOKEN environment variable.",
    )
    parser.add_argument(
        "--jira-rank-field",
        type=str,
        help="Explicit JIRA Rank field ID (e.g., 'customfield_12311940'). If not provided, will attempt automatic discovery.",
    )
    parser.add_argument(
        "--include-rank",
        action="store_true",
        help="Include JIRA rank column in output. Requires JIRA configuration (--jira-url or JIRA_BASE_URL). Only includes issues of type Feature and Initiative.",
    )
    parser.add_argument(
        "--jira-issue-pattern",
        type=str,
        action="append",
        help="Regex pattern to extract JIRA issue keys from file contents. Use parentheses to capture the issue key (e.g., '(PROJECT-\\d+)'). Can be specified multiple times to use multiple patterns.",
    )
    parser.add_argument(
        "--jira-include",
        type=str,
        action="append",
        help="Always include this JIRA issue in the output, regardless of filters. Useful for marker stories when looking at rankings. Can be specified multiple times.",
    )
    parser.add_argument(
        "--jira-metadata-row-pattern",
        type=str,
        default=r"feature\s*/?\s*initiative",
        help="Regex pattern to identify the metadata table row containing primary JIRA issue (case-insensitive). Default is 'feature\\s*/?\\s*initiative' to match rows like '| **Feature / Initiative** | [PROJECT-1234](...) |'.",
    )
    parser.add_argument(
        "--jira-metadata-row-search-depth",
        type=int,
        default=50,
        help="Number of lines to search from the top of PR body and proposal files for metadata table. Use -1 to search entire files. Default is 50.",
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
    jira_metadata_row_pattern=None,
    jira_metadata_search_depth=None,
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
        jira_metadata_row_pattern: Regex pattern to identify metadata row (case-insensitive)
        jira_metadata_search_depth: Number of lines to search from top (-1 for unlimited)
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
            return [], {}
        prs = [pr]  # Wrap in a list for consistent processing
    else:
        # Fetch all PRs (filtered by review_requested_for if specified)
        # Always returns full PR objects with consistent structure
        prs = fetch_pull_requests(owner, repo, github_token, review_requested_for)
        if prs is None:
            logging.error("Failed to fetch pull requests")
            return [], {}

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
                file_contents_list,
                jira_issue_patterns,
                pr_body,
                jira_metadata_row_pattern,
                jira_metadata_search_depth,
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
            pr_author_url = (
                author_details.get("html_url") or f"https://github.com/{pr_author}"
            )
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
            PullRequestData(
                date=pr_ready_date,
                title=pr_title,
                number=pr_number,
                url=pr_url,
                author_name=pr_author_name,
                author_url=pr_author_url,
                reviews=pr_reviews,
                approvals=pr_approvals,
                changes=pr_changes,
                pr_body_urls_dict=pr_body_urls_dict,
                rank=pr_rank or "",
                closed_issue_keys=pr_closed_issue_keys,
            )
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

            jira_issues[issue_key] = JiraIssueData(
                title=jira_summary,
                url=f"{jira_client.base_url}/browse/{issue_key}",
                rank=pr_rank or "",
                closed=issue_key in closed_keys,
            )

    logging.info("Done loading PR data.")

    return pull_requests, jira_issues


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
        jira_issue_patterns = []
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
        jira_metadata_row_pattern=args.jira_metadata_row_pattern,
        jira_metadata_search_depth=args.jira_metadata_row_search_depth,
        review_requested_for=args.review_requested_for,
        github_token=github_token,
    )

    # Add synthetic entries for jira-include issues that weren't found in any PRs
    if args.jira_include and jira_issues:
        # Collect all issue keys already present in pull_requests
        existing_issue_keys = set()
        for pr in pull_requests:
            if pr.rank:
                # Extract issue key from rank (format: "rank_value ISSUE-123")
                rank_parts = pr.rank.split()
                if rank_parts:
                    issue_key = rank_parts[-1]
                    existing_issue_keys.add(issue_key)

        # Create synthetic entries for missing issues
        for issue_key in args.jira_include:
            if issue_key not in existing_issue_keys and issue_key in jira_issues:
                jira_data = jira_issues[issue_key]
                if jira_data.rank:  # Only include if has valid rank
                    logging.info(
                        f"Creating synthetic entry for jira-include issue {issue_key}"
                    )
                    pull_requests.append(
                        PullRequestData(
                            date="",
                            title=None,
                            number=None,
                            url=None,
                            jira_key=issue_key,
                            author_name="",
                            author_url="",
                            reviews=0,
                            approvals=0,
                            changes="",
                            rank=jira_data.rank,
                        )
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
            return ",".join(pr.pr_body_urls_dict.keys()) if pr.pr_body_urls_dict else ""
        if key == "rank":
            if not pr.rank:
                return "z" * 100
            return pr.rank
        return getattr(pr, key, "")

    # Two-phase sort: first by PR number (ascending) for stable baseline,
    # then by the requested column (stable sort preserves PR number order for ties)
    pr_number_sorted = sorted(pull_requests, key=lambda pr: pr.number or 0)
    sorted_prs = sorted(pr_number_sorted, key=sort_key)

    # Add data rows
    for pr in sorted_prs:
        row = create_markdown_table_row(pr, url_column, rank_column, jira_issues)
        output.append(row)

    # Close JIRA client session if it was created
    if jira_client:
        jira_client.close()

    return "\n".join(output)


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
