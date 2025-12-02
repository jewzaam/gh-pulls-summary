# gh-pulls-summary - Project Context

**Last Updated**: 2024-11-05

## Overview

`gh-pulls-summary` is a command-line tool that fetches and summarizes open pull requests from GitHub repositories. It generates Markdown tables with comprehensive PR information including review status, author details, and optional JIRA issue rank data.

### Primary Use Case

Generate weekly/monthly PR summary reports for team meetings, documentation, or tracking purposes. Particularly useful for organizations that track work via JIRA issues referenced in GitHub PRs.

### Key Design Principles

1. **CLI-First**: Designed for automation and scripting
2. **Markdown Output**: Easy integration into documentation systems
3. **Flexible Filtering**: Multiple ways to filter PRs (draft status, file patterns, etc.)
4. **Optional Integrations**: JIRA integration is completely optional
5. **High Test Coverage**: 96%+ unit test coverage for reliability

---

## Core Functionality

### GitHub Integration

**What it does**:
- Fetches all open pull requests from a specified GitHub repository
- Retrieves detailed PR information including:
  - Title, number, URL
  - Author name and profile link
  - Date marked ready for review (or created date)
  - Review counts and approval status
  - Change request counts
  - Files changed (for filtering)
  - PR diff content (for URL extraction)

**Authentication**:
- Works without authentication (60 requests/hour rate limit)
- Supports GitHub Personal Access Token (5000 requests/hour):
  - Command-line argument: `--github-token`
  - Environment variable: `GITHUB_TOKEN`
  - CLI argument takes precedence over environment variable
- Compatible with both public and private repositories

**API Usage**:
- Uses GitHub REST API v3
- Implements automatic rate limit retry with exponential backoff
- Handles pagination for large result sets
- Includes comprehensive error handling

### PR Filtering

Multiple filtering options available:

1. **Draft Status Filtering** (`--draft-filter`)
   - `only-drafts`: Show only draft PRs
   - `no-drafts`: Exclude draft PRs
   - Default: Show all PRs

2. **File Pattern Filtering** (`--file-include`, `--file-exclude`)
   - Filter PRs based on changed file paths
   - Uses regex patterns
   - Multiple patterns can be specified
   - Include/exclude logic: PR must match include AND not match exclude

3. **Single PR Query** (`--pr-number`)
   - Fetch details for a specific PR number only

4. **URL Extraction** (`--url-from-pr-content`)
   - Extract URLs from PR diff using regex pattern
   - Only searches added lines (lines starting with `+`)
   - Displays extracted URLs in separate column
   - URLs sorted alphabetically by display text

### Output Generation

**Markdown Table Format**:
- Date (ready for review or created)
- Title with PR number and GitHub link
- Author name with profile link
- Change requests count
- Approvals (X of Y format)
- Optional: Extracted URLs column
- Optional: JIRA rank column

**Customization Options**:
- Custom column titles (`--column-title`)
- Sortable by any column (`--sort-column`)
- Output to file (`--output-markdown`) or stdout
- Includes timestamp and generator attribution

**Example Output**:
```markdown
| Date 🔽 | Title | Author | ∆ | +1s | URLs | RANK |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-09-29 | Feature X #[123](url) | [John](url) | 1 | 4 of 7 | [ANSTRAT-1660](url) | 0_i00ywg:9 |
```

---

## JIRA Integration

### Purpose

Optionally fetch JIRA issue metadata (specifically rank information) to support priority-based PR sorting and filtering.

### How It Works

When `--include-rank` flag is enabled:
1. **Extracts JIRA issue keys**:
   - First checks PR metadata table (first 50 lines) for `Feature / Initiative` row (case-insensitive)
   - Extracts **all** matching issues from the metadata row (not just first match)
   - Falls back to searching full content of files matching `--file-include` patterns
   - Uses `--jira-issue-pattern` regex to extract issue keys (supports multiple patterns)
2. **Fetches metadata** for each JIRA issue via REST API
3. **Filters issues** by:
   - Issue type: Only Feature and Initiative
   - Status: Only New, Backlog, In Progress, or Refinement
