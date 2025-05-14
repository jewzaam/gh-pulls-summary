import unittest
import logging
from unittest.mock import patch, MagicMock
from gh_pulls_summary import fetch_and_process_pull_requests, generate_markdown_output

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class TestProcessingLogic(unittest.TestCase):

    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_fetch_and_process_pull_requests(self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pull_requests):
        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {
                "number": 1,
                "title": "Add feature X",
                "user": {"login": "johndoe"},
                "html_url": "https://github.com/owner/repo/pull/1",
                "draft": False,
                "created_at": "2025-05-01T12:00:00Z"
            },
            {
                "number": 2,
                "title": "Fix bug Y",
                "user": {"login": "janedoe"},
                "html_url": "https://github.com/owner/repo/pull/2",
                "draft": False,
                "created_at": "2025-05-02T12:00:00Z"
            }
        ]

        # Mock issue events
        mock_fetch_issue_events.return_value = [
            {"event": "ready_for_review", "created_at": "2025-05-02T12:00:00Z"}
        ]

        # Mock user details
        mock_fetch_user_details.return_value = {
            "name": "John Doe",
            "html_url": "https://github.com/johndoe"
        }

        # Mock reviews
        mock_fetch_reviews.return_value = [
            {"user": {"login": "reviewer1"}, "state": "APPROVED"},
            {"user": {"login": "reviewer2"}, "state": "COMMENTED"}
        ]

        # Call the function
        result = fetch_and_process_pull_requests("owner", "repo")

        # Verify the result
        expected_result = [
            {
                "date": "2025-05-02",
                "title": "Add feature X",
                "number": 1,
                "url": "https://github.com/owner/repo/pull/1",
                "author_name": "John Doe",
                "author_url": "https://github.com/johndoe",
                "reviews": 2,
                "approvals": 1
            }
        ]
        self.assertEqual(result, expected_result)

    @patch("gh_pulls_summary.fetch_reviews")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_pull_requests")
    def test_generate_markdown_output(self, mock_fetch_reviews, mock_fetch_issue_events, mock_fetch_pull_requests):
        # Mock reviews
        mock_fetch_reviews.return_value = [
            {"user": {"login": "reviewer1"}, "state": "APPROVED"},
            {"user": {"login": "reviewer2"}, "state": "COMMENTED"}
        ]

        # Mock issue events
        mock_fetch_issue_events.return_value = [
            {"event": "ready_for_review", "created_at": "2025-05-02T12:00:00Z"}
        ]

        # Mock pull requests
        mock_fetch_pull_requests.return_value = [
            {
                "number": 1,
                "title": "Add feature X",
                "user": {"login": "johndoe"},
                "html_url": "https://github.com/owner/repo/pull/1",
                "draft": False,
                "created_at": "2025-05-01T12:00:00Z"
            },
            {
                "number": 2,
                "title": "Fix bug Y",
                "user": {"login": "janedoe"},
                "html_url": "https://github.com/owner/repo/pull/2",
                "draft": False,
                "created_at": "2025-05-02T12:00:00Z"
            }
        ]

        pull_requests = [
            {
                "date": "2025-05-02",
                "title": "Fix bug Y",
                "number": 124,
                "url": "https://github.com/owner/repo/pull/124",
                "author_name": "Jane Smith",
                "author_url": "https://github.com/janesmith",
                "reviews": 1,
                "approvals": 1
            },
            {
                "date": "2025-05-01",
                "title": "Add feature X",
                "number": 123,
                "url": "https://github.com/owner/repo/pull/123",
                "author_name": "John Doe",
                "author_url": "https://github.com/johndoe",
                "reviews": 3,
                "approvals": 2
            }
        ]

        expected_output = (
            "| Date 🔽 | Title | Author | Reviews | Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 3 | 2 |\n"
            "| 2025-05-02 | Fix bug Y #[124](https://github.com/owner/repo/pull/124) | [Jane Smith](https://github.com/janesmith) | 1 | 1 |"
        )

        self.assertEqual(generate_markdown_output(pull_requests, sort_by="date"), expected_output)

        pull_requests = fetch_and_process_pull_requests("owner", "repo")

        # Test sorting by title
        sorted_by_title = generate_markdown_output(pull_requests, sort_by="title")
        self.assertIn("Fix bug Y", sorted_by_title)
        self.assertIn("Add feature X", sorted_by_title)

if __name__ == "__main__":
    unittest.main()