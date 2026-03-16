"""
Markdown output generation functions.
"""

import logging

from gh_pulls_summary.common import ValidationError


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
