import unittest
import logging
from unittest.mock import patch, MagicMock
from gh_pulls_summary import main, generate_timestamp, generate_markdown_output, MissingRepoError
from datetime import datetime, timezone

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class TestMainFunction(unittest.TestCase):
    def test_generate_timestamp(self):
        """Test the generate_timestamp function."""
        mock_time = datetime(2025, 5, 14, 15, 12, tzinfo=timezone.utc)
        result = generate_timestamp(mock_time)
        self.assertEqual(result, "**Generated at 2025-05-14 15:12Z**\n")

    def test_generate_markdown_output(self):
        """Test the generate_markdown_output function."""
        class Args:
            owner = "owner"
            repo = "repo"
            draft_filter = None
            debug = False
            pr_number = None
            file_include = None
            file_exclude = None
            url_from_pr_content = None
        args = Args()
        # Patch fetch_and_process_pull_requests to avoid network
        with patch("gh_pulls_summary.fetch_and_process_pull_requests") as mock_fetch:
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
            markdown_output = generate_markdown_output(args)
        expected_output = (
            "| Date 🔽 | Title | Author | Change Requested | Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 2 |"
        )
        self.assertEqual(markdown_output, expected_output)

    @patch("gh_pulls_summary.generate_markdown_output")
    @patch("gh_pulls_summary.generate_timestamp")
    @patch("gh_pulls_summary.parse_arguments")
    def test_main(self, mock_parse_arguments, mock_generate_timestamp, mock_generate_markdown_output):
        """Test the main function."""
        # Mock command-line arguments
        mock_parse_arguments.return_value = MagicMock(
            owner="owner",
            repo="repo",
            draft_filter=None,
            debug=False,
            pr_number=None,
            file_include=None,
            file_exclude=None,
            url_from_pr_content=None,
            output_markdown=None
        )
        mock_generate_timestamp.return_value = "**Generated at 2025-05-14 15:12Z**\n"
        mock_generate_markdown_output.return_value = (
            "| Date | Title | Author | Reviews | Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 3 | 2 |"
        )
        # Patch print to capture output
        with patch("builtins.print") as mock_print:
            main()
        mock_generate_markdown_output.assert_called_once_with(mock_parse_arguments.return_value)
        mock_generate_timestamp.assert_called_once()
        mock_print.assert_called_once_with(
            f"**Generated at 2025-05-14 15:12Z**\n\n| Date | Title | Author | Reviews | Approvals |\n| --- | --- | --- | --- | --- |\n| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 3 | 2 |\n"
        )

    @patch("gh_pulls_summary.get_repo_and_owner_from_git", return_value=(None, None))
    @patch("gh_pulls_summary.parse_arguments")
    def test_main_failure_without_owner_and_repo(self, mock_parse_arguments, mock_get_repo_and_owner_from_git):
        # Mock command-line arguments with no owner or repo
        mock_parse_arguments.return_value = MagicMock(
            owner=None,
            repo=None,
            draft_filter=None,
            debug=False,
            pr_number=None,
        )

        # Call main and check for MissingRepoError
        with self.assertRaises(MissingRepoError):
            main()

if __name__ == "__main__":
    unittest.main()