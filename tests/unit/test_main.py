import logging
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

from gh_pulls_summary.main import (
    GitHubAPIError,
    NetworkError,
    RateLimitError,
    ValidationError,
    fetch_pr_diff,
    fetch_pr_files,
    fetch_single_pull_request,
    generate_markdown_output,
    generate_timestamp,
    get_authenticated_user_info,
    main,
)

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


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
            column_title = None
            sort_column = "date"

        args = Args()
        # Patch fetch_and_process_pull_requests to avoid network
        with patch(
            "gh_pulls_summary.main.fetch_and_process_pull_requests"
        ) as mock_fetch:
            mock_fetch.return_value = [
                {
                    "date": "2025-05-02",
                    "title": "Fix bug Y",
                    "number": 124,
                    "url": "https://github.com/owner/repo/pull/124",
                    "author_name": "Jane Smith",
                    "author_url": "https://github.com/janesmith",
                    "reviews": 1,
                    "approvals": 1,
                    "changes": 0,
                    "pr_body_urls_dict": {},
                },
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
                },
            ]
            markdown_output = generate_markdown_output(args)
        expected_output = (
            "| Date 🔽 | Title | Author | Change Requested | Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 2 |\n"
            "| 2025-05-02 | Fix bug Y #[124](https://github.com/owner/repo/pull/124) | [Jane Smith](https://github.com/janesmith) | 0 | 1 of 1 |"
        )
        self.assertEqual(markdown_output, expected_output)

    def test_generate_markdown_output_with_custom_titles(self):
        """Test generate_markdown_output with custom column titles."""

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
            sort_column = "date"

        args = Args()
        with patch(
            "gh_pulls_summary.main.fetch_and_process_pull_requests"
        ) as mock_fetch:
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
            "| Ready Date 🔽 | Title | Author | Change Requested | Total Approvals |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 2 |"
        )
        self.assertEqual(markdown_output, expected_output)

    def test_generate_markdown_output_sort_by_approvals(self):
        """Test generate_markdown_output with sort_column=approvals."""

        class Args:
            owner = "owner"
            repo = "repo"
            draft_filter = None
            debug = False
            pr_number = None
            file_include = None
            file_exclude = None
            url_from_pr_content = None
            column_title = None
            sort_column = "approvals"

        args = Args()
        with patch(
            "gh_pulls_summary.main.fetch_and_process_pull_requests"
        ) as mock_fetch:
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
                },
                {
                    "date": "2025-05-02",
                    "title": "Fix bug Y",
                    "number": 124,
                    "url": "https://github.com/owner/repo/pull/124",
                    "author_name": "Jane Smith",
                    "author_url": "https://github.com/janesmith",
                    "reviews": 1,
                    "approvals": 1,
                    "changes": 0,
                    "pr_body_urls_dict": {},
                },
            ]
            markdown_output = generate_markdown_output(args)
        expected_output = (
            "| Date | Title | Author | Change Requested | Approvals 🔽 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 2025-05-02 | Fix bug Y #[124](https://github.com/owner/repo/pull/124) | [Jane Smith](https://github.com/janesmith) | 0 | 1 of 1 |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 2 |"
        )
        self.assertEqual(markdown_output, expected_output)

    @patch("gh_pulls_summary.main.generate_markdown_output")
    @patch("gh_pulls_summary.main.generate_timestamp")
    @patch("gh_pulls_summary.main.parse_arguments")
    def test_main(
        self,
        mock_parse_arguments,
        mock_generate_timestamp,
        mock_generate_markdown_output,
    ):
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
            output_markdown=None,
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
        mock_generate_markdown_output.assert_called_once_with(
            mock_parse_arguments.return_value
        )
        mock_generate_timestamp.assert_called_once()
        mock_print.assert_called_once_with(
            "**Generated at 2025-05-14 15:12Z**\n\n| Date | Title | Author | Reviews | Approvals |\n| --- | --- | --- | --- | --- |\n| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 3 | 2 |\n"
        )

    @patch(
        "gh_pulls_summary.main.get_repo_and_owner_from_git", return_value=(None, None)
    )
    @patch("gh_pulls_summary.main.parse_arguments")
    @patch("builtins.print")
    @patch("gh_pulls_summary.main.sys.exit")
    def test_main_failure_without_owner_and_repo(
        self,
        mock_exit,
        mock_print,
        mock_parse_arguments,
        mock_get_repo_and_owner_from_git,
    ):
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit(1)

        # Mock command-line arguments with no owner or repo
        mock_parse_arguments.return_value = MagicMock(
            owner=None,
            repo=None,
            draft_filter=None,
            debug=False,
            pr_number=None,
            output_markdown=None,
        )

        # Call main and check that sys.exit is called
        with self.assertRaises(SystemExit) as ctx:
            main()

        # Verify that sys.exit was called with code 1
        self.assertEqual(ctx.exception.code, 1)
        mock_exit.assert_called_with(1)

        # Verify that error message was printed to stderr
        mock_print.assert_any_call(
            "ERROR: Repository owner and name must be specified.", file=sys.stderr
        )

    @patch("gh_pulls_summary.main.generate_markdown_output")
    @patch("gh_pulls_summary.main.generate_timestamp")
    @patch("gh_pulls_summary.main.parse_arguments")
    def test_main_output_markdown(
        self,
        mock_parse_arguments,
        mock_generate_timestamp,
        mock_generate_markdown_output,
    ):
        """Test the main function with --output-markdown argument."""
        import os
        import tempfile

        # Create a temporary file path
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            output_path = tmpfile.name
        try:
            mock_parse_arguments.return_value = MagicMock(
                owner="owner",
                repo="repo",
                draft_filter=None,
                debug=False,
                pr_number=None,
                file_include=None,
                file_exclude=None,
                url_from_pr_content=None,
                output_markdown=output_path,
            )
            mock_generate_timestamp.return_value = (
                "**Generated at 2025-05-14 15:12Z**\n"
            )
            mock_generate_markdown_output.return_value = (
                "| Date | Title | Author | Reviews | Approvals |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 3 | 2 |"
            )
            # Patch print to capture the informational message
            with patch("builtins.print") as mock_print:
                main()
            mock_generate_markdown_output.assert_called_once_with(
                mock_parse_arguments.return_value
            )
            mock_generate_timestamp.assert_called_once()
            # Now expect print to be called with the informational message
            mock_print.assert_called_once_with(
                f"Markdown output written to: {output_path}", file=sys.stderr
            )
            # Check file contents
            with open(output_path, encoding="utf-8") as f:
                file_content = f.read()
            expected = "**Generated at 2025-05-14 15:12Z**\n\n| Date | Title | Author | Reviews | Approvals |\n| --- | --- | --- | --- | --- |\n| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 3 | 2 |\n"
            self.assertEqual(file_content, expected)
        finally:
            os.remove(output_path)

    @patch("gh_pulls_summary.main.generate_markdown_output")
    @patch("gh_pulls_summary.main.generate_timestamp")
    @patch("gh_pulls_summary.main.parse_arguments")
    def test_main_url_from_pr_content(
        self,
        mock_parse_arguments,
        mock_generate_timestamp,
        mock_generate_markdown_output,
    ):
        """Test the main function with --url-from-pr-content argument."""
        mock_parse_arguments.return_value = MagicMock(
            owner="owner",
            repo="repo",
            draft_filter=None,
            debug=False,
            pr_number=None,
            file_include=None,
            file_exclude=None,
            url_from_pr_content=r"https://example.com/[^\s]+",
            output_markdown=None,
        )
        mock_generate_timestamp.return_value = "**Generated at 2025-05-14 15:12Z**\n"
        mock_generate_markdown_output.return_value = (
            "| Date 🔽 | Title | Author | Change Requested | Approvals | URLs |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 2 | [bar123](https://example.com/foo/bar123) [baz456](https://example.com/foo/baz456) |"
        )
        with patch("builtins.print") as mock_print:
            main()
        mock_generate_markdown_output.assert_called_once_with(
            mock_parse_arguments.return_value
        )
        mock_generate_timestamp.assert_called_once()
        mock_print.assert_called_once_with(
            "**Generated at 2025-05-14 15:12Z**\n\n| Date 🔽 | Title | Author | Change Requested | Approvals | URLs |\n| --- | --- | --- | --- | --- | --- |\n| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 2 | [bar123](https://example.com/foo/bar123) [baz456](https://example.com/foo/baz456) |\n"
        )

    @patch("gh_pulls_summary.main.sys.exit")
    @patch("builtins.print")
    @patch("gh_pulls_summary.main.generate_markdown_output")
    @patch("gh_pulls_summary.main.parse_arguments")
    def test_main_rate_limit_error(
        self, mock_parse, mock_generate, mock_print, mock_exit
    ):
        """Test main function handles RateLimitError."""
        mock_exit.side_effect = SystemExit(1)
        mock_parse.return_value = Mock(
            owner="test", repo="test", debug=False, output_markdown=None
        )
        mock_generate.side_effect = RateLimitError("Rate limit exceeded")

        with self.assertRaises(SystemExit):
            main()

        mock_print.assert_called_with(
            "ERROR: GitHub API rate limit exceeded. Rate limit exceeded",
            file=sys.stderr,
        )
        mock_exit.assert_called_with(1)

    @patch("gh_pulls_summary.main.sys.exit")
    @patch("builtins.print")
    @patch("gh_pulls_summary.main.generate_markdown_output")
    @patch("gh_pulls_summary.main.parse_arguments")
    def test_main_github_api_error(
        self, mock_parse, mock_generate, mock_print, mock_exit
    ):
        """Test main function handles GitHubAPIError."""
        mock_exit.side_effect = SystemExit(1)
        mock_parse.return_value = Mock(
            owner="test", repo="test", debug=False, output_markdown=None
        )
        mock_generate.side_effect = GitHubAPIError(
            "API error", status_code=404, response_text="Not found"
        )

        with self.assertRaises(SystemExit):
            main()

        mock_print.assert_called_with(
            "ERROR: GitHub API error. API error", file=sys.stderr
        )
        mock_exit.assert_called_with(1)

    @patch("gh_pulls_summary.main.sys.exit")
    @patch("builtins.print")
    @patch("gh_pulls_summary.main.generate_markdown_output")
    @patch("gh_pulls_summary.main.parse_arguments")
    def test_main_network_error(self, mock_parse, mock_generate, mock_print, mock_exit):
        """Test main function handles NetworkError."""
        mock_exit.side_effect = SystemExit(1)
        mock_parse.return_value = Mock(
            owner="test", repo="test", debug=False, output_markdown=None
        )
        mock_generate.side_effect = NetworkError("Network failed")

        with self.assertRaises(SystemExit):
            main()

        mock_print.assert_called_with(
            "ERROR: Network error. Network failed", file=sys.stderr
        )
        mock_exit.assert_called_with(1)

    @patch("gh_pulls_summary.main.sys.exit")
    @patch("builtins.print")
    @patch("gh_pulls_summary.main.generate_markdown_output")
    @patch("gh_pulls_summary.main.parse_arguments")
    def test_main_validation_error(
        self, mock_parse, mock_generate, mock_print, mock_exit
    ):
        """Test main function handles ValidationError."""
        mock_exit.side_effect = SystemExit(1)
        mock_parse.return_value = Mock(
            owner="test", repo="test", debug=False, output_markdown=None
        )
        mock_generate.side_effect = ValidationError("Invalid input")

        with self.assertRaises(SystemExit):
            main()

        mock_print.assert_called_with(
            "ERROR: Input validation failed. Invalid input", file=sys.stderr
        )
        mock_exit.assert_called_with(1)


