import os
import requests
import json
from datetime import datetime
from urllib.parse import urljoin

# Configuration
DEBUG = False
PAGE_SIZE = 100
SKIP_DRAFT = True
GITHUB_API_BASE = "https://api.github.com"

# Replace with your GitHub token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set this in your environment variables

if not GITHUB_TOKEN:
    raise Exception("GITHUB_TOKEN environment variable is not set.")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def debug(message):
    if DEBUG:
        print(f"DEBUG: {message}")

def get_owner_and_repo():
    # Replace this with your repository details
    # Example: "owner/repo"
    repo_url = os.getenv("REPO_URL")  # Set this in your environment variables
    if not repo_url:
        raise Exception("REPO_URL environment variable is not set.")
    owner, repo = repo_url.split("/")[-2:]
    return owner, repo

def github_api_request(endpoint, params=None):
    url = urljoin(GITHUB_API_BASE, endpoint)
    response = requests.get(url, headers=HEADERS, params=params)
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
    owner, repo = get_owner_and_repo()
    debug(f"OWNER={owner}, REPO={repo}")

    page = 1
    pull_requests = []
    print("Loading pull request data...", end="", flush=True)

    while True:
        prs = fetch_pull_requests(owner, repo, page)
        if not prs:
            break

        for pr in prs:
            print(".", end="", flush=True)

            if SKIP_DRAFT and pr.get("draft", False):
                debug(f"SKIPPING draft PR_NUMBER={pr['number']}")
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
                print(f"WARNING: PR #{pr_number} has {pr_reviews_count} reviews and may have exceeded page limit.")

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