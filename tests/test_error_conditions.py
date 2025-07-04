import unittest
import logging
from unittest.mock import patch, MagicMock
from gh_pulls_summary import (
    github_api_request, fetch_and_process_pull_requests, 
    get_repo_and_owner_from_git, generate_markdown_output,
    parse_column_titles, validate_sort_column
)

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


class TestErrorConditions(unittest.TestCase):
    """Test error conditions and edge cases for better code coverage."""

    @patch("gh_pulls_summary.requests.get")
    def test_github_api_request_http_error(self, mock_get):
        """Test github_api_request with HTTP error response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        with self.assertRaises(Exception) as ctx:
            github_api_request("/test/endpoint")
        
        self.assertIn("GitHub API request failed: 404", str(ctx.exception))

    @patch("gh_pulls_summary.requests.get")
    def test_github_api_request_json_error(self, mock_get):
        """Test github_api_request when JSON parsing fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        result = github_api_request("/test/endpoint")
        self.assertIsNone(result)

    @patch("gh_pulls_summary.requests.get")
    def test_github_api_request_network_error(self, mock_get):
        """Test github_api_request with network error."""
        mock_get.side_effect = ConnectionError("Network error")
        
        result = github_api_request("/test/endpoint")
        self.assertIsNone(result)

    def test_validate_sort_column_empty_string(self):
        """Test validate_sort_column with empty string."""
        with self.assertRaises(ValueError) as ctx:
            validate_sort_column("")
        self.assertIn("Invalid sort column", str(ctx.exception))

    def test_validate_sort_column_case_insensitive(self):
        """Test validate_sort_column is case insensitive."""
        result = validate_sort_column("DATE")
        self.assertEqual(result, "date")
        
        result = validate_sort_column("Title")
        self.assertEqual(result, "title")

    def test_parse_column_titles_edge_cases(self):
        """Test parse_column_titles with edge cases."""
        class Args:
            column_title = ["", "=", "date=", "=New Date", "spaces = around = equals"]
        
        args = Args()
        result = parse_column_titles(args)
        
        # The "date=" entry should set date to empty string (this is the actual behavior)
        expected = {
            "date": "",  # Empty string because of "date=" entry
            "title": "Title",
            "author": "Author",
            "changes": "Change Requested",
            "approvals": "Approvals",
            "urls": "URLs"
        }
        self.assertEqual(result, expected)

    def test_parse_column_titles_whitespace_handling(self):
        """Test parse_column_titles handles whitespace correctly."""
        class Args:
            column_title = ["  date  =  Ready Date  ", "title=   PR Title   "]
        
        args = Args()
        result = parse_column_titles(args)
        
        self.assertEqual(result["date"], "Ready Date")
        self.assertEqual(result["title"], "PR Title")

    @patch("gh_pulls_summary.fetch_pull_requests")
    def test_fetch_and_process_pull_requests_no_prs(self, mock_fetch):
        """Test fetch_and_process_pull_requests when no PRs are returned."""
        mock_fetch.return_value = []
        
        result = fetch_and_process_pull_requests("owner", "repo")
        
        self.assertEqual(result, [])
        mock_fetch.assert_called_once_with("owner", "repo")

    @patch("gh_pulls_summary.fetch_pull_requests")
    def test_fetch_and_process_pull_requests_fetch_failure(self, mock_fetch):
        """Test fetch_and_process_pull_requests when API call fails."""
        mock_fetch.return_value = None
        
        result = fetch_and_process_pull_requests("owner", "repo")
        
        self.assertEqual(result, [])

    @patch("gh_pulls_summary.fetch_single_pull_request")
    def test_fetch_and_process_pull_requests_single_pr_failure(self, mock_fetch_single):
        """Test fetch_and_process_pull_requests when single PR fetch fails."""
        mock_fetch_single.return_value = None
        
        result = fetch_and_process_pull_requests("owner", "repo", pr_number=123)
        
        self.assertEqual(result, [])

    @patch("gh_pulls_summary.fetch_and_process_pull_requests")
    def test_generate_markdown_output_empty_results(self, mock_fetch):
        """Test generate_markdown_output with empty PR results."""
        mock_fetch.return_value = []
        
        class Args:
            owner = "owner"
            repo = "repo"
            draft_filter = None
            file_include = None
            file_exclude = None
            pr_number = None
            url_from_pr_content = None
            sort_column = "date"
        
        args = Args()
        result = generate_markdown_output(args)
        
        # Should still generate header even with no PRs
        self.assertIn("Date 🔽", result)
        self.assertIn("Title", result)
        self.assertIn("Author", result)

    def test_validate_sort_column_mixed_case_variations(self):
        """Test validate_sort_column with various case combinations."""
        test_cases = [
            ("date", "date"),
            ("DATE", "date"), 
            ("Date", "date"),
            ("dAtE", "date"),
            ("APPROVALS", "approvals"),
            ("Approvals", "approvals"),
            ("changes", "changes"),
            ("CHANGES", "changes")
        ]
        
        for input_col, expected in test_cases:
            result = validate_sort_column(input_col)
            self.assertEqual(result, expected)

    @patch("gh_pulls_summary.subprocess.check_output")
    def test_get_repo_and_owner_from_git_subprocess_error(self, mock_subprocess):
        """Test get_repo_and_owner_from_git when subprocess fails."""
        mock_subprocess.side_effect = Exception("Git command failed")
        
        result = get_repo_and_owner_from_git()
        
        self.assertEqual(result, (None, None))

    @patch("gh_pulls_summary.subprocess.check_output")
    def test_get_repo_and_owner_from_git_invalid_url_format(self, mock_subprocess):
        """Test get_repo_and_owner_from_git with invalid URL format."""
        mock_subprocess.return_value = "invalid-url-format"
        
        result = get_repo_and_owner_from_git()
        
        self.assertEqual(result, (None, None))

    @patch("gh_pulls_summary.subprocess.check_output")
    def test_get_repo_and_owner_from_git_ssh_url_no_git_suffix(self, mock_subprocess):
        """Test get_repo_and_owner_from_git with SSH URL without .git suffix."""
        mock_subprocess.return_value = "git@github.com:owner/repo"
        
        result = get_repo_and_owner_from_git()
        
        self.assertEqual(result, ("owner", "repo"))

    @patch("gh_pulls_summary.subprocess.check_output") 
    def test_get_repo_and_owner_from_git_https_url_no_git_suffix(self, mock_subprocess):
        """Test get_repo_and_owner_from_git with HTTPS URL without .git suffix."""
        mock_subprocess.return_value = "https://github.com/owner/repo"
        
        result = get_repo_and_owner_from_git()
        
        self.assertEqual(result, ("owner", "repo"))


if __name__ == "__main__":
    unittest.main() 