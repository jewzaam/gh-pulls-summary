import unittest
import logging
from unittest.mock import patch, MagicMock
from gh_pulls_summary import (
    github_api_request,
    fetch_pull_requests,
    fetch_issue_events,
    fetch_reviews,
    fetch_user_details,
    generate_markdown_output,
    fetch_and_process_pull_requests,
    main,
    parse_arguments,
    get_repo_and_owner_from_git,
)

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class TestGhPullsSummary(unittest.TestCase):

    @patch("gh_pulls_summary.requests.get")
    def test_github_api_request_with_pagination(self, mock_get):
        # Mock paginated responses
        mock_get.side_effect = [
            MagicMock(status_code=200, json=MagicMock(return_value=[{"id": 1}, {"id": 2}])),
            MagicMock(status_code=200, json=MagicMock(return_value=[{"id": 3}])),
            MagicMock(status_code=200, json=MagicMock(return_value=[])),
        ]

        result = github_api_request("/test-endpoint")
        self.assertEqual(len(result), 3)
        self.assertEqual(result, [{"id": 1}, {"id": 2}, {"id": 3}])

    @patch("gh_pulls_summary.requests.get")
    def test_github_api_request_with_dict_response(self, mock_get):
        # Mock a single dictionary response
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"key": "value"}))

        result = github_api_request("/test-endpoint", use_paging=False)
        self.assertEqual(result, {"key": "value"})

    @patch("gh_pulls_summary.requests.get")
    def test_fetch_pull_requests(self, mock_get):
        # Mock paginated responses for pull requests
        mock_get.side_effect = [
            MagicMock(status_code=200, json=MagicMock(return_value=[{"number": 1}, {"number": 2}])),
            MagicMock(status_code=200, json=MagicMock(return_value=[{"number": 3}])),
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # No more results
        ]

        result = fetch_pull_requests("owner", "repo")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["number"], 1)
        self.assertEqual(result[1]["number"], 2)
        self.assertEqual(result[2]["number"], 3)

    @patch("gh_pulls_summary.requests.get")
    def test_fetch_issue_events(self, mock_get):
        # Mock paginated responses for issue events
        mock_get.side_effect = [
            MagicMock(status_code=200, json=MagicMock(return_value=[{"event": "ready_for_review"}])),
            MagicMock(status_code=200, json=MagicMock(return_value=[{"event": "labeled"}])),
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # No more results
        ]

        result = fetch_issue_events("owner", "repo", 1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["event"], "ready_for_review")
        self.assertEqual(result[1]["event"], "labeled")

    @patch("gh_pulls_summary.requests.get")
    def test_fetch_reviews(self, mock_get):
        # Mock paginated responses for reviews
        mock_get.side_effect = [
            MagicMock(status_code=200, json=MagicMock(return_value=[{"state": "APPROVED"}])),
            MagicMock(status_code=200, json=MagicMock(return_value=[{"state": "COMMENTED"}])),
            MagicMock(status_code=200, json=MagicMock(return_value=[])),  # No more results
        ]

        result = fetch_reviews("owner", "repo", 1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["state"], "APPROVED")
        self.assertEqual(result[1]["state"], "COMMENTED")

    @patch("gh_pulls_summary.requests.get")
    def test_fetch_user_details(self, mock_get):
        # Mock user details response
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"name": "John Doe", "html_url": "https://github.com/johndoe"}))

        result = fetch_user_details("johndoe")
        self.assertEqual(result["name"], "John Doe")
        self.assertEqual(result["html_url"], "https://github.com/johndoe")

    def test_generate_markdown_output(self):
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

        self.assertEqual(generate_markdown_output(pull_requests), expected_output)


