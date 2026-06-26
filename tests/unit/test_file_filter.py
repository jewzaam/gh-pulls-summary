import re
import unittest
from unittest.mock import patch

from gh_pulls_summary.local_checkout import LocalCheckoutError
from gh_pulls_summary.main import fetch_and_process_pull_requests


class TestFetchAndProcessPullRequests(unittest.TestCase):
    @patch("gh_pulls_summary.main.LocalCheckout")
    @patch("gh_pulls_summary.main.fetch_pull_requests")
    @patch("gh_pulls_summary.main.fetch_pr_files")
    @patch("gh_pulls_summary.main.fetch_issue_events")
    @patch("gh_pulls_summary.main.fetch_user_details")
    @patch("gh_pulls_summary.main.fetch_reviews")
    def test_file_include_filter(
        self,
        mock_fetch_reviews,
        mock_fetch_user_details,
        mock_fetch_issue_events,
        mock_fetch_pr_files,
        mock_fetch_pull_requests,
        mock_checkout_cls,
    ):
        mock_checkout_cls.return_value.ensure_clone.side_effect = LocalCheckoutError(
            "test"
        )

        mock_fetch_pull_requests.return_value = [
            {
                "number": 1,
                "title": "Fix bug",
                "user": {"login": "user1"},
                "html_url": "url1",
                "draft": False,
                "created_at": "2025-05-01T12:00:00Z",
            },
            {
                "number": 2,
                "title": "Add feature",
                "user": {"login": "user2"},
                "html_url": "url2",
                "draft": False,
                "created_at": "2025-05-02T12:00:00Z",
            },
        ]

        mock_fetch_pr_files.side_effect = [
            [{"filename": "src/file1.py"}],
            [{"filename": "docs/readme.md"}],
        ]

        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []
        mock_fetch_user_details.return_value = {
            "name": "User Name",
            "html_url": "user_url",
        }

        file_include = [re.compile(r".*\.py$")]
        pull_requests, _ = fetch_and_process_pull_requests(
            "owner", "repo", file_include=file_include
        )

        self.assertEqual(len(pull_requests), 1)
        self.assertEqual(pull_requests[0].number, 1)

    @patch("gh_pulls_summary.main.LocalCheckout")
    @patch("gh_pulls_summary.main.fetch_pull_requests")
    @patch("gh_pulls_summary.main.fetch_pr_files")
    @patch("gh_pulls_summary.main.fetch_issue_events")
    @patch("gh_pulls_summary.main.fetch_user_details")
    @patch("gh_pulls_summary.main.fetch_reviews")
    def test_file_exclude_filter(
        self,
        mock_fetch_reviews,
        mock_fetch_user_details,
        mock_fetch_issue_events,
        mock_fetch_pr_files,
        mock_fetch_pull_requests,
        mock_checkout_cls,
    ):
        mock_checkout_cls.return_value.ensure_clone.side_effect = LocalCheckoutError(
            "test"
        )

        mock_fetch_pull_requests.return_value = [
            {
                "number": 1,
                "title": "Fix bug",
                "user": {"login": "user1"},
                "html_url": "url1",
                "draft": False,
                "created_at": "2025-05-01T12:00:00Z",
            },
            {
                "number": 2,
                "title": "Add feature",
                "user": {"login": "user2"},
                "html_url": "url2",
                "draft": False,
                "created_at": "2025-05-02T12:00:00Z",
            },
        ]

        mock_fetch_pr_files.side_effect = [
            [{"filename": "src/file1.py"}],
            [{"filename": "docs/readme.md"}],
        ]

        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []
        mock_fetch_user_details.return_value = {
            "name": "User Name",
            "html_url": "user_url",
        }

        file_exclude = [re.compile(r"docs/.*")]
        pull_requests, _ = fetch_and_process_pull_requests(
            "owner", "repo", file_exclude=file_exclude
        )

        self.assertEqual(len(pull_requests), 1)
        self.assertEqual(pull_requests[0].number, 1)

    @patch("gh_pulls_summary.main.LocalCheckout")
    @patch("gh_pulls_summary.main.fetch_pull_requests")
    @patch("gh_pulls_summary.main.fetch_pr_files")
    @patch("gh_pulls_summary.main.fetch_issue_events")
    @patch("gh_pulls_summary.main.fetch_user_details")
    @patch("gh_pulls_summary.main.fetch_reviews")
    def test_file_include_and_exclude_filters(
        self,
        mock_fetch_reviews,
        mock_fetch_user_details,
        mock_fetch_issue_events,
        mock_fetch_pr_files,
        mock_fetch_pull_requests,
        mock_checkout_cls,
    ):
        mock_checkout_cls.return_value.ensure_clone.side_effect = LocalCheckoutError(
            "test"
        )

        mock_fetch_pull_requests.return_value = [
            {
                "number": 1,
                "title": "Fix bug",
                "user": {"login": "user1"},
                "html_url": "url1",
                "draft": False,
                "created_at": "2025-05-01T12:00:00Z",
            },
            {
                "number": 2,
                "title": "Add feature",
                "user": {"login": "user2"},
                "html_url": "url2",
                "draft": False,
                "created_at": "2025-05-02T12:00:00Z",
            },
            {
                "number": 3,
                "title": "Update docs",
                "user": {"login": "user3"},
                "html_url": "url3",
                "draft": False,
                "created_at": "2025-05-03T12:00:00Z",
            },
        ]

        mock_fetch_pr_files.side_effect = [
            [{"filename": "src/file1.py"}],
            [{"filename": "docs/readme.md"}],
            [{"filename": "src/file2.py"}, {"filename": "docs/readme.md"}],
        ]

        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []
        mock_fetch_user_details.return_value = {
            "name": "User Name",
            "html_url": "user_url",
        }

        file_include = [re.compile(r".*\.py$")]
        file_exclude = [re.compile(r"docs/.*")]
        pull_requests, _ = fetch_and_process_pull_requests(
            "owner", "repo", file_include=file_include, file_exclude=file_exclude
        )

        self.assertEqual(len(pull_requests), 1)
        self.assertEqual(
            pull_requests[0].number, 1
        )  # PR 1 is included, PR 2 and PR 3 are excluded


if __name__ == "__main__":
    unittest.main()
