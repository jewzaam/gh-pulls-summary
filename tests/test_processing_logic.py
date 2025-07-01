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
            {"user": {"login": "reviewer1"}, "state": "APPROVED", "submitted_at": "2025-05-02T12:00:00Z"},
            {"user": {"login": "reviewer1"}, "state": "COMMENTED", "submitted_at": "2025-05-03T12:00:00Z"},
            {"user": {"login": "reviewer2"}, "state": "COMMENTED", "submitted_at": "2025-05-02T12:00:00Z"}
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
                "pr_body_urls_dict": {},
                "reviews": 2,
                "approvals": 1,
                "changes": 0,
            }
        ]
        self.assertEqual(result, expected_result)

    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_author_name_fallback_to_username(self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pull_requests):
        """Test that author_name falls back to username if name is not found."""
        mock_fetch_pull_requests.return_value = [
            {
                "number": 2,
                "title": "Fix bug Y",
                "user": {"login": "janedoe"},
                "html_url": "https://github.com/owner/repo/pull/2",
                "draft": False,
                "created_at": "2025-05-05T12:00:00Z"
            }
        ]
        mock_fetch_issue_events.return_value = [
            {"event": "ready_for_review", "created_at": "2025-05-06T12:00:00Z"}
        ]
        # Simulate missing 'name' in user details
        mock_fetch_user_details.return_value = {
            "name": None,
            "html_url": "https://github.com/janedoe"
        }
        mock_fetch_reviews.return_value = []
        result = fetch_and_process_pull_requests("owner", "repo")
        expected_result = [
            {
                "date": "2025-05-06",
                "title": "Fix bug Y",
                "number": 2,
                "url": "https://github.com/owner/repo/pull/2",
                "author_name": "janedoe",  # Fallback to username
                "author_url": "https://github.com/janedoe",
                "pr_body_urls_dict": {},
                "reviews": 0,
                "approvals": 0,
                "changes": 0,
            }
        ]
        self.assertEqual(result, expected_result)

    @patch("gh_pulls_summary.fetch_pr_diff")
    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_pr_body_url_text_extraction(self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pull_requests, mock_fetch_pr_diff):
        # Mock a PR
        mock_fetch_pull_requests.return_value = [
            {
                "number": 1,
                "title": "Test PR",
                "user": {"login": "testuser"},
                "html_url": "https://github.com/owner/repo/pull/1",
                "draft": False,
                "created_at": "2025-06-06T12:00:00Z",
                "body": "This PR references https://example.com/foo/bar123 and should extract the last segment."
            }
        ]
        mock_fetch_issue_events.return_value = []
        mock_fetch_user_details.return_value = {"name": "Test User", "html_url": "https://github.com/testuser"}
        mock_fetch_reviews.return_value = []
        # Mock the diff to contain added lines with multiple URLs
        mock_fetch_pr_diff.return_value = """
+ This is an added line with https://example.com/foo/bar123 and https://example.com/foo/baz456
+ Another added line with https://example.com/foo/qux789
- This is a removed line with https://example.com/foo/shouldnotmatch
"""
        # Regex to match the URL in the added line
        url_regex = r"https://example.com/[^\s]+"
        prs = fetch_and_process_pull_requests(
            owner="owner",
            repo="repo",
            draft_filter=None,
            file_include=None,
            file_exclude=None,
            pr_number=None,
            url_from_pr_content=url_regex
        )
        self.assertEqual(len(prs), 1)
        pr = prs[0]
        self.assertEqual(pr["pr_body_urls_dict"], {
            "bar123": "https://example.com/foo/bar123",
            "baz456": "https://example.com/foo/baz456",
            "qux789": "https://example.com/foo/qux789"
        })

class TestGenerateMarkdownOutput(unittest.TestCase):
    @patch("gh_pulls_summary.fetch_and_process_pull_requests")
    def test_generate_markdown_output(self, mock_fetch_and_process_pull_requests):
        """Test the generate_markdown_output function."""
        # Mock arguments
        args = MagicMock(
            owner="owner",
            repo="repo",
            draft_filter=None,
            file_include=None,
            file_exclude=None,
            pr_number=None,
            url_from_pr_content=None
        )

        # Mock pull request data
        mock_fetch_and_process_pull_requests.return_value = [
            {
                "date": "2025-05-01",
                "title": "Add feature X",
                "number": 123,
                "url": "https://github.com/owner/repo/pull/123",
                "author_name": "John Doe",
                "author_url": "https://github.com/johndoe",
                "reviews": 2,
                "approvals": 2,
                "changes": 1,
            }
        ]

        # Call the function
        markdown_output = generate_markdown_output(args)

        # Verify the output
        expected_output = (
            "| Date 🔽 | Title | Author | Change Requested | Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 2 |"
        )
        self.assertEqual(markdown_output, expected_output)

        # Verify that fetch_and_process_pull_requests was called with the correct arguments
        mock_fetch_and_process_pull_requests.assert_called_once_with(
            "owner", "repo", None, None, None, None, None
        )

    @patch("gh_pulls_summary.fetch_and_process_pull_requests")
    def test_generate_markdown_output_with_custom_titles(self, mock_fetch):
        class Args:
            owner = "owner"
            repo = "repo"
            draft_filter = None
            debug = False
            pr_number = None
            file_include = None
            file_exclude = None
            url_from_pr_content = None
            column_title = ["date=Ready Date", "approvals=Total Approvals"]
        mock_fetch.return_value = [
            {
                "date": "2025-05-01",
                "title": "Add feature X",
                "number": 123,
                "url": "https://github.com/owner/repo/pull/123",
                "author_name": "John Doe",
                "author_url": "https://github.com/johndoe",
                "reviews": 2,
                "approvals": 2,
                "changes": 1,
                "pr_body_urls_dict": {},
            }
        ]
        from gh_pulls_summary import generate_markdown_output
        args = Args()
        markdown_output = generate_markdown_output(args)
        expected_output = (
            "| Ready Date | Title | Author | Change Requested | Total Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 2 |"
        )
        self.assertEqual(markdown_output, expected_output)

if __name__ == "__main__":
    unittest.main()