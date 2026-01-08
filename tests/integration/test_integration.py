#!/usr/bin/env python3

import logging
import os
import time
import unittest
from typing import Any, cast

from gh_pulls_summary.main import (
    fetch_and_process_pull_requests,
    fetch_issue_events,
    fetch_pr_files,
    fetch_pull_requests,
    fetch_reviews,
    fetch_single_pull_request,
    fetch_user_details,
    generate_markdown_output,
    get_repo_and_owner_from_git,
)

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class IntegrationTestBase(unittest.TestCase):
    """Base class for integration tests with rate limiting helpers."""

    # Test repository (the actual gh-pulls-summary repo)
    TEST_OWNER = "jewzaam"
    TEST_REPO = "gh-pulls-summary"

    # Known PRs for testing (these should exist in the repo)
    KNOWN_PR_NUMBERS = [1, 2, 3]  # Based on current repo state

    @classmethod
    def setUpClass(cls):
        """Set up class-level test fixtures."""
        # Warn if using GitHub token in integration tests
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            logging.warning(
                "GITHUB_TOKEN is set - integration tests will use authenticated requests"
            )
        else:
            logging.info(
                "Running integration tests without GitHub token (rate limited)"
            )

        # Check rate limit before starting
        cls._check_rate_limit()

        # Small delay to avoid immediate rate limiting
        time.sleep(0.5)

    def setUp(self):
        """Set up individual test fixtures."""
        # Add small delay between tests to avoid rate limiting
        time.sleep(0.3)

    @classmethod
    def _check_rate_limit(cls):
        """Check current rate limit status."""
        try:
            import requests

            github_token = os.getenv("GITHUB_TOKEN")
            response = requests.get(
                "https://api.github.com/rate_limit",
                headers={"Authorization": f"Bearer {github_token}"}
                if github_token
                else {},
            )
            if response.status_code == 200:
                data = response.json()
                remaining = data.get("rate", {}).get("remaining", 0)
                if remaining < 10:
                    raise unittest.SkipTest(
                        f"Rate limit too low ({remaining} remaining). Please wait or use a GitHub token."
                    )
                logging.info(f"Rate limit remaining: {remaining}")
            else:
                logging.warning(f"Could not check rate limit: {response.status_code}")
        except Exception as e:
            logging.warning(f"Could not check rate limit: {e}")

    def _safe_api_call(self, func, *args, **kwargs):
        """Safely make an API call with rate limit handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "Rate limit exceeded" in str(e):
                self.skipTest(f"Rate limit exceeded during {func.__name__}")
            raise

    def assertPullRequestDataValid(self, pr_data):
        """Assert that pull request data has expected structure."""
        required_fields = [
            "date",
            "title",
            "number",
            "url",
            "author_name",
            "author_url",
            "reviews",
            "approvals",
            "changes",
        ]

        for field in required_fields:
            self.assertIn(field, pr_data, f"Missing field: {field}")

        # Validate data types
        self.assertIsInstance(pr_data["number"], int)
        self.assertIsInstance(pr_data["reviews"], int)
        self.assertIsInstance(pr_data["approvals"], int)
        self.assertIsInstance(pr_data["changes"], int)

        # Validate URLs
        self.assertTrue(pr_data["url"].startswith("https://github.com/"))
        self.assertTrue(pr_data["author_url"].startswith("https://github.com/"))

        # Validate date format (YYYY-MM-DD)
        self.assertRegex(pr_data["date"], r"^\d{4}-\d{2}-\d{2}$")


class TestGitHubApiIntegration(IntegrationTestBase):
    """Integration tests for GitHub API functions."""

    def test_fetch_pull_requests_real_repo(self):
        """Test fetching pull requests from real repository."""
        prs = self._safe_api_call(fetch_pull_requests, self.TEST_OWNER, self.TEST_REPO)

        self.assertIsNotNone(prs)
        self.assertIsInstance(prs, list)
        if prs:  # Check if list is not empty
            self.assertGreater(len(prs), 0, "Expected at least one PR in test repo")

            # Validate structure of first PR
            pr_list = cast(list[dict[str, Any]], prs)
            pr = pr_list[0]
            self.assertIn("number", pr)
            self.assertIn("title", pr)
            self.assertIn("user", pr)
            self.assertIn("html_url", pr)
            self.assertIn("draft", pr)
            self.assertIn("created_at", pr)
        else:
            self.skipTest("No pull requests found in test repository")

    def test_fetch_single_pull_request_real_repo(self):
        """Test fetching a single pull request from real repository."""
        pr_number = self.KNOWN_PR_NUMBERS[0]
        pr = fetch_single_pull_request(
            self.TEST_OWNER,
            self.TEST_REPO,
            pr_number,
            github_token=os.getenv("GITHUB_TOKEN"),
        )

        self.assertIsNotNone(pr)
        self.assertIsInstance(pr, dict)
        pr = cast(dict[str, Any], pr)
        self.assertEqual(pr["number"], pr_number)
        self.assertIn("title", pr)
        self.assertIn("user", pr)
        self.assertIn("html_url", pr)

    def test_fetch_pr_files_real_repo(self):
        """Test fetching files for a pull request from real repository."""
        pr_number = self.KNOWN_PR_NUMBERS[0]
        files = fetch_pr_files(
            self.TEST_OWNER,
            self.TEST_REPO,
            pr_number,
            github_token=os.getenv("GITHUB_TOKEN"),
        )

        self.assertIsNotNone(files)
        self.assertIsInstance(files, list)

        if files:  # Only validate if files exist
            file_obj = files[0]
            self.assertIn("filename", file_obj)
            self.assertIn("status", file_obj)

    def test_fetch_user_details_real_user(self):
        """Test fetching user details for a real GitHub user."""
        # Use the repo owner as a known user
        user_details = fetch_user_details(
            self.TEST_OWNER, github_token=os.getenv("GITHUB_TOKEN")
        )

        self.assertIsNotNone(user_details)
        self.assertIsInstance(user_details, dict)
        self.assertIn("login", user_details)
        self.assertIn("html_url", user_details)
        self.assertEqual(user_details["login"], self.TEST_OWNER)

    def test_fetch_issue_events_real_repo(self):
        """Test fetching issue events for a real pull request."""
        pr_number = self.KNOWN_PR_NUMBERS[0]
        events = fetch_issue_events(
            self.TEST_OWNER,
            self.TEST_REPO,
            pr_number,
            github_token=os.getenv("GITHUB_TOKEN"),
        )

        self.assertIsNotNone(events)
        self.assertIsInstance(events, list)

        # Events might be empty, but if they exist, validate structure
        if events:
            event = events[0]
            self.assertIn("event", event)
            self.assertIn("created_at", event)

    def test_fetch_reviews_real_repo(self):
        """Test fetching reviews for a real pull request."""
        pr_number = self.KNOWN_PR_NUMBERS[0]
        reviews = fetch_reviews(
            self.TEST_OWNER,
            self.TEST_REPO,
            pr_number,
            github_token=os.getenv("GITHUB_TOKEN"),
        )

        self.assertIsNotNone(reviews)
        self.assertIsInstance(reviews, list)

        # Reviews might be empty, but if they exist, validate structure
        if reviews:
            review = reviews[0]
            self.assertIn("state", review)
            self.assertIn("user", review)


class TestEndToEndIntegration(IntegrationTestBase):
    """End-to-end integration tests for complete workflows."""

    def test_fetch_and_process_pull_requests_real_repo(self):
        """Test complete pull request processing workflow."""
        prs, _ = fetch_and_process_pull_requests(
            self.TEST_OWNER, self.TEST_REPO, github_token=os.getenv("GITHUB_TOKEN")
        )

        self.assertIsNotNone(prs)
        self.assertIsInstance(prs, list)
        self.assertGreater(len(prs), 0, "Expected at least one processed PR")

        # Validate each PR's data structure
        for pr in prs:
            self.assertPullRequestDataValid(pr)

    def test_single_pr_processing_real_repo(self):
        """Test processing a single pull request."""
        pr_number = self.KNOWN_PR_NUMBERS[0]
        prs, _ = fetch_and_process_pull_requests(
            self.TEST_OWNER, self.TEST_REPO, pr_number=pr_number
        )

        self.assertIsNotNone(prs)
        self.assertIsInstance(prs, list)
        self.assertEqual(len(prs), 1)

        pr = prs[0]
        self.assertPullRequestDataValid(pr)
        self.assertEqual(pr["number"], pr_number)

    def test_draft_filter_real_repo(self):
        """Test draft filtering with real repository."""
        # Test no-drafts filter
        prs_no_drafts, _ = fetch_and_process_pull_requests(
            self.TEST_OWNER, self.TEST_REPO, draft_filter="no-drafts"
        )

        # Test only-drafts filter
        prs_only_drafts, _ = fetch_and_process_pull_requests(
            self.TEST_OWNER, self.TEST_REPO, draft_filter="only-drafts"
        )

        # Both should be lists
        self.assertIsInstance(prs_no_drafts, list)
        self.assertIsInstance(prs_only_drafts, list)

        # Validate data structure for any results
        for pr in prs_no_drafts:
            self.assertPullRequestDataValid(pr)

        for pr in prs_only_drafts:
            self.assertPullRequestDataValid(pr)

    def test_generate_markdown_output_real_repo(self):
        """Test markdown generation with real repository data."""

        class Args:
            owner = self.TEST_OWNER
            repo = self.TEST_REPO
            draft_filter = None
            file_include = None
            file_exclude = None
            pr_number = None
            url_from_pr_content = None
            column_title = None
            sort_column = "date"
            include_rank = False
            jira_issue_pattern = r"(ANSTRAT-\d+)"
            jira_include = None
            jira_url = None
            jira_token = None
            jira_rank_field = None
            github_token = os.getenv("GITHUB_TOKEN")

        args = Args()
        markdown_output = generate_markdown_output(args)

        self.assertIsInstance(markdown_output, str)
        self.assertIn("Date 🔽", markdown_output)  # Sort indicator
        self.assertIn("Title", markdown_output)
        self.assertIn("Author", markdown_output)
        self.assertIn("Change Requested", markdown_output)
        self.assertIn("Approvals", markdown_output)

        # Should contain markdown table formatting
        self.assertIn("| --- |", markdown_output)

        # Should contain at least one PR row
        lines = markdown_output.split("\n")
        data_rows = [
            line
            for line in lines
            if line.startswith("|") and "---" not in line and "Date" not in line
        ]
        self.assertGreater(len(data_rows), 0, "Expected at least one PR data row")


class TestRealWorldScenarios(IntegrationTestBase):
    """Integration tests for real-world usage scenarios."""

    def test_git_metadata_detection(self):
        """Test that git metadata detection works in real repository."""
        owner, repo = get_repo_and_owner_from_git()

        # Should detect current repo metadata
        self.assertIsNotNone(owner)
        self.assertIsNotNone(repo)
        self.assertIsInstance(owner, str)
        self.assertIsInstance(repo, str)

        # Should match expected values for this repo
        self.assertEqual(owner, self.TEST_OWNER)
        self.assertEqual(repo, self.TEST_REPO)

    def test_url_extraction_real_repo(self):
        """Test URL extraction from real PR content."""
        # Use PR #3 which was created specifically for URL testing
        pr_number = 3
        url_pattern = r"https://[^\s]+"

        prs, _ = fetch_and_process_pull_requests(
            self.TEST_OWNER,
            self.TEST_REPO,
            pr_number=pr_number,
            url_from_pr_content=url_pattern,
        )

        self.assertIsNotNone(prs)
        self.assertIsInstance(prs, list)
        self.assertEqual(len(prs), 1)

        pr = prs[0]
        self.assertPullRequestDataValid(pr)
        self.assertIn("pr_body_urls_dict", pr)
        self.assertIsInstance(pr["pr_body_urls_dict"], dict)

    def test_sort_functionality_real_repo(self):
        """Test different sort options with real data."""
        sort_columns = ["date", "title", "author", "approvals"]

        for sort_col in sort_columns:

            class Args:
                owner = self.TEST_OWNER
                repo = self.TEST_REPO
                draft_filter = None
                file_include = None
                file_exclude = None
                pr_number = None
                url_from_pr_content = None
                column_title = None
                sort_column = sort_col
                include_rank = False
                jira_issue_pattern = r"(ANSTRAT-\d+)"
                jira_include = None
                jira_url = None
                jira_token = None
                jira_rank_field = None
                github_token = os.getenv("GITHUB_TOKEN")

            args = Args()
            markdown_output = generate_markdown_output(args)

            # Should contain sort indicator
            self.assertIn("🔽", markdown_output)

            # Should be valid markdown
            self.assertIn("| --- |", markdown_output)


class TestRateLimitingAndErrors(IntegrationTestBase):
    """Integration tests for error handling and rate limiting."""

    def test_nonexistent_repo_error_handling(self):
        """Test error handling with non-existent repository."""
        with self.assertRaises(Exception):
            fetch_pull_requests(
                "nonexistent",
                "nonexistent-repo",
                github_token=os.getenv("GITHUB_TOKEN"),
            )

    def test_nonexistent_pr_error_handling(self):
        """Test error handling with non-existent PR number."""
        # Use a very high PR number that shouldn't exist
        with self.assertRaises(Exception):
            fetch_single_pull_request(
                self.TEST_OWNER,
                self.TEST_REPO,
                99999,
                github_token=os.getenv("GITHUB_TOKEN"),
            )

    def test_rate_limit_awareness(self):
        """Test that we can make multiple requests without hitting rate limits."""
        # Make several requests in sequence
        for i in range(3):
            prs = fetch_pull_requests(
                self.TEST_OWNER, self.TEST_REPO, github_token=os.getenv("GITHUB_TOKEN")
            )
            self.assertIsNotNone(prs)
            time.sleep(0.1)  # Small delay between requests


if __name__ == "__main__":
    # Only run integration tests if explicitly requested
    if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() in ("1", "true", "yes"):
        unittest.main(verbosity=2)
    else:
        print("Integration tests skipped. Set RUN_INTEGRATION_TESTS=1 to run them.")
        print(
            "Example: RUN_INTEGRATION_TESTS=1 python -m unittest discover -s integration_tests -v"
        )
