import os
import requests
import json
import sys
import argparse
import logging
from datetime import datetime
from urllib.parse import urljoin

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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)  # Log to stderr
    ]
)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch and summarize GitHub pull requests.")
    parser.add_argument("--owner", required=True, help="The owner of the repository (e.g., 'microsoft').")
    parser.add_argument("--repo", required=True, help="The name of the repository (e.g., 'vscode').")
    parser.add_argument(
        "--draft-filter",
        choices=["only-drafts", "no-drafts"],
        help="Filter pull requests based on draft status. Use 'only-drafts' to include only drafts, or 'no-drafts' to exclude drafts."
    )
    return parser.parse_args()

def github_api_request(endpoint, params=None):
    url = urljoin(GITHUB_API_BASE, endpoint)
    logging.debug(f"Making API request to {url} with params {params}")
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers and response.headers["X-RateLimit-Remaining"] == "0":
        raise Exception("Rate limit exceeded. Consider using a GitHub token to increase the limit.")
    if response.status_code != 200:
        raise Exception(f"GitHub API request failed: {response.status_code} {response.text}")
    return response.json()

def fetch_pull_requests(owner, repo, page):
    endpoint = f"/repos/{owner}/{repo}/pulls"
    params = {"state": "open", "per_page": PAGE_SIZE, "page": page}
    return github_api_request(endpoint, params)

def fetch_issue_events(owner, repo, pr_number, page):
    endpoint = f"/repos/{owner}/{repo}/issues/{pr_number}/events"
    params = {"per_page": PAGE_SIZE, "page": page}
    return github_api_request(endpoint, params)

def fetch_reviews(owner, repo, pr_number):
    endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    params = {"per_page": PAGE_SIZE}
    return github_api_request(endpoint, params)

def fetch_user_details(username):
    endpoint = f"/users/{username}"
    return github_api_request(endpoint)

def main():
    args = parse_arguments()
    owner = args.owner
    repo = args.repo
    draft_filter = args.draft_filter
    logging.info(f"Fetching pull requests for repository {owner}/{repo}")

    page = 1
    pull_requests = []
    print("Loading pull request data...", end="", flush=True)

    while True:
        prs = fetch_pull_requests(owner, repo, page)
        if not prs:
            break

        for pr in prs:
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
            events_page = 1
            while True:
                events = fetch_issue_events(owner, repo, pr_number, events_page)
                if not events:
                    break
                for event in events:
                    if event["event"] == "ready_for_review":
                        event_date = event["created_at"]
                        if not pr_ready_date or event_date > pr_ready_date:
                            pr_ready_date = event_date
                events_page += 1

            if not pr_ready_date:
                pr_ready_date = pr["created_at"]

            pr_ready_date = pr_ready_date.split("T")[0]

            # Fetch author details
            author_details = fetch_user_details(pr_author)
            pr_author_name = author_details.get("name", pr_author)

            # Fetch reviews and approvals
            reviews = fetch_reviews(owner, repo, pr_number)
            pr_reviews_count = len(reviews)
            pr_reviews = len(set(review["user"]["login"] for review in reviews))
            pr_approvals = len(set(review["user"]["login"] for review in reviews if review["state"] == "APPROVED"))

            if pr_reviews_count == PAGE_SIZE:
                logging.warning(f"PR #{pr_number} has {pr_reviews_count} reviews and may have exceeded page limit.")

            pull_requests.append({
                "date": pr_ready_date,
                "title": pr_title,
                "number": pr_number,
                "url": pr_url,
                "author_name": pr_author_name,
                "author_login": pr_author,
                "reviews": pr_reviews,
                "approvals": pr_approvals
            })

        page += 1

    print("")  # New line after loading dots

    # Output as Markdown
    print("| Date 🔽 | Title | Author | Reviews | Approvals |")
    print("| --- | --- | --- | --- | --- |")
    for pr in sorted(pull_requests, key=lambda x: x["date"]):
        print(f"| {pr['date']} | {pr['title']} #[{pr['number']}]({pr['url']}) | [{pr['author_name']}](https://github.com/{pr['author_login']}) | {pr['reviews']} | {pr['approvals']} |")

if __name__ == "__main__":
    main()