class TestFetchAndProcessPullRequests(unittest.TestCase):

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
            {"user": {"login": "reviewer1"}, "state": "APPROVED"},
            {"user": {"login": "reviewer2"}, "state": "COMMENTED"}
        ]

        # Call the function
        result = fetch_and_process_pull_requests("owner", "repo", draft_filter=None)

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

        # Verify mocks were called
        mock_fetch_pull_requests.assert_called_once_with("owner", "repo")
        mock_fetch_issue_events.assert_called_once_with("owner", "repo", 1)
        mock_fetch_user_details.assert_called_once_with("johndoe")
        mock_fetch_reviews.assert_called_once_with("owner", "repo", 1)

    @patch("gh_pulls_summary.fetch_pull_requests")
    @patch("gh_pulls_summary.fetch_issue_events")
    @patch("gh_pulls_summary.fetch_user_details")
    @patch("gh_pulls_summary.fetch_reviews")
    def test_pr_ready_date_not_set(self, mock_fetch_reviews, mock_fetch_user_details, mock_fetch_issue_events, mock_fetch_pull_requests):
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

        # Mock issue events (no "ready_for_review" event)
        mock_fetch_issue_events.return_value = []

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
        result = fetch_and_process_pull_requests("owner", "repo", draft_filter=None)

        # Verify the result
        expected_result = [
            {
                "date": "2025-05-01",  # Falls back to created_at date
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

        # Verify mocks were called
        mock_fetch_pull_requests.assert_called_once_with("owner", "repo")
        mock_fetch_issue_events.assert_called_once_with("owner", "repo", 1)
        mock_fetch_user_details.assert_called_once_with("johndoe")
        mock_fetch_reviews.assert_called_once_with("owner", "repo", 1)


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
        result = fetch_and_process_pull_requests("owner", "repo", draft_filter="only-drafts")

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
        result = fetch_and_process_pull_requests("owner", "repo", draft_filter="no-drafts")

        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Regular PR")


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
        mock_fetch_and_process_pull_requests.assert_called_once_with("owner", "repo", None)

        # Verify that generate_markdown_output was called with the processed pull requests
        mock_generate_markdown_output.assert_called_once_with(mock_fetch_and_process_pull_requests.return_value)

        # Verify that the output was printed
        mock_print.assert_called_once_with(mock_generate_markdown_output.return_value)


class TestParseArguments(unittest.TestCase):

    @patch("sys.argv", ["gh_pulls_summary.py", "--owner", "owner", "--repo", "repo", "--draft-filter", "no-drafts", "--debug"])
    def test_parse_arguments_with_all_options(self):
        args = parse_arguments()
        self.assertEqual(args.owner, "owner")
        self.assertEqual(args.repo, "repo")
        self.assertEqual(args.draft_filter, "no-drafts")
        self.assertTrue(args.debug)

    @patch("sys.argv", ["gh_pulls_summary.py", "--owner", "owner", "--repo", "repo"])
    def test_parse_arguments_with_required_options_only(self):
        args = parse_arguments()
        self.assertEqual(args.owner, "owner")
        self.assertEqual(args.repo, "repo")
        self.assertIsNone(args.draft_filter)
        self.assertFalse(args.debug)

    @patch("gh_pulls_summary.get_repo_and_owner_from_git")
    @patch("sys.argv", ["gh_pulls_summary.py"])
    def test_parse_arguments_with_git_metadata(self, mock_get_repo_and_owner_from_git):
        # Mock Git metadata
        mock_get_repo_and_owner_from_git.return_value = ("mock_owner", "mock_repo")

        # Call parse_arguments
        args = parse_arguments()

        # Verify the parsed arguments
        self.assertEqual(args.owner, "mock_owner")
        self.assertEqual(args.repo, "mock_repo")
        self.assertIsNone(args.draft_filter)
        self.assertFalse(args.debug)

    @patch("gh_pulls_summary.get_repo_and_owner_from_git", return_value=(None, None))
    @patch("sys.argv", ["gh_pulls_summary.py"])
    def test_parse_arguments_without_git_metadata(self, mock_get_repo_and_owner_from_git):
        # Call parse_arguments
        args = parse_arguments()

        # Verify the parsed arguments
        self.assertIsNone(args.owner)
        self.assertIsNone(args.repo)
        self.assertIsNone(args.draft_filter)
        self.assertFalse(args.debug)


if __name__ == "__main__":
    unittest.main()
