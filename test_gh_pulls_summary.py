import unittest
from unittest.mock import patch, MagicMock
from gh_pulls_summary import (
    github_api_request,
    fetch_pull_requests,
    fetch_issue_events,
    fetch_reviews,
    fetch_user_details,
)

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
        # Mock pull requests response
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=[{"number": 1}, {"number": 2}]))

        result = fetch_pull_requests("owner", "repo")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["number"], 1)

    @patch("gh_pulls_summary.requests.get")
    def test_fetch_issue_events(self, mock_get):
        # Mock issue events response
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=[{"event": "ready_for_review"}]))

        result = fetch_issue_events("owner", "repo", 1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["event"], "ready_for_review")

    @patch("gh_pulls_summary.requests.get")
    def test_fetch_reviews(self, mock_get):
        # Mock reviews response with multiple states
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value=[
                {"state": "APPROVED"},
                {"state": "COMMENTED"}
            ])
        )

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


if __name__ == "__main__":
    unittest.main()