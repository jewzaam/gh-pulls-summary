#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from gh_pulls_summary import (
    github_api_request, 
    fetch_user_details,
    validate_sort_column,
    GitHubAPIError,
    NetworkError,
    ValidationError,
    RateLimitError
)

class TestErrorConditions(unittest.TestCase):
    
    @patch('gh_pulls_summary.requests.get')
    def test_github_api_request_http_error(self, mock_get):
        """Test github_api_request with HTTP error response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        with self.assertRaises(GitHubAPIError) as ctx:
            github_api_request("/test/endpoint")
        
        self.assertIn("GitHub API endpoint not found", str(ctx.exception))
    
    @patch('gh_pulls_summary.requests.get')
    def test_github_api_request_json_error(self, mock_get):
        """Test github_api_request when JSON parsing fails."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with self.assertRaises(GitHubAPIError) as ctx:
            github_api_request("/test/endpoint")
        
        self.assertIn("Invalid JSON response from GitHub API", str(ctx.exception))
    
    @patch('gh_pulls_summary.requests.get')
    def test_github_api_request_network_error(self, mock_get):
        """Test github_api_request with network error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with self.assertRaises(NetworkError) as ctx:
            github_api_request("/test/endpoint")
        
        self.assertIn("Network connection failed", str(ctx.exception))
    
    def test_validate_sort_column_empty_string(self):
        """Test validate_sort_column with empty string."""
        with self.assertRaises(ValidationError) as ctx:
            validate_sort_column("")
        
        self.assertIn("Invalid sort column", str(ctx.exception))

    def test_validate_sort_column_invalid(self):
        """Test validate_sort_column with invalid column."""
        with self.assertRaises(ValidationError) as ctx:
            validate_sort_column("invalid")
        
        self.assertIn("Invalid sort column", str(ctx.exception))
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_success(self, mock_get):
        """Test fetch_user_details with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "name": "Test User",
            "html_url": "https://github.com/testuser"
        }
        mock_get.return_value = mock_response
        
        result = fetch_user_details("testuser")
        
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result["login"], "testuser")
            self.assertEqual(result["name"], "Test User")
            self.assertEqual(result["html_url"], "https://github.com/testuser")
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_404_error(self, mock_get):
        """Test fetch_user_details returns None for 404 error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = fetch_user_details("nonexistent_user")
        
        self.assertIsNone(result)
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_copilot_user(self, mock_get):
        """Test fetch_user_details returns None for GitHub Copilot user (common 404 case)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = fetch_user_details("Copilot")
        
        self.assertIsNone(result)
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_empty_username(self, mock_get):
        """Test fetch_user_details with empty username."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": ""}
        mock_get.return_value = mock_response
        
        result = fetch_user_details("")
        
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result["login"], "")
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_rate_limit_error(self, mock_get):
        """Test fetch_user_details raises RateLimitError for rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "0"}
        mock_get.return_value = mock_response
        
        with self.assertRaises(RateLimitError) as ctx:
            fetch_user_details("testuser")
        
        self.assertIn("GitHub API rate limit exceeded", str(ctx.exception))
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_other_http_error(self, mock_get):
        """Test fetch_user_details raises GitHubAPIError for other HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        with self.assertRaises(GitHubAPIError) as ctx:
            fetch_user_details("testuser")
        
        self.assertIn("Failed to fetch user details", str(ctx.exception))
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_network_error(self, mock_get):
        """Test fetch_user_details raises NetworkError for network errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with self.assertRaises(NetworkError) as ctx:
            fetch_user_details("testuser")
        
        self.assertIn("Network connection failed", str(ctx.exception))
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_json_parse_error(self, mock_get):
        """Test fetch_user_details raises GitHubAPIError when JSON parsing fails."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with self.assertRaises(GitHubAPIError) as ctx:
            fetch_user_details("testuser")
        
        self.assertIn("Invalid JSON response", str(ctx.exception))
    
    @patch('gh_pulls_summary.requests.get')
    def test_fetch_user_details_403_without_rate_limit(self, mock_get):
        """Test fetch_user_details raises GitHubAPIError for 403 without rate limit headers."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {}
        mock_response.text = "Forbidden"
        mock_get.return_value = mock_response
        
        with self.assertRaises(GitHubAPIError) as ctx:
            fetch_user_details("testuser")
        
        self.assertIn("Failed to fetch user details", str(ctx.exception))

if __name__ == '__main__':
    unittest.main() 