4. **Selects highest priority** rank (lowest lexicographic value) if multiple issues match
5. **Formats rank value** for markdown display (replaces pipes with underscores, appends issue key)
6. **Adds RANK column** to output table (format: `<rank> <issue_key>`)
7. **Supports sorting** by rank

### JIRA Client

**Location**: `src/gh_pulls_summary/jira_client.py`

**Features**:
- Standalone REST API client (no external dependencies)
- Automatic rank field discovery (looks for `customfield_12311940` or similar)
- Token-based authentication (Bearer token)
- Field ID caching to minimize API calls
- Comprehensive error handling with custom exceptions

**Authentication**:
- Token-based authentication only (Bearer token)
- JIRA URL:
  - Command-line argument: `--jira-url`
  - Environment variable: `JIRA_BASE_URL`
  - CLI argument takes precedence over environment variable
- JIRA Token:
  - Command-line argument: `--jira-token`
  - Environment variable: `JIRA_TOKEN`
  - CLI argument takes precedence over environment variable
- Both URL and token are required when `--include-rank` is specified
- Tool will fail execution if rank is requested but JIRA is not properly configured

### Rank Field Handling

**JIRA Rank Semantics**:
- Rank values are lexicographically sortable strings
- Lower lexicographic value = higher priority
- Example values: `0|i00ywg:9` (high) vs `0|i00ywl:3i` (lower)
- Empty/null ranks treated as lowest priority

**Issue Type Filtering**:
- Only includes: Feature, Initiative
- Excludes: Outcome, and all other types
- Rationale: Only certain issue types have meaningful rank ordering

**Status Filtering**:
- Only includes issues with status: New, Backlog, In Progress, Refinement
- Excludes: Release Pending, Released, Closed, and all other statuses
- Rationale: Only active issues should be considered for ranking

**JIRA Issue Extraction**:
- **Priority 1**: Checks PR metadata table (first 50 lines) for `Feature / Initiative` row (case-insensitive)
  - Extracts **all** matching issues from metadata row (not just first)
- **Priority 2**: If not found in metadata, searches full content of files matching `--file-include`
- Uses `--jira-issue-pattern` regex to extract issue keys (supports multiple patterns via `action="append"`)

**Multiple Issues Per PR**:
- If PR references multiple JIRA issues (from file contents or metadata)
- Tool fetches metadata for all issues
- Filters by type (Feature/Initiative) and status (New/Backlog/In Progress/Refinement)
- Selects issue with highest priority (lowest lexicographic rank)
- Displays that rank with issue key appended in RANK column

**Rank Display Format**:
- Original rank: `0|i00ywg:9` for issue `ANSTRAT-1579`
- Displayed rank: `0_i00ywg:9 ANSTRAT-1579`
- Pipe characters (`|`) replaced with underscores to prevent breaking table formatting
- Issue key appended for transparency

### Configuration

**Command-Line Arguments**:
```bash
--jira-url <url>                  # JIRA instance base URL
--jira-token <token>              # JIRA API token (Bearer token)
--include-rank                    # Enable JIRA rank column
--jira-issue-pattern <regex>      # Regex to extract issue keys (default: ANSTRAT-\d+)
```

**Environment Variables**:
```bash
JIRA_BASE_URL=https://issues.redhat.com
JIRA_TOKEN=mytoken
```

### Error Handling

**Hard Failure on Configuration Issues**:
- If `--include-rank` is specified but JIRA is not properly configured, execution fails immediately
- Missing JIRA URL: Tool exits with error message
- Missing JIRA token: Tool exits with error message
- JIRA connection test failure: Tool exits with error message

**Rationale**: Prevents misleading output where rank column is empty when user expected rank data

**Per-Issue Failures** (during processing):
- Individual JIRA API failures: Warning logged, that PR's rank is empty
- Invalid issue keys: Silently skipped
- Rate limiting: Logged as warning, rank unavailable for that PR
- Network errors: Logged as warning, rank unavailable for that PR

When `--include-rank` is NOT specified, JIRA is completely bypassed and no errors occur.

---

## Architecture

### Project Structure

