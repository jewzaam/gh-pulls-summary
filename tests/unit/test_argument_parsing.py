import logging
import unittest
from unittest.mock import patch

from gh_pulls_summary.main import parse_arguments

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TestArgumentParsing(unittest.TestCase):
    @patch(
        "sys.argv",
        [
            "gh_pulls_summary.py",
            "--owner",
            "owner",
            "--repo",
            "repo",
            "--draft-filter",
            "no-drafts",
            "--debug",
        ],
    )
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

    @patch("sys.argv", ["gh_pulls_summary.py"])
    @patch(
        "gh_pulls_summary.main.get_repo_and_owner_from_git",
        return_value=("mock_owner", "mock_repo"),
    )
    def test_parse_arguments_with_git_metadata(self, mock_get_repo_and_owner_from_git):
        args = parse_arguments()
        self.assertEqual(args.owner, "mock_owner")
        self.assertEqual(args.repo, "mock_repo")

    @patch(
        "gh_pulls_summary.main.get_repo_and_owner_from_git", return_value=(None, None)
    )
    @patch("sys.argv", ["gh_pulls_summary.py"])
    def test_parse_arguments_without_git_metadata(
        self, mock_get_repo_and_owner_from_git
    ):
        # Call parse_arguments
        args = parse_arguments()

        # Verify the parsed arguments
        self.assertIsNone(args.owner)
        self.assertIsNone(args.repo)
        self.assertIsNone(args.draft_filter)
        self.assertFalse(args.debug)

    @patch(
        "sys.argv",
        [
            "gh_pulls_summary.py",
            "--owner",
            "owner",
            "--repo",
            "repo",
            "--url-from-pr-content",
            "http://example.com",
        ],
    )
    def test_parse_arguments_with_url_from_pr_content(self):
        args = parse_arguments()
        self.assertEqual(args.owner, "owner")
        self.assertEqual(args.repo, "repo")
        self.assertEqual(args.url_from_pr_content, "http://example.com")

    @patch(
        "sys.argv",
        [
            "gh_pulls_summary.py",
            "--owner",
            "owner",
            "--repo",
            "repo",
            "--jira-include",
            "ANSTRAT-1234",
            "--jira-include",
            "ANSTRAT-5678",
        ],
    )
    def test_parse_arguments_with_jira_include(self):
        args = parse_arguments()
        self.assertEqual(args.owner, "owner")
        self.assertEqual(args.repo, "repo")
        self.assertEqual(args.jira_include, ["ANSTRAT-1234", "ANSTRAT-5678"])

    @patch(
        "sys.argv",
        [
            "gh_pulls_summary.py",
            "--owner",
            "owner",
            "--repo",
            "repo",
        ],
    )
    def test_parse_arguments_without_jira_include(self):
        args = parse_arguments()
        self.assertEqual(args.owner, "owner")
        self.assertEqual(args.repo, "repo")
        self.assertIsNone(args.jira_include)

    @patch(
        "sys.argv",
        [
            "gh_pulls_summary.py",
            "--owner",
            "owner",
            "--repo",
            "repo",
            "--review-requested-for",
            "testuser",
        ],
    )
    def test_parse_arguments_with_review_requested_for(self):
        args = parse_arguments()
        self.assertEqual(args.owner, "owner")
        self.assertEqual(args.repo, "repo")
        self.assertEqual(args.review_requested_for, "testuser")

    @patch(
        "sys.argv",
        [
            "gh_pulls_summary.py",
            "--owner",
            "owner",
            "--repo",
            "repo",
        ],
    )
    def test_parse_arguments_without_review_requested_for(self):
        args = parse_arguments()
        self.assertEqual(args.owner, "owner")
        self.assertEqual(args.repo, "repo")
        self.assertIsNone(args.review_requested_for)


if __name__ == "__main__":
    unittest.main()
