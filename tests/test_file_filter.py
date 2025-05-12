import unittest
import re
from unittest.mock import patch, MagicMock
from gh_pulls_summary import fetch_and_process_pull_requests

class TestFetchAndProcessPullRequests(unittest.TestCase):
    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_pr_files")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_fetch_and_process_pull_requests_with_file_filters(
        self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pr_files, mock_fetch_pull_requests
    ):
        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {"number": 1, "title": "Fix bug", "user": {"login": "user1"}, "html_url": "url1", "draft": False, "created_at": "2025-05-01T12:00:00Z"},
            {"number": 2, "title": "Add feature", "user": {"login": "user2"}, "html_url": "url2", "draft": False, "created_at": "2025-05-02T12:00:00Z"},
        ]

        # Mock files changed in PRs
        mock_fetch_pr_files.side_effect = [
            [{"filename": "src/file1.py"}],  # PR 1
            [{"filename": "docs/readme.md"}],  # PR 2
        ]

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []

        # Mock other API calls
        mock_fetch_user_details.return_value = {"name": "User Name", "html_url": "user_url"}

        # Call the function with file filters
        file_filters = [re.compile(r".*\.py$")]
        pull_requests = fetch_and_process_pull_requests("owner", "repo", None, file_filters)

        # Verify results
        self.assertEqual(len(pull_requests), 1)
        self.assertEqual(pull_requests[0]["number"], 1)

        # Verify fetch_pr_files was called
        mock_fetch_pr_files.assert_called()

    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_pr_files")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_fetch_and_process_pull_requests_without_file_filters(
        self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pr_files, mock_fetch_pull_requests
    ):
        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {"number": 1, "title": "Fix bug", "user": {"login": "user1"}, "html_url": "url1", "draft": False, "created_at": "2025-05-01T12:00:00Z"},
            {"number": 2, "title": "Add feature", "user": {"login": "user2"}, "html_url": "url2", "draft": False, "created_at": "2025-05-02T12:00:00Z"},
        ]

        # Mock files changed in PRs
        mock_fetch_pr_files.side_effect = [
            [{"filename": "src/file1.py"}],  # PR 1
            [{"filename": "docs/readme.md"}],  # PR 2
        ]

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []

        # Mock other API calls
        mock_fetch_user_details.return_value = {"name": "User Name", "html_url": "user_url"}

        # Call the function with file filters
        pull_requests = fetch_and_process_pull_requests("owner", "repo", None, None)

        # Verify results
        self.assertEqual(len(pull_requests), 2)
        self.assertEqual(pull_requests[0]["number"], 1)

        # Verify fetch_pr_files was not called
        self.assertEqual(mock_fetch_pr_files.call_count, 0)

    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_pr_files")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_fetch_and_process_pull_requests_with_multiple_file_filters(
        self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pr_files, mock_fetch_pull_requests
    ):
        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {"number": 1, "title": "Fix bug", "user": {"login": "user1"}, "html_url": "url1", "draft": False, "created_at": "2025-05-01T12:00:00Z"},
            {"number": 2, "title": "Add feature", "user": {"login": "user2"}, "html_url": "url2", "draft": False, "created_at": "2025-05-02T12:00:00Z"},
        ]

        # Mock files changed in PRs
        mock_fetch_pr_files.side_effect = [
            [{"filename": "src/file1.py"}],  # PR 1
            [{"filename": "docs/readme.md"}],  # PR 2
        ]

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []

        # Mock other API calls
        mock_fetch_user_details.return_value = {"name": "User Name", "html_url": "user_url"}

        # Call the function with file filters
        file_filters = [re.compile(r".*\.py$"), re.compile(r"docs/.*")]
        pull_requests = fetch_and_process_pull_requests("owner", "repo", None, file_filters)

        # Verify results
        self.assertEqual(len(pull_requests), 2)
        self.assertEqual(pull_requests[0]["number"], 1)

        # Verify fetch_pr_files was called
        mock_fetch_pr_files.assert_called()


    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_pr_files")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_fetch_and_process_pull_requests_with_exclusion_file_filters(
        self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pr_files, mock_fetch_pull_requests
    ):
        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {"number": 1, "title": "Fix bug", "user": {"login": "user1"}, "html_url": "url1", "draft": False, "created_at": "2025-05-01T12:00:00Z"},
            {"number": 2, "title": "Add feature", "user": {"login": "user2"}, "html_url": "url2", "draft": False, "created_at": "2025-05-02T12:00:00Z"},
            {"number": 3, "title": "Update feature", "user": {"login": "user2"}, "html_url": "url2", "draft": False, "created_at": "2025-05-02T12:00:00Z"},
        ]

        # Mock files changed in PRs
        mock_fetch_pr_files.side_effect = [
            [{"filename": "src/file1.py"}],  # PR 1
            [{"filename": "docs/readme.md"}],  # PR 2
            [{"filename": "bob/readme.md"}],  # PR 2
            [{"filename": "src/file1.py"}],  # PR 3
        ]

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []

        # Mock other API calls
        mock_fetch_user_details.return_value = {"name": "User Name", "html_url": "user_url"}

        # Call the function with file filters
        file_filters = [re.compile(r"^(?!.*(docs|bob)).*")]
        pull_requests = fetch_and_process_pull_requests("owner", "repo", None, file_filters)

        # Verify results
        self.assertEqual(len(pull_requests), 2)
        self.assertEqual(pull_requests[0]["number"], 1)
        self.assertEqual(pull_requests[1]["number"], 3)

        # Verify fetch_pr_files was called
        mock_fetch_pr_files.assert_called()


if __name__ == "__main__":
    unittest.main()