```
gh-pulls-summary/
├── src/gh_pulls_summary/
│   ├── __init__.py           # Package metadata and version
│   ├── main.py               # Core application logic
│   └── jira_client.py        # JIRA REST API client
├── tests/
│   ├── unit/                 # Unit tests (98 tests, 96%+ coverage)
│   │   ├── test_main.py
│   │   ├── test_jira_client.py
│   │   ├── test_api_requests.py
│   │   ├── test_argument_parsing.py
│   │   ├── test_processing_logic.py
│   │   └── ...
│   └── integration/          # Integration tests (real API calls)
│       ├── test_integration.py
│       └── test_integration_simple.py
├── make/                     # Modular Makefile components
├── docs/                     # Documentation
├── Makefile                  # Build automation
├── pyproject.toml           # Python project config
└── requirements.txt         # Runtime dependencies
```

### Key Components

#### 1. GitHub API Client (`main.py`)

**Functions**:
- `github_api_request()`: Low-level API request handler with pagination and retry
- `fetch_pull_requests()`: Get all open PRs
- `fetch_single_pull_request()`: Get specific PR by number
- `fetch_reviews()`: Get PR review information
- `fetch_issue_events()`: Get PR events (ready_for_review, etc.)
- `fetch_user_details()`: Get author information
- `fetch_pr_files()`: Get changed files in PR
- `fetch_pr_diff()`: Get PR diff content

**Error Handling**:
- Custom exception classes: `GitHubAPIError`, `RateLimitError`, `NetworkError`
- Automatic retry with exponential backoff for rate limits
- Graceful degradation for non-critical failures

#### 2. JIRA API Client (`jira_client.py`)

**Classes**:
- `JiraClient`: Main REST API client
- `JiraClientError`: Base exception for JIRA errors
- `JiraAuthenticationError`: Authentication-specific errors

**Methods**:
- `get_issue(issue_key)`: Fetch single issue with rank field
- `get_issues_metadata(issue_keys)`: Batch fetch metadata
- `extract_rank_value(issue_data)`: Extract rank from issue data
- `get_issue_type(issue_data)`: Extract issue type
- `_discover_rank_field()`: Auto-discover rank field ID

#### 3. Data Processing Pipeline (`main.py`)

**Flow**:
1. Parse command-line arguments
2. Initialize JIRA client (if `--include-rank` specified)
3. Fetch PRs from GitHub
4. For each PR:
   - Apply draft filter
   - Apply file filters
   - Fetch review information
   - Fetch author details
   - Extract URLs from diff (if requested)
   - Fetch JIRA rank (if enabled)
5. Sort PRs by specified column
6. Generate markdown table
7. Output to file or stdout

**Data Structures**:

PR Data Dictionary:
```python
{
    "date": "2025-05-01",           # Ready for review date
    "title": "Add feature X",        # PR title
    "number": 123,                   # PR number
    "url": "https://...",            # PR URL
    "author_name": "John Doe",       # Author display name
    "author_url": "https://...",     # Author profile URL
    "reviews": 3,                    # Total review count
    "approvals": 2,                  # Approval count
    "changes": 1,                    # Change request count
    "pr_body_urls_dict": {...},      # Extracted URLs
    "rank": "0_i00ywg:9"            # JIRA rank (optional)
}
```

#### 4. Output Generation (`main.py`)

**Functions**:
- `parse_column_titles()`: Handle custom column titles
- `validate_sort_column()`: Validate sort column name
- `create_markdown_table_header()`: Generate table header
- `create_markdown_table_row()`: Generate table row for each PR
- `generate_markdown_output()`: Main output generation function
- `generate_timestamp()`: Add timestamp to output

---

## Configuration

### Command-Line Interface

**Required Arguments** (if not in git repo):
- `--owner <owner>`: Repository owner
- `--repo <repo>`: Repository name

**GitHub Options**:
- `--pr-number <num>`: Query single PR
- `--draft-filter <only-drafts|no-drafts>`: Filter by draft status
- `--file-include <regex>`: Include PRs with matching file paths (repeatable)
- `--file-exclude <regex>`: Exclude PRs with matching file paths (repeatable)
- `--url-from-pr-content <regex>`: Extract URLs from PR diffs

