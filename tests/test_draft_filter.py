import unittest
import logging
from unittest.mock import patch, MagicMock
from gh_pulls_summary import (
    fetch_and_process_pull_requests,
)

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class TestDraftFilter(unittest.TestCase):

    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_only_drafts_filter(self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pull_requests):
        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {"number": 1, "title": "Draft PR", "user": {"login": "johndoe"}, "html_url": "https://github.com/owner/repo/pull/1", "draft": True, "created_at": "2025-05-01T12:00:00Z"},
            {"number": 2, "title": "Regular PR", "user": {"login": "janedoe"}, "html_url": "https://github.com/owner/repo/pull/2", "draft": False, "created_at": "2025-05-02T12:00:00Z"}
        ]

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_user_details.return_value = {"name": "John Doe", "html_url": "https://github.com/johndoe"}
        mock_fetch_reviews.return_value = []

        # Call the function with "only-drafts" filter
        result = fetch_and_process_pull_requests("owner", "repo", draft_filter="only-drafts", file_filters=None)

        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Draft PR")

    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_no_drafts_filter(self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pull_requests):
        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {"number": 1, "title": "Draft PR", "user": {"login": "johndoe"}, "html_url": "https://github.com/owner/repo/pull/1", "draft": True, "created_at": "2025-05-01T12:00:00Z"},
            {"number": 2, "title": "Regular PR", "user": {"login": "janedoe"}, "html_url": "https://github.com/owner/repo/pull/2", "draft": False, "created_at": "2025-05-02T12:00:00Z"}
        ]

        # Mock other dependencies
        mock_fetch_issue_events.return_value = []
        mock_fetch_user_details.return_value = {"name": "Jane Doe", "html_url": "https://github.com/janedoe"}
        mock_fetch_reviews.return_value = []

        # Call the function with "no-drafts" filter
        result = fetch_and_process_pull_requests("owner", "repo", draft_filter="no-drafts", file_filters=None)

        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Regular PR")
    
if __name__ == "__main__":
    unittest.main()