class TestGithubApiHelpers(unittest.TestCase):
    @patch("gh_pulls_summary.main.github_api_request")
    def test_fetch_single_pull_request(self, mock_github_api_request):
        mock_github_api_request.return_value = {"number": 42, "title": "Test PR"}
        result = fetch_single_pull_request("owner", "repo", 42)
        mock_github_api_request.assert_called_once_with(
            "/repos/owner/repo/pulls/42", use_paging=False
        )
        self.assertEqual(result, {"number": 42, "title": "Test PR"})

    @patch("gh_pulls_summary.main.github_api_request")
    def test_fetch_pr_files(self, mock_github_api_request):
        mock_github_api_request.return_value = [
            {"filename": "file1.py"},
            {"filename": "file2.py"},
        ]
        result = fetch_pr_files("owner", "repo", 123)
        mock_github_api_request.assert_called_once_with(
            "/repos/owner/repo/pulls/123/files", use_paging=True
        )
        self.assertEqual(result, [{"filename": "file1.py"}, {"filename": "file2.py"}])

    @patch("gh_pulls_summary.main.requests.get")
    def test_fetch_pr_diff(self, mock_requests_get):
        from gh_pulls_summary.main import GitHubAPIError

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "diff --git a/file1.py b/file1.py"
        mock_requests_get.return_value = mock_response
        result = fetch_pr_diff("owner", "repo", 99)
        mock_requests_get.assert_called_once()
        self.assertEqual(result, "diff --git a/file1.py b/file1.py")

        # Test error case
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_requests_get.return_value = mock_response
        with self.assertRaises(GitHubAPIError) as ctx:
            fetch_pr_diff("owner", "repo", 99)
        self.assertIn("Pull request #99 not found", str(ctx.exception))

    @patch("gh_pulls_summary.main.requests.get")
    def test_get_authenticated_user_info_success(self, mock_requests_get):
        """Test get_authenticated_user_info with successful response."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "name": "Test User",
            "html_url": "https://github.com/testuser",
        }
        mock_requests_get.return_value = mock_response

        # Call the function
        name, html_url = get_authenticated_user_info()

        # Verify the request was made to the correct endpoint
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/user")
        self.assertEqual(call_args[1]["timeout"], 5)
        # Headers will include Authorization if GITHUB_TOKEN is set, so just verify required headers
        headers = call_args[1]["headers"]
        self.assertIn("Accept", headers)
        self.assertIn("X-GitHub-Api-Version", headers)

        # Verify the json method was called (this covers line 569: data = resp.json())
        mock_response.json.assert_called_once()

        # Verify the returned values
        self.assertEqual(name, "Test User")
        self.assertEqual(html_url, "https://github.com/testuser")

    @patch("gh_pulls_summary.main.requests.get")
    def test_get_authenticated_user_info_success_no_name(self, mock_requests_get):
        """Test get_authenticated_user_info with successful response but no name field."""
        # Mock the response with no name field
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "html_url": "https://github.com/testuser",
        }
        mock_requests_get.return_value = mock_response

        # Call the function
        name, html_url = get_authenticated_user_info()

        # Verify the json method was called (this covers line 569: data = resp.json())
        mock_response.json.assert_called_once()

        # Verify the returned values (should fallback to login)
        self.assertEqual(name, "testuser")
        self.assertEqual(html_url, "https://github.com/testuser")

    @patch("gh_pulls_summary.main.requests.get")
    def test_get_authenticated_user_info_failure(self, mock_requests_get):
        """Test get_authenticated_user_info with failed response."""
        # Mock a failed response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests_get.return_value = mock_response

        # Call the function
        name, html_url = get_authenticated_user_info()

        # Verify the json method was NOT called (since status_code != 200)
        mock_response.json.assert_not_called()

        # Verify the returned values are None
        self.assertIsNone(name)
        self.assertIsNone(html_url)


class TestHelperFunctions(unittest.TestCase):
    """Test cases for the newly refactored helper functions."""

    def test_parse_column_titles_default(self):
        """Test parse_column_titles with no custom titles."""
        from gh_pulls_summary.main import parse_column_titles

        class Args:
            column_title = None

        args = Args()
        result = parse_column_titles(args)

        expected = {
            "date": "Date",
            "title": "Title",
            "author": "Author",
            "changes": "Change Requested",
            "approvals": "Approvals",
            "urls": "URLs",
        }
        self.assertEqual(result, expected)

    def test_parse_column_titles_with_custom_titles(self):
        """Test parse_column_titles with custom column titles."""
        from gh_pulls_summary.main import parse_column_titles

        class Args:
            column_title = [
                "date=Ready Date",
                "approvals=Total Approvals",
                "author=Contributor",
            ]

        args = Args()
        result = parse_column_titles(args)

        expected = {
            "date": "Ready Date",
            "title": "Title",
            "author": "Contributor",
            "changes": "Change Requested",
            "approvals": "Total Approvals",
            "urls": "URLs",
        }
        self.assertEqual(result, expected)

    def test_parse_column_titles_with_invalid_column(self):
        """Test parse_column_titles with invalid column name."""
        from gh_pulls_summary.main import parse_column_titles

        class Args:
            column_title = ["date=Ready Date", "invalid=Bad Column", "title=PR Title"]

        args = Args()

        with patch("gh_pulls_summary.main.logging.warning") as mock_warning:
            result = parse_column_titles(args)
            mock_warning.assert_called_once_with(
                "Invalid column name 'invalid' in --column-title. Valid columns: date, title, author, changes, approvals, urls"
            )

        # Should ignore invalid column but keep valid ones
        expected = {
            "date": "Ready Date",
            "title": "PR Title",
            "author": "Author",
            "changes": "Change Requested",
            "approvals": "Approvals",
            "urls": "URLs",
        }
        self.assertEqual(result, expected)

    def test_parse_column_titles_with_malformed_entry(self):
        """Test parse_column_titles with malformed entries (no equals sign)."""
        from gh_pulls_summary.main import parse_column_titles

        class Args:
            column_title = ["date=Ready Date", "bad-entry", "title=PR Title"]

        args = Args()
        result = parse_column_titles(args)

        # Should skip malformed entries
        expected = {
            "date": "Ready Date",
            "title": "PR Title",
            "author": "Author",
            "changes": "Change Requested",
            "approvals": "Approvals",
            "urls": "URLs",
        }
        self.assertEqual(result, expected)

    def test_parse_column_titles_no_attribute(self):
        """Test parse_column_titles when args doesn't have column_title attribute."""
        from gh_pulls_summary.main import parse_column_titles

        class Args:
            pass

        args = Args()
        result = parse_column_titles(args)

        # Should return defaults
        expected = {
            "date": "Date",
            "title": "Title",
            "author": "Author",
            "changes": "Change Requested",
            "approvals": "Approvals",
            "urls": "URLs",
        }
        self.assertEqual(result, expected)

    def test_validate_sort_column_invalid(self):
        """Test validate_sort_column with invalid columns."""
        from gh_pulls_summary.main import ValidationError, validate_sort_column

        invalid_columns = ["invalid", "foo", "bar"]
        for col in invalid_columns:
            with self.assertRaises(ValidationError):
                validate_sort_column(col)

    def test_validate_sort_column_case_insensitive(self):
        """Test validate_sort_column is case insensitive."""
        from gh_pulls_summary.main import validate_sort_column

        result = validate_sort_column("DATE")
        self.assertEqual(result, "date")

        result = validate_sort_column("Title")
        self.assertEqual(result, "title")

        result = validate_sort_column("APPROVALS")
        self.assertEqual(result, "approvals")

    @patch("gh_pulls_summary.main.requests.get")
    def test_fetch_pr_diff(self, mock_get):
        """Test fetch_pr_diff function with error response."""
        from gh_pulls_summary.main import GitHubAPIError

        # Mock HTTP 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        with self.assertRaises(GitHubAPIError) as ctx:
            fetch_pr_diff("owner", "repo", 99)

        self.assertIn("Pull request #99 not found", str(ctx.exception))

    @patch("gh_pulls_summary.main.sys.exit")
    def test_main_failure_without_owner_and_repo(self, mock_exit):
        """Test main function exits when owner and repo are not provided."""
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit(1)

        with patch("gh_pulls_summary.main.parse_arguments") as mock_parse:
            mock_args = Mock()
            mock_args.owner = None
            mock_args.repo = None
            # Add the required attributes that the main function checks
            mock_args.file_include = None
            mock_args.file_exclude = None
            mock_args.pr_number = None
            mock_args.url_from_pr_content = None
            mock_args.draft_filter = None
            mock_args.sort_column = "date"
            mock_args.column_title = None
            mock_args.debug = False
            mock_args.output_markdown = None
            mock_parse.return_value = mock_args

            with self.assertRaises(SystemExit) as ctx:
                main()

            # Verify that sys.exit was called with code 1
            self.assertEqual(ctx.exception.code, 1)
            mock_exit.assert_called_with(1)

    @patch("gh_pulls_summary.main.open", create=True)
    @patch("gh_pulls_summary.main.generate_markdown_output")
    @patch("gh_pulls_summary.main.get_authenticated_user_info")
    @patch("gh_pulls_summary.main.generate_timestamp")
    @patch("gh_pulls_summary.main.configure_logging")
    @patch("gh_pulls_summary.main.parse_arguments")
    @patch("builtins.print")
    def test_main_output_markdown(
        self,
        mock_print,
        mock_parse,
        mock_configure,
        mock_timestamp,
        mock_auth,
        mock_generate,
        mock_open,
    ):
        """Test the main function with --output-markdown argument."""
        import os
        import tempfile

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_filename = temp_file.name

        try:
            # Mock parse_arguments to return appropriate args
            mock_args = Mock()
            mock_args.owner = "test_owner"
            mock_args.repo = "test_repo"
            mock_args.output_markdown = temp_filename
            mock_args.debug = False
            mock_parse.return_value = mock_args

            # Mock other functions
            mock_timestamp.return_value = "**Generated at 2023-01-01 12:00Z**"
            mock_auth.return_value = ("Test User", "https://github.com/test")
            mock_generate.return_value = (
                "| Date | Title | Author |\n| --- | --- | --- |"
            )

            # Mock the file context manager
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            main()

            # Verify file was opened for writing
            mock_open.assert_called_once_with(temp_filename, "w", encoding="utf-8")

            # Verify content was written to file
            mock_file.write.assert_called_once()
            written_content = mock_file.write.call_args[0][0]
            self.assertIn("**Generated at 2023-01-01 12:00Z**", written_content)
            self.assertIn("| Date | Title | Author |", written_content)

            # Verify the new informational message was printed
            mock_print.assert_called_once_with(
                f"Markdown output written to: {temp_filename}",
                file=mock_print.call_args[1]["file"],
            )

        finally:
            # Clean up the temporary file
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_create_markdown_table_header_no_url_column(self):
        """Test create_markdown_table_header without URL column."""
        from gh_pulls_summary.main import create_markdown_table_header

        titles = {
            "date": "Date 🔽",
            "title": "Title",
            "author": "Author",
            "changes": "Change Requested",
            "approvals": "Approvals",
        }

        header, separator = create_markdown_table_header(titles, url_column=False)

        expected_header = "| Date 🔽 | Title | Author | Change Requested | Approvals |"
        expected_separator = "| --- | --- | --- | --- | --- |"

        self.assertEqual(header, expected_header)
        self.assertEqual(separator, expected_separator)

    def test_create_markdown_table_header_with_url_column(self):
        """Test create_markdown_table_header with URL column."""
        from gh_pulls_summary.main import create_markdown_table_header

        titles = {
            "date": "Date",
            "title": "Title",
            "author": "Author",
            "changes": "Change Requested",
            "approvals": "Approvals 🔽",
            "urls": "URLs",
        }

        header, separator = create_markdown_table_header(titles, url_column=True)

        expected_header = (
            "| Date | Title | Author | Change Requested | Approvals 🔽 | URLs |"
        )
        expected_separator = "| --- | --- | --- | --- | --- | --- |"

        self.assertEqual(header, expected_header)
        self.assertEqual(separator, expected_separator)

    def test_create_markdown_table_row_no_url_column(self):
        """Test create_markdown_table_row without URL column."""
        from gh_pulls_summary.main import create_markdown_table_row

        pr = {
            "date": "2025-05-01",
            "title": "Add feature X",
            "number": 123,
            "url": "https://github.com/owner/repo/pull/123",
            "author_name": "John Doe",
            "author_url": "https://github.com/johndoe",
            "changes": 1,
            "approvals": 2,
            "reviews": 3,
        }

        result = create_markdown_table_row(pr, url_column=False)

        expected = "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 1 | 2 of 3 |"
        self.assertEqual(result, expected)

    def test_create_markdown_table_row_with_url_column_and_urls(self):
        """Test create_markdown_table_row with URL column and URLs present."""
        from gh_pulls_summary.main import create_markdown_table_row

        pr = {
            "date": "2025-05-01",
            "title": "Add feature X",
            "number": 123,
            "url": "https://github.com/owner/repo/pull/123",
            "author_name": "John Doe",
            "author_url": "https://github.com/johndoe",
            "changes": 0,
            "approvals": 1,
            "reviews": 1,
            "pr_body_urls_dict": {
                "bar123": "https://example.com/foo/bar123",
                "baz456": "https://example.com/foo/baz456",
            },
        }

        result = create_markdown_table_row(pr, url_column=True)

        expected = "| 2025-05-01 | Add feature X #[123](https://github.com/owner/repo/pull/123) | [John Doe](https://github.com/johndoe) | 0 | 1 of 1 | [bar123](https://example.com/foo/bar123) [baz456](https://example.com/foo/baz456) |"
        self.assertEqual(result, expected)

    def test_create_markdown_table_row_with_url_column_no_urls(self):
        """Test create_markdown_table_row with URL column but no URLs."""
        from gh_pulls_summary.main import create_markdown_table_row

        pr = {
            "date": "2025-05-02",
            "title": "Fix bug Y",
            "number": 124,
            "url": "https://github.com/owner/repo/pull/124",
            "author_name": "Jane Smith",
            "author_url": "https://github.com/janesmith",
            "changes": 2,
            "approvals": 0,
            "reviews": 2,
            "pr_body_urls_dict": {},
        }

        result = create_markdown_table_row(pr, url_column=True)

        expected = "| 2025-05-02 | Fix bug Y #[124](https://github.com/owner/repo/pull/124) | [Jane Smith](https://github.com/janesmith) | 2 | 0 of 2 | |"
        self.assertEqual(result, expected)

    def test_create_markdown_table_row_with_url_column_missing_dict(self):
        """Test create_markdown_table_row with URL column when pr_body_urls_dict is missing."""
        from gh_pulls_summary.main import create_markdown_table_row

        pr = {
            "date": "2025-05-03",
            "title": "Update docs",
            "number": 125,
            "url": "https://github.com/owner/repo/pull/125",
            "author_name": "Bob Wilson",
            "author_url": "https://github.com/bobwilson",
            "changes": 0,
            "approvals": 1,
            "reviews": 1,
            # No pr_body_urls_dict key
        }

        result = create_markdown_table_row(pr, url_column=True)

        expected = "| 2025-05-03 | Update docs #[125](https://github.com/owner/repo/pull/125) | [Bob Wilson](https://github.com/bobwilson) | 0 | 1 of 1 | |"
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