**JIRA Options**:
- `--jira-url <url>`: JIRA instance base URL
- `--jira-token <token>`: JIRA API token (Bearer token)
- `--include-rank`: Enable JIRA rank column
- `--jira-issue-pattern <regex>`: Pattern to extract issue keys

**Output Options**:
- `--output-markdown <file>`: Write output to file
- `--column-title <COLUMN=TITLE>`: Override column title (repeatable)
- `--sort-column <column>`: Sort by column (date, title, author, changes, approvals, urls, rank)
- `--debug`: Enable debug logging

### Environment Variables

**GitHub**:
- `--github-token` or `GITHUB_TOKEN`: GitHub Personal Access Token for authentication
  - CLI argument takes precedence over environment variable

**JIRA**:
- `--jira-url` or `JIRA_BASE_URL`: JIRA instance base URL
- `--jira-token` or `JIRA_TOKEN`: JIRA API token (Bearer token) for authentication
  - CLI arguments take precedence over environment variables

### Default Behaviors

- **Repository**: Defaults to current git repository's remote.origin.url
- **Output**: Prints to stdout if `--output-markdown` not specified
- **Sort**: Sorts by date (ascending) by default
- **Draft Filter**: Shows all PRs (drafts and non-drafts)
- **JIRA**: Disabled by default, must use `--include-rank` to enable

---

## Testing

### Unit Tests

**Coverage**: 96%+ of code

**Test Files**:
- `test_main.py`: Core application logic (39 tests)
- `test_jira_client.py`: JIRA integration (18 tests)
- `test_api_requests.py`: GitHub API calls (6 tests)
- `test_argument_parsing.py`: CLI argument parsing (5 tests)
- `test_processing_logic.py`: Data processing (10 tests)
- `test_draft_filter.py`: Draft filtering (2 tests)
- `test_file_filter.py`: File pattern filtering (3 tests)
- `test_rate_limit_retry.py`: Rate limit handling (9 tests)
- `test_error_conditions.py`: Error scenarios (14 tests)

**Testing Approach**:
- Mock all external API calls (GitHub, JIRA)
- Test error conditions and edge cases
- Verify data transformation logic
- Validate output formatting
- Check CLI argument parsing and validation

**Run Tests**:
```bash
make test-unit        # Fast, no network calls
make coverage         # With coverage report and threshold check
```

### Integration Tests

**Purpose**: Verify real API interactions

**Test Scenarios**:
- Fetch PRs from public GitHub repositories
- Handle authentication
- Process large result sets
- Handle rate limiting
- Test with real network conditions

**Run Tests**:
```bash
# Set GitHub token via environment variable
export GITHUB_TOKEN=your_token
make test-integration

# Or pass token via command-line when running the tool
```

**Note**: Integration tests disabled in CI due to rate limiting. Run locally before submitting PRs.

---

## Performance Characteristics

### GitHub API Calls

For N open PRs:
- Base: 1 call to fetch PR list
- Per PR: 3-4 calls (reviews, events, author details, optionally files/diff)
- Total: ~1 + 3N to 4N calls

**Rate Limits**:
- Without token: 60 requests/hour
- With token: 5000 requests/hour
- Automatic retry with backoff when rate limited

**Performance**:
- 100 PRs: ~2-3 minutes without caching
- Network latency is primary bottleneck

### JIRA API Calls

For N unique JIRA issues (when `--include-rank` enabled):
- Rank field discovery: 1 call (cached)
- Per issue: 1 call to fetch metadata
- Total: 1 + N calls

**Optimizations**:
- Rank field ID cached after first discovery
- Issue metadata fetched only when needed
- Duplicate JIRA references use same data

### Memory Usage

- Minimal: Processes PRs sequentially
- Stores all PR data in memory for sorting
- Typical usage: <50MB for 100 PRs

---

## Dependencies

### Runtime Dependencies (`requirements.txt`)

```
requests>=2.31.0      # HTTP client for API calls
argcomplete>=3.0.0    # Shell tab completion
```

