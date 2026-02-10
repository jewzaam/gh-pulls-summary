import unittest
from unittest.mock import patch

from gh_pulls_summary.main import fetch_and_process_pull_requests


class TestReviewRequestedFilter(unittest.TestCase):
    @patch("gh_pulls_summary.main.fetch_pull_requests")
    @patch("gh_pulls_summary.main.fetch_issue_events")
    @patch("gh_pulls_summary.main.fetch_user_details")
    @patch("gh_pulls_summary.main.fetch_reviews")
    def test_review_requested_for_filter_match(
        self,
        mock_fetch_reviews,
        mock_fetch_user_details,
        mock_fetch_issue_events,
        mock_fetch_pull_requests,
    ):
        """Test filtering PRs where review is requested for a specific user."""
        # Mock pull requests - fetch_pull_requests now returns full PR objects
        # (fetches from /pulls and filters using Search API intersection)
        mock_fetch_pull_requests.return_value = [
            {
                "number": 1,
                "title": "Fix bug",
                "user": {"login": "author1"},
                "html_url": "https://github.com/owner/repo/pull/1",
                "draft": False,
                "created_at": "2025-05-01T12:00:00Z",
                "body": "Fix description",
                "head": {"sha": "abc123"},  # Full PR object has head.sha
            },
        ]

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []
        mock_fetch_user_details.return_value = {
            "name": "User Name",
            "html_url": "user_url",
        }

        # Call the function with review_requested_for filter
        pull_requests, _ = fetch_and_process_pull_requests(
            "owner", "repo", review_requested_for="targetuser"
        )

        # Verify results - only PR 1 should be included
        self.assertEqual(len(pull_requests), 1)
        self.assertEqual(pull_requests[0]["number"], 1)
        self.assertEqual(pull_requests[0]["title"], "Fix bug")

        # Verify fetch_pull_requests was called with review_requested_for parameter
        mock_fetch_pull_requests.assert_called_once_with(
            "owner", "repo", None, "targetuser"
        )

    @patch("gh_pulls_summary.main.fetch_pull_requests")
    @patch("gh_pulls_summary.main.fetch_issue_events")
    @patch("gh_pulls_summary.main.fetch_user_details")
    @patch("gh_pulls_summary.main.fetch_reviews")
    def test_review_requested_for_filter_no_match(
        self,
        mock_fetch_reviews,
        mock_fetch_user_details,
        mock_fetch_issue_events,
        mock_fetch_pull_requests,
    ):
        """Test filtering when no PRs match the requested reviewer (Search API returns empty)."""
        # Mock pull requests - Search API returns empty when no matches
        mock_fetch_pull_requests.return_value = []

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []
        mock_fetch_user_details.return_value = {
            "name": "User Name",
            "html_url": "user_url",
        }

        # Call the function with review_requested_for filter
        pull_requests, _ = fetch_and_process_pull_requests(
            "owner", "repo", review_requested_for="targetuser"
        )

        # Verify results - no PRs should be included
        self.assertEqual(len(pull_requests), 0)

    @patch("gh_pulls_summary.main.fetch_pull_requests")
    @patch("gh_pulls_summary.main.fetch_issue_events")
    @patch("gh_pulls_summary.main.fetch_user_details")
    @patch("gh_pulls_summary.main.fetch_reviews")
    def test_no_review_requested_filter(
        self,
        mock_fetch_reviews,
        mock_fetch_user_details,
        mock_fetch_issue_events,
        mock_fetch_pull_requests,
    ):
        """Test that all PRs are included when no review_requested_for filter is specified."""
        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {
                "number": 1,
                "title": "Fix bug",
                "user": {"login": "author1"},
                "html_url": "url1",
                "draft": False,
                "created_at": "2025-05-01T12:00:00Z",
            },
            {
                "number": 2,
                "title": "Add feature",
                "user": {"login": "author2"},
                "html_url": "url2",
                "draft": False,
                "created_at": "2025-05-02T12:00:00Z",
            },
        ]

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_reviews.return_value = []
        mock_fetch_user_details.return_value = {
            "name": "User Name",
            "html_url": "user_url",
        }

        # Call the function without review_requested_for filter
        pull_requests, _ = fetch_and_process_pull_requests("owner", "repo")

        # Verify results - all PRs should be included
        self.assertEqual(len(pull_requests), 2)


if __name__ == "__main__":
    unittest.main()
