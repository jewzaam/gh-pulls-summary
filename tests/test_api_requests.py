import unittest
from unittest.mock import patch, MagicMock
from gh_pulls_summary import (
    github_api_request,
    fetch_pull_requests,
    fetch_issue_events,
    fetch_reviews,
    fetch_user_details,
)

class TestApiRequests(unittest.TestCase):

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

if __name__ == "__main__":
    unittest.main()