#!/usr/bin/env python3

import logging
import os
import unittest

from gh_pulls_summary.main import (
    fetch_and_process_pull_requests,
    generate_markdown_output,
    get_repo_and_owner_from_git,
)

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class SimpleIntegrationTests(unittest.TestCase):
    """Simplified integration tests focusing on core functionality."""

    # Test repository (the actual gh-pulls-summary repo)
    TEST_OWNER = "jewzaam"
    TEST_REPO = "gh-pulls-summary"

    @classmethod
    def setUpClass(cls):
        """Set up class-level test fixtures."""
        # Check if rate limits are sufficient
        cls._check_rate_limit()

    @classmethod
    def _check_rate_limit(cls):
        """Check current rate limit status."""
        try:
            import requests

            headers = {}
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                headers["Authorization"] = f"Bearer {github_token}"

            response = requests.get(
                "https://api.github.com/rate_limit", headers=headers, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                remaining = data.get("rate", {}).get("remaining", 0)
                if remaining < 5:
                    raise unittest.SkipTest(
                        f"Rate limit too low ({remaining} remaining). Please wait or use a GitHub token."
                    )
                print(f"Rate limit remaining: {remaining}")
            else:
                print(f"Could not check rate limit: {response.status_code}")
        except Exception as e:
            print(f"Could not check rate limit: {e}")

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

    def test_end_to_end_with_single_pr(self):
        """Test complete end-to-end workflow with a single PR."""
        # Use PR #1 which should always exist
        pr_number = 1

        try:
            prs, _ = fetch_and_process_pull_requests(
                self.TEST_OWNER,
                self.TEST_REPO,
                pr_number=pr_number,
                github_token=os.getenv("GITHUB_TOKEN"),
            )

            # Validate results
            self.assertIsNotNone(prs)
            self.assertIsInstance(prs, list)
            self.assertEqual(len(prs), 1)

            pr = prs[0]
            self._validate_pr_structure(pr)
            self.assertEqual(pr["number"], pr_number)

            print(f"✓ Successfully processed PR #{pr_number}: {pr['title']}")

        except Exception as e:
            if "Rate limit exceeded" in str(e):
                self.skipTest(
                    "Rate limit exceeded - this is expected for unauthenticated requests"
                )
            else:
                raise

    def test_markdown_generation_with_single_pr(self):
        """Test markdown generation with a single PR to minimize API calls."""

        class Args:
            owner = self.TEST_OWNER
            repo = self.TEST_REPO
            draft_filter = None
            file_include = None
            file_exclude = None
            pr_number = 1  # Use specific PR to minimize API calls
            url_from_pr_content = None
            column_title = None
            sort_column = "date"
            include_rank = False
            jira_issue_pattern = r"(ANSTRAT-\d+)"
            jira_include = None
            jira_url = None
            jira_token = None
            jira_rank_field = None
            review_requested_for = None
            github_token = os.getenv("GITHUB_TOKEN")

        try:
            args = Args()
            markdown_output = generate_markdown_output(args)

            # Validate markdown structure
            self.assertIsInstance(markdown_output, str)
            self.assertIn("Date 🔽", markdown_output)
            self.assertIn("Title", markdown_output)
            self.assertIn("Author", markdown_output)
            self.assertIn("| --- |", markdown_output)

            # Should contain the PR data
            self.assertIn("a non-draft pull request", markdown_output)

            print("✓ Successfully generated markdown output")

        except Exception as e:
            if "Rate limit exceeded" in str(e):
                self.skipTest(
                    "Rate limit exceeded - this is expected for unauthenticated requests"
                )
            else:
                raise

    def test_draft_filter_functionality(self):
        """Test draft filtering functionality."""

        try:
            # Test filtering for non-draft PRs
            prs_no_drafts, _ = fetch_and_process_pull_requests(
                self.TEST_OWNER,
                self.TEST_REPO,
                draft_filter="no-drafts",
                github_token=os.getenv("GITHUB_TOKEN"),
            )

            self.assertIsNotNone(prs_no_drafts)
            self.assertIsInstance(prs_no_drafts, list)

            # Validate any results
            for pr in prs_no_drafts:
                self._validate_pr_structure(pr)

            print(f"✓ Successfully filtered non-draft PRs: {len(prs_no_drafts)} found")

        except Exception as e:
            if "Rate limit exceeded" in str(e):
                self.skipTest(
                    "Rate limit exceeded - this is expected for unauthenticated requests"
                )
            else:
                raise

    def _validate_pr_structure(self, pr):
        """Validate that PR data has expected structure."""
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
            self.assertIn(field, pr, f"Missing field: {field}")

        # Validate data types
        self.assertIsInstance(pr["number"], int)
        self.assertIsInstance(pr["reviews"], int)
        self.assertIsInstance(pr["approvals"], int)
        self.assertIsInstance(pr["changes"], int)

        # Validate URLs
        self.assertTrue(pr["url"].startswith("https://github.com/"))
        self.assertTrue(pr["author_url"].startswith("https://github.com/"))

        # Validate date format (YYYY-MM-DD)

        self.assertRegex(pr["date"], r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    # Only run integration tests if explicitly requested
    if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() in ("1", "true", "yes"):
        unittest.main(verbosity=2)
    else:
        print("Integration tests skipped. Set RUN_INTEGRATION_TESTS=1 to run them.")
        print(
            "Example: RUN_INTEGRATION_TESTS=1 python -m unittest discover -s integration_tests -p test_integration_simple.py -v"
        )
