"""
JIRA issue extraction and ranking functions.
"""

import logging
import re
from typing import Any

from gh_pulls_summary.jira_client import JiraClient, JiraClientError


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
            user=args.jira_user,
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


def extract_primary_jira_from_metadata(
    content: str,
    patterns: list[str],
    row_pattern: str,
    search_depth: int,
) -> list[str]:
    """
    Extract primary JIRA issues from metadata table.

    Looks for a markdown table with a row matching the specified pattern, e.g.:
    | **Feature / Initiative** | [PROJECT-1586](url) |

    Args:
        content: Text content to search (PR body or file content)
        patterns: List of regex patterns to extract issue keys (e.g., [r"(PROJECT-\\d+)"])
        row_pattern: Regex pattern to identify the metadata row (case-insensitive)
        search_depth: Number of lines to search from the top (-1 for unlimited)

    Returns:
        List of JIRA issue keys found in metadata table, or empty list if none found
    """
    if not content or not patterns:
        return []

    # Limit lines based on search depth
    if search_depth < 0:
        lines = content.split("\n")
    else:
        lines = content.split("\n")[:search_depth]

    # Compile the row pattern (case-insensitive)
    try:
        metadata_row_regex = re.compile(row_pattern, re.IGNORECASE)
    except re.error as e:
        logging.warning(f"Invalid metadata row pattern '{row_pattern}': {e}")
        return []

    for line in lines:
        # Check if this line contains the metadata row marker
        if metadata_row_regex.search(line):
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

    logging.debug("No primary JIRA issues found in metadata table")
    return []


def extract_primary_jira_from_file_contents(
    file_contents: list[str],
    patterns: list[str],
    row_pattern: str,
    search_depth: int,
) -> list[str]:
    """
    Extract primary JIRA issues from metadata tables in file contents.

    Searches each file for a markdown table with a row matching the specified pattern.
    Returns the first match found across all files.

    Args:
        file_contents: List of file content strings to search
        patterns: List of regex patterns to extract issue keys (e.g., [r"(PROJECT-\\d+)"])
        row_pattern: Regex pattern to identify the metadata row (case-insensitive)
        search_depth: Number of lines to search from the top of each file (-1 for unlimited)

    Returns:
        List of JIRA issue keys found in metadata table, or empty list if none found
    """
    if not file_contents or not patterns:
        return []

    for content in file_contents:
        if not content:
            continue

        # Check this file's content for metadata table
        primary_issues = extract_primary_jira_from_metadata(
            content, patterns, row_pattern, search_depth
        )
        if primary_issues:
            logging.info(
                f"Found primary JIRA issues in file metadata table: {', '.join(primary_issues)}"
            )
            return primary_issues

    logging.debug("No primary JIRA issues found in file metadata tables")
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
        patterns: List of regex patterns to extract issue keys (e.g., [r"(PROJECT-\\d+)", r"(OTHERJIRA-\\d+)"])

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
    pr_body: str | None,
    metadata_row_pattern: str,
    metadata_search_depth: int,
) -> list[str]:
    """
    Extract JIRA issue keys from a PR without fetching metadata.

    Extraction strategy (priority order):
    1. First checks PR body metadata table (searching N lines for metadata row pattern)
    2. Then checks file contents for metadata tables (searching N lines of each file)
    3. Falls back to searching full file contents if no metadata tables found

    Args:
        file_contents: List of file content strings to search for JIRA issues
        issue_patterns: List of regex patterns to extract issue keys
        pr_body: PR body/description text (optional)
        metadata_row_pattern: Regex pattern to identify metadata row (case-insensitive)
        metadata_search_depth: Number of lines to search from top (-1 for unlimited)

    Returns:
        List of JIRA issue keys found
    """
    if not issue_patterns:
        return []

    # Priority 1: Try to extract primary issues from PR body metadata table
    issue_keys = []
    if pr_body:
        primary_issues = extract_primary_jira_from_metadata(
            pr_body, issue_patterns, metadata_row_pattern, metadata_search_depth
        )
        if primary_issues:
            issue_keys = primary_issues
            logging.debug(
                f"Found JIRA issues in PR body metadata: {', '.join(primary_issues)}"
            )
            return issue_keys

    # Priority 2: Try to extract primary issues from file contents metadata tables
    if file_contents:
        primary_issues = extract_primary_jira_from_file_contents(
            file_contents, issue_patterns, metadata_row_pattern, metadata_search_depth
        )
        if primary_issues:
            issue_keys = primary_issues
            logging.debug(
                f"Found JIRA issues in file metadata: {', '.join(primary_issues)}"
            )
            return issue_keys

    # Priority 3: Fall back to extracting from full file contents
    issue_keys = extract_jira_from_file_contents(file_contents, issue_patterns)
    if issue_keys:
        logging.debug(f"Found JIRA issues in file contents (no metadata): {issue_keys}")

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
