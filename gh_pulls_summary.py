#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import os
import requests
import sys
import argparse
import logging
import argcomplete

# Configuration
PAGE_SIZE = 100
GITHUB_API_BASE = "https://api.github.com"

# Optional GitHub token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set this in your environment variables

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch and summarize GitHub pull requests.")
    parser.add_argument("--owner", required=True, help="The owner of the repository (e.g., 'microsoft').")
    parser.add_argument("--repo", required=True, help="The name of the repository (e.g., 'vscode').")
    parser.add_argument(
        "--draft-filter",
        choices=["only-drafts", "no-drafts"],
        help="Filter pull requests based on draft status. Use 'only-drafts' to include only drafts, or 'no-drafts' to exclude drafts."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging."
    )

    # Enable tab completion
    argcomplete.autocomplete(parser)
    return parser.parse_args()

def configure_logging(debug):
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
    """
    if params is None:
        params = {}

    all_results = []
    page = 1

    while True:
        if use_paging:
            params["page"] = page
        url = f"{GITHUB_API_BASE}{endpoint}"
        logging.debug(f"Making API request to {url} with params {params}")
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers and response.headers["X-RateLimit-Remaining"] == "0":
            raise Exception("Rate limit exceeded. Consider using a GitHub token to increase the limit.")
        if response.status_code != 200:
            raise Exception(f"GitHub API request failed: {response.status_code} {response.text}")

        results = response.json()

        # Handle cases where the response is a dictionary
        if isinstance(results, dict):
            logging.debug(f"Response is a dictionary: {results}")
            return results

        # Handle cases where the response is a list
        if not results or not use_paging:
            all_results.extend(results)
            break

        all_results.extend(results)
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
    """
    endpoint = f"/users/{username}"
    logging.debug(f"Fetching user details for {username}")
    return github_api_request(endpoint)

def main():
    args = parse_arguments()
    owner = args.owner
    repo = args.repo
    draft_filter = args.draft_filter
    configure_logging(args.debug)
    logging.info(f"Fetching pull requests for repository {owner}/{repo}")

    logging.debug("Starting to fetch pull requests...")
    pull_requests = []
    print("Loading pull request data...", end="", flush=True)

    prs = fetch_pull_requests(owner, repo)
    for pr in prs:
        logging.debug(f"Processing PR #{pr['number']}: {pr['title']}")
        print(".", end="", flush=True)

        # Apply draft filter if specified
        if draft_filter == "no-drafts" and pr.get("draft", False):
            logging.debug(f"Excluding draft PR #{pr['number']}")
            continue
        if draft_filter == "only-drafts" and not pr.get("draft", False):
            logging.debug(f"Excluding non-draft PR #{pr['number']}")
            continue

        pr_number = pr["number"]
        pr_title = pr["title"]
        pr_author = pr["user"]["login"]
        pr_url = pr["html_url"]

        # Determine when the PR was last marked as ready for review
        pr_ready_date = None
        events = fetch_issue_events(owner, repo, pr_number)
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
        pr_author_name = author_details.get("name", pr_author)
        pr_author_url = author_details.get("html_url")

        # Fetch reviews and approvals
        reviews = fetch_reviews(owner, repo, pr_number)
        pr_reviews = len(set(review["user"]["login"] for review in reviews))
        logging.debug(f"PR #{pr_number} has {len(reviews)} reviews, {pr_reviews} unique reviewers")
        pr_approvals = len(set(review["user"]["login"] for review in reviews if review["state"] == "APPROVED"))

        pull_requests.append({
            "date": pr_ready_date,
            "title": pr_title,
            "number": pr_number,
            "url": pr_url,
            "author_name": pr_author_name,
            "author_url": pr_author_url,
            "reviews": pr_reviews,
            "approvals": pr_approvals
        })

    print("")  # New line after loading dots

    # Output as Markdown
    logging.debug("Generating Markdown output for pull requests")
    print("| Date 🔽 | Title | Author | Reviews | Approvals |")
    print("| --- | --- | --- | --- | --- |")
    for pr in sorted(pull_requests, key=lambda x: x["date"]):
        print(f"| {pr['date']} | {pr['title']} #[{pr['number']}]({pr['url']}) | [{pr['author_name']}]({pr['author_url']}) | {pr['reviews']} | {pr['approvals']} |")

if __name__ == "__main__":
    main()