### Development Dependencies (`requirements-dev.txt`)

```
pytest>=7.0.0         # Testing framework
pytest-cov>=4.0.0     # Coverage reporting
mypy>=1.0.0           # Static type checking
ruff>=0.1.0           # Fast linting and formatting
types-requests>=2.31.0 # Type stubs for requests
```

### Python Version

- **Minimum**: Python 3.10
- **Tested**: Python 3.10, 3.11, 3.12
- **Uses**: Type hints, modern f-strings, pattern matching (limited)

---

## Code Quality

### Linting and Formatting

**Tools**:
- **ruff**: All-in-one linter and formatter
  - Replaces: black, isort, flake8, pylint
  - Fast: Rust-based implementation
  - Configuration: `pyproject.toml`

- **mypy**: Static type checking
  - Checks type hints
  - Helps catch bugs before runtime
  - Configuration: `pyproject.toml`

**Standards**:
- Line length: 88 characters
- Target: Python 3.10+
- Type hints: Preferred but not required everywhere
- Docstrings: Required for public functions

**Run Checks**:
```bash
make lint      # Run all linters
make format    # Auto-format code
```

### CI/CD

**GitHub Actions Workflows**:

1. **Test Workflow** (`.github/workflows/test.yml`)
   - Runs on: Python 3.10, 3.11, 3.12
   - Executes: Unit tests only (integration tests too slow for CI)
   - Triggers: PRs and pushes to main

2. **Lint Workflow** (`.github/workflows/lint.yml`)
   - Runs: ruff and mypy
   - Ensures code quality
   - Triggers: PRs and pushes to main

3. **Coverage Workflow** (`.github/workflows/coverage.yml`)
   - Threshold: 90% coverage required
   - Fails if coverage drops below threshold
   - Triggers: PRs and pushes to main

**Branch Protection**:
- All status checks must pass
- Reviews required for PRs
- Cannot merge with failing tests

---

## Common Usage Patterns

### 1. Weekly Team Report

```bash
# Generate report for team standup
gh-pulls-summary \
  --owner myorg \
  --repo myrepo \
  --draft-filter no-drafts \
  --output-markdown weekly-prs-$(date +%Y-%m-%d).md
```

### 2. Track PRs by JIRA Priority

```bash
# Show PRs sorted by JIRA rank
export JIRA_BASE_URL=https://issues.redhat.com
export JIRA_TOKEN=mytoken

gh-pulls-summary \
  --owner ansible \
  --repo ansible-rulebook \
  --url-from-pr-content 'https://issues.redhat.com/browse/(ANSTRAT-\d+)' \
  --include-rank \
  --sort-column rank
```

### 3. Focus on Specific File Changes

```bash
# Show PRs that changed Python files but not tests
gh-pulls-summary \
  --owner myorg \
  --repo myrepo \
  --file-include '.*\.py$' \
  --file-exclude 'test_.*\.py$'
```

### 4. Extract Issue References

```bash
# Extract all JIRA references from PRs
gh-pulls-summary \
  --owner myorg \
  --repo myrepo \
  --url-from-pr-content 'https://jira\.example\.com/browse/([A-Z]+-[0-9]+)'
```

### 5. Custom Report Format

```bash
# Customize column titles and sorting
gh-pulls-summary \
  --owner myorg \
  --repo myrepo \
  --column-title date="Ready Date" \
  --column-title approvals="+1 Count" \
  --sort-column approvals
```

---

## Troubleshooting

### GitHub Rate Limiting

**Problem**: "Rate limit exceeded" error

**Solutions**:
1. Use `--github-token` argument or set `GITHUB_TOKEN` environment variable
2. Wait for rate limit reset (check `X-RateLimit-Reset` header)
3. Tool automatically retries after rate limit reset

### JIRA Connection Failures

**Problem**: "JIRA connection failed" warning

**Causes**:
- Missing or incorrect JIRA credentials
- JIRA instance URL incorrect
- Network connectivity issues
- JIRA instance requires authentication but none provided

**Solutions**:
1. Verify JIRA_BASE_URL is correct
2. Check JIRA_USERNAME and JIRA_TOKEN are set
3. Test JIRA credentials manually
4. Tool continues without rank data if JIRA fails

### Missing PR Data

**Problem**: PRs shown without author names or review counts

**Causes**:
- Network timeouts fetching additional data
- GitHub API rate limiting
- Private repository without proper token permissions

**Solutions**:
1. Check network connectivity
2. Verify GitHub token (via `--github-token` or `GITHUB_TOKEN`) has `repo` scope
3. Enable `--debug` flag to see detailed errors

### Empty Output

**Problem**: No PRs shown when expecting results

**Causes**:
- No open PRs in repository
- Filters excluding all PRs (draft filter, file filters)
- Repository owner/name incorrect

**Solutions**:
1. Verify repository has open PRs on GitHub
2. Remove filters temporarily to see all PRs
3. Check owner and repo arguments are correct
4. Enable `--debug` for detailed logging

---

## Maintenance Notes

### When Updating the Codebase

1. **Run tests**: `make test-unit` before committing
2. **Check coverage**: `make coverage` to verify threshold
3. **Run linting**: `make lint` to check code quality
4. **Format code**: `make format` for consistent style
5. **Update CONTEXT.md**: Document any significant changes (THIS FILE)
6. **Update README.md**: If user-facing changes
7. **Update version**: Bump version in `src/gh_pulls_summary/__init__.py`

### Adding New Features

1. **Write tests first**: TDD approach preferred
2. **Add CLI arguments**: Update `parse_arguments()` in main.py
3. **Update documentation**: README.md and CONTEXT.md
4. **Test integration**: Run integration tests locally
5. **Check CI**: Ensure all workflows pass

### JIRA Integration Maintenance

The JIRA client (`jira_client.py`) is **maintained independently** from the mcp-jira-server project. Changes to mcp-jira-server do not automatically apply here.

**If updating JIRA logic**:
1. Review changes in mcp-jira-server if applicable
2. Manually port relevant changes to this codebase
3. Update tests in `test_jira_client.py`
4. Verify JIRA integration still works
5. Document changes in this file

---

## Version History

### Current Version: 1.0.0

**Features**:
- GitHub PR fetching and summarization
- Multiple filtering options (draft, files)
- URL extraction from diffs
- JIRA rank integration
- Markdown table output
- 96%+ test coverage

**Recent Additions** (2024-11-05):
- JIRA rank field integration
- Issue type filtering (Feature/Initiative)
- Rank-based sorting
- Independent JIRA client implementation
- 18 new JIRA-specific tests

---

## Future Considerations

*Note: This section is for high-level awareness only. See PLAN.md for detailed future planning.*

**Potential Enhancements** (Not Currently Implemented):
- Caching of JIRA metadata across runs
- Batch JIRA API requests
- Additional JIRA fields (priority, status, assignee)
- PR filtering by JIRA ancestry relationships
- JSON output format option
- Configuration file support
- More detailed progress indicators

**Not Planning**:
- GUI interface (CLI-focused)
- Direct database integration
- Complex workflow automation
- JIRA ticket creation/updates

---

## Support and Resources

### Documentation
- **README.md**: User guide and quick start
- **CONTEXT.md**: This file - project context and architecture
- **docs/INTEGRATION_TESTS.md**: Integration testing guide
- **JIRA_IMPLEMENTATION_SUMMARY.md**: Detailed JIRA integration docs
- **RANK_CONTEXT.md**: JIRA rank field specifications

### External Resources
- [GitHub REST API](https://docs.github.com/en/rest)
- [JIRA REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v2/)
- [pytest Documentation](https://docs.pytest.org/)
- [ruff Documentation](https://docs.astral.sh/ruff/)

### Repository
- **GitHub**: https://github.com/jewzaam/gh-pulls-summary
- **Issues**: https://github.com/jewzaam/gh-pulls-summary/issues
- **CI/CD**: https://github.com/jewzaam/gh-pulls-summary/actions

---

**Document Maintained By**: Development team
**Review Frequency**: Update on significant feature additions or architectural changes
**Last Major Update**: 2024-11-05 (JIRA integration)

