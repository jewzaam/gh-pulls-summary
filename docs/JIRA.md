# JIRA Integration

The tool can optionally fetch JIRA issue metadata and display rank information in the output, enabling priority-based PR sorting.

## Setup

Uses Atlassian Cloud Basic Auth (email + API token):

```bash
# Environment variables (recommended)
export JIRA_BASE_URL="https://yourorg.atlassian.net"
export JIRA_USER="you@example.com"
export JIRA_TOKEN="your_api_token"

# Or use command-line arguments
gh-pulls-summary --jira-url https://yourorg.atlassian.net \
  --jira-user you@example.com \
  --jira-token your_token \
  --include-rank ...
```

All three (URL, user, token) are required when `--include-rank` is specified. The tool exits with an error if JIRA is not properly configured when rank is requested.

## Usage

Enable rank column with `--include-rank`:

```bash
gh-pulls-summary --owner myorg --repo myrepo \
  --file-include 'path/to/proposals/' \
  --jira-issue-pattern '(PROJECT-\d+)' \
  --include-rank \
  --sort-column rank
```

Always include specific JIRA issues (useful for ranking reference points):

```bash
gh-pulls-summary --owner myorg --repo myrepo \
  --include-rank \
  --jira-include PROJECT-100 \
  --jira-include PROJECT-200
```

## How It Works

1. **Extracts JIRA issue keys from PR files** (priority order):
   - PR body metadata table matching `--jira-metadata-row-pattern`
   - File content metadata tables (depth controlled by `--jira-metadata-row-search-depth`)
   - Full content of files matching `--file-include` patterns
   - Uses `--jira-issue-pattern` regex to extract issue keys (supports multiple patterns)
2. **Batch fetches metadata** for all discovered issues via the v3 search/jql endpoint
3. **Hierarchy traversal**: If a referenced issue is not a Feature/Initiative, traverses the JIRA hierarchy upward to find an ancestor Feature/Initiative with a rank
4. **Filters issues** by type (Feature, Initiative) and prefers open issues (New, Backlog, In Progress, Refinement)
5. **Closed issue fallback**: If no open Feature/Initiative is found, falls back to closed issues (displayed with strikethrough)
6. **Selects highest priority** (lowest lexicographic rank) if multiple issues match
7. **Displays rank** in RANK column with issue key appended

## JIRA Options Reference

| Option | Description | Default |
| --- | --- | --- |
| `--jira-url` | JIRA instance base URL | `JIRA_BASE_URL` env var |
| `--jira-user` | User email for Basic Auth | `JIRA_USER` env var |
| `--jira-token` | API token | `JIRA_TOKEN` env var |
| `--jira-rank-field` | Explicit Rank field ID | Auto-discovered |
| `--include-rank` | Enable JIRA rank column | Disabled |
| `--jira-issue-pattern` | Regex to extract issue keys (repeatable) | None |
| `--jira-include` | Always include this issue (repeatable) | None |
| `--jira-metadata-row-pattern` | Regex for metadata table row | `feature\s*/?\\s*initiative` |
| `--jira-metadata-row-search-depth` | Lines to search for metadata | 50 (-1 for all) |

## Notes

- **Authentication**: Uses Atlassian Cloud Basic Auth (email:api_token)
- **Rank format**: `<rank_value> <issue_key>` (e.g., `0_i00ywg:9 PROJECT-123`)
- **Rank sorting**: Lexicographically sorted (lower = higher priority)
- **Pipe replacement**: Pipe characters in rank values are replaced with underscores for markdown compatibility
- **Hierarchy traversal**: Non-Feature/Initiative issues are traversed upward to find an ancestor with rank
- **Closed fallback**: If no open issues have ranks, closed issues are used (with strikethrough in output)
- **Batch fetching**: Issues are fetched in a single batch request for efficiency
- **Issue caching**: Issue data is cached to avoid redundant API calls during hierarchy traversal
- **Metadata priority**: PR body metadata > file metadata > full file content search
- **Error handling**: Individual issue fetch failures are logged but don't stop processing
