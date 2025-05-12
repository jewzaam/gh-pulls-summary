import unittest
import logging
from unittest.mock import patch, MagicMock
from gh_pulls_summary import main

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class TestMainFunction(unittest.TestCase):

    @patch("gh_pulls_summary.fetch_and_process_pull_requests")
    @patch("gh_pulls_summary.generate_markdown_output")
    @patch("builtins.print")
    @patch("gh_pulls_summary.parse_arguments")
    def test_main(self, mock_parse_arguments, mock_print, mock_generate_markdown_output, mock_fetch_and_process_pull_requests):
        # Mock command-line arguments
        mock_parse_arguments.return_value = MagicMock(
            owner="owner",
            repo="repo",
            draft_filter=None,
            debug=False
        )

        # Mock fetch_and_process_pull_requests
        mock_fetch_and_process_pull_requests.return_value = [
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

        # Mock generate_markdown_output
        mock_generate_markdown_output.return_value = (
            "| Date 🔽 | Title | Author | Reviews | Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 3 | 2 |"
        )

        # Call the main function
        main()

        # Verify that fetch_and_process_pull_requests was called with the correct arguments
        mock_fetch_and_process_pull_requests.assert_called_once_with("owner", "repo", None, [])

        # Verify that generate_markdown_output was called with the processed pull requests
        mock_generate_markdown_output.assert_called_once_with(mock_fetch_and_process_pull_requests.return_value)

        # Verify that the output was printed
        mock_print.assert_called_once_with(mock_generate_markdown_output.return_value)

if __name__ == "__main__":
    unittest.main()