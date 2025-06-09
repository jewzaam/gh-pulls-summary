import unittest
import logging
from unittest.mock import patch, MagicMock
from gh_pulls_summary import main, print_timestamp, print_markdown_output
from datetime import datetime, timezone

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class TestMainFunction(unittest.TestCase):
    @patch("builtins.print")
    def test_print_timestamp(self, mock_print):
        """Test the print_timestamp function."""
        mock_time = datetime(2025, 5, 14, 15, 12, tzinfo=timezone.utc)
        print_timestamp(mock_time)
        mock_print.assert_called_once_with("**Generated at 2025-05-14 15:12Z**\n")

    @patch("builtins.print")
    def test_print_markdown_output(self, mock_print):
        """Test the print_markdown_output function."""
        markdown_output = "| Date | Title | Author | Reviews | Approvals |\n| --- | --- | --- | --- | --- |"
        print_markdown_output(markdown_output)
        mock_print.assert_called_once_with(markdown_output)

    @patch("gh_pulls_summary.generate_markdown_output")
    @patch("gh_pulls_summary.print_markdown_output")
    @patch("gh_pulls_summary.print_timestamp")
    @patch("gh_pulls_summary.parse_arguments")
    def test_main(self, mock_parse_arguments, mock_print_timestamp, mock_print_markdown_output, mock_generate_markdown_output):
        """Test the main function."""
        # Mock command-line arguments
        mock_parse_arguments.return_value = MagicMock(
            owner="owner",
            repo="repo",
            draft_filter=None,
            debug=False,
            pr_number=None,
        )

        # Mock generate_markdown_output
        mock_generate_markdown_output.return_value = (
            "| Date | Title | Author | Reviews | Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 3 | 2 |"
        )

        # Call the main function
        main()

        # Verify that generate_markdown_output was called with the correct arguments
        mock_generate_markdown_output.assert_called_once_with(mock_parse_arguments.return_value)

        # Verify that print_timestamp and print_markdown_output were called
        mock_print_timestamp.assert_called_once()
        mock_print_markdown_output.assert_called_once_with(mock_generate_markdown_output.return_value)

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

        # Call main and check return value
        from gh_pulls_summary import main
        result = main()
        self.assertEqual(result, 1)

if __name__ == "__main__":
    unittest.main()