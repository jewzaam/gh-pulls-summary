# Integration Tests

This document explains the integration tests for the GitHub Pull Requests Summary Tool.

## Overview

The integration tests (`integration_tests/test_integration.py` and `integration_tests/test_integration_simple.py`) are designed to test the tool against real GitHub APIs and repositories, complementing the unit tests that use mocked dependencies.

## Key Features

### Real API Testing
- Tests against the actual GitHub API without mocking
- Validates end-to-end functionality with real data
- Ensures the tool works with actual GitHub responses

### Rate Limit Awareness
- Designed to work without GitHub tokens (unauthenticated requests)
- Includes delays between requests to avoid rate limiting
- Tests are structured to minimize API calls

### Test Repository
- Uses the `jewzaam/gh-pulls-summary` repository as test data
- Tests against known pull requests (#1, #2, #3)
- Validates real-world scenarios

## Running Integration Tests

### Prerequisites
- Network connection
- Access to GitHub API (no token required, but rate limited)

### Running the Tests

```bash
# Run only integration tests
make test-integration

# Run both unit and integration tests
make test-all

# Run integration tests directly
RUN_INTEGRATION_TESTS=1 python -m unittest discover -s integration_tests -v

# Run with pytest (if you have it installed)
RUN_INTEGRATION_TESTS=1 python -m pytest integration_tests/test_integration.py -v
```

### Environment Variables

- `RUN_INTEGRATION_TESTS`: Set to `1`, `true`, or `yes` to enable integration tests
- `GITHUB_TOKEN`: Optional GitHub token for higher rate limits (not required)

## Test Categories

### 1. GitHub API Integration (`TestGitHubApiIntegration`)
Tests individual API functions:
- `test_fetch_pull_requests_real_repo()`: Fetches all PRs from real repo
- `test_fetch_single_pull_request_real_repo()`: Fetches a specific PR
- `test_fetch_pr_files_real_repo()`: Fetches files changed in a PR
- `test_fetch_user_details_real_user()`: Fetches user information
- `test_fetch_issue_events_real_repo()`: Fetches PR events
- `test_fetch_reviews_real_repo()`: Fetches PR reviews

### 2. End-to-End Integration (`TestEndToEndIntegration`)
Tests complete workflows:
- `test_fetch_and_process_pull_requests_real_repo()`: Full PR processing
- `test_single_pr_processing_real_repo()`: Single PR processing
- `test_draft_filter_real_repo()`: Draft filtering functionality
- `test_generate_markdown_output_real_repo()`: Markdown generation

### 3. Real-World Scenarios (`TestRealWorldScenarios`)
Tests practical usage:
- `test_git_metadata_detection()`: Git repository detection
- `test_url_extraction_real_repo()`: URL extraction from PR content
- `test_sort_functionality_real_repo()`: Different sorting options

### 4. Error Handling (`TestRateLimitingAndErrors`)
Tests error conditions:
- `test_nonexistent_repo_error_handling()`: Invalid repository handling
- `test_nonexistent_pr_error_handling()`: Invalid PR number handling
- `test_rate_limit_awareness()`: Multiple requests without rate limiting

## Best Practices

### Writing Integration Tests
1. **Be mindful of rate limits**: Add delays between requests
2. **Use real data**: Test against actual repository data
3. **Validate data structure**: Ensure real API responses match expectations
4. **Handle failures gracefully**: Account for network issues and API changes

### Test Data
- **Known PRs**: Tests reference specific PR numbers that exist in the test repository
- **Flexible assertions**: Tests adapt to changing PR states (reviews, approvals, etc.)
- **Structure validation**: Focus on data structure rather than exact values

### CI/CD Considerations
- Integration tests are **optional** in CI/CD pipelines
- Can be run separately from unit tests
- Should be run less frequently due to rate limits
- Consider using GitHub tokens in CI for higher rate limits

## Rate Limiting

### Without GitHub Token
- **60 requests per hour** for unauthenticated requests
- Tests include delays to avoid hitting limits
- Suitable for development and occasional testing

### With GitHub Token
- **5,000 requests per hour** for authenticated requests
- Set `GITHUB_TOKEN` environment variable
- Recommended for CI/CD environments

## Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**
   - Wait for the rate limit to reset (check GitHub API headers)
   - Add `GITHUB_TOKEN` to your environment
   - Increase delays between tests

2. **Network Errors**
   - Check internet connection
   - Verify GitHub API accessibility
   - Consider proxy settings if needed

3. **Test Failures Due to Data Changes**
   - PRs in the test repository may change over time
   - Reviews and approvals may be added/removed
   - Tests focus on structure validation rather than exact values

### Debug Mode
Run tests with debug logging:
```bash
RUN_INTEGRATION_TESTS=1 python -m unittest tests.test_integration -v --debug
```

## Maintenance

### Updating Test Data
- If PRs in the test repository are closed/merged, update `KNOWN_PR_NUMBERS`
- Create new test PRs if needed
- Update expectations based on repository changes

### Adding New Tests
- Follow the existing pattern for rate limiting
- Use the `IntegrationTestBase` class
- Add appropriate delays between API calls
- Focus on structural validation over exact values

## Security Considerations

- Never commit GitHub tokens to version control
- Use environment variables for sensitive data
- Integration tests should work without tokens
- Consider using dedicated test repositories for sensitive projects 