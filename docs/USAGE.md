# Usage

## Basic Usage

```bash
# Run against a repository
gh-pulls-summary --owner microsoft --repo vscode

# With authentication for private repos or higher rate limits
GITHUB_TOKEN=<your_token> gh-pulls-summary --owner myorg --repo myrepo
```

If run from within a git repository, `--owner` and `--repo` default to the current remote origin.

## CLI Options

Run `gh-pulls-summary --help` for the full list. Key options:

### GitHub Options

| Option | Description |
| --- | --- |
| `--owner` | Repository owner (defaults to current git config) |
| `--repo` | Repository name (defaults to current git config) |
| `--github-token` | GitHub personal access token (or `GITHUB_TOKEN` env var) |
| `--pr-number` | Query a single PR by number |
| `--draft-filter` | Filter by draft status (`only-drafts` or `no-drafts`) |
| `--review-requested-for` | Filter PRs where review is requested for a specific user |
| `--file-include` | Regex to include PRs by changed files (repeatable) |
| `--file-exclude` | Regex to exclude PRs by changed files (repeatable) |
| `--url-from-pr-content` | Regex to extract URLs from PR diffs |

### Output Options

| Option | Description |
| --- | --- |
| `--output-markdown` | Write output to file (prints to stdout if not set) |
| `--column-title` | Override column titles, format: `COLUMN=TITLE` (repeatable) |
| `--sort-column` | Sort by column: `date`, `title`, `author`, `changes`, `approvals`, `urls`, `rank` |
| `--debug` | Enable debug logging |

### JIRA Options

See [JIRA Integration](JIRA.md) for full details.

| Option | Description |
| --- | --- |
| `--jira-url` | JIRA instance base URL (or `JIRA_BASE_URL` env var) |
| `--jira-user` | JIRA user email for Basic Auth (or `JIRA_USER` env var) |
| `--jira-token` | JIRA API token (or `JIRA_TOKEN` env var) |
| `--jira-rank-field` | Explicit Rank field ID (auto-discovered if not set) |
| `--include-rank` | Add JIRA rank column to output |
| `--jira-issue-pattern` | Regex to extract issue keys (repeatable) |
| `--jira-include` | Always include a specific JIRA issue (repeatable) |
| `--jira-metadata-row-pattern` | Regex for metadata table row identification |
| `--jira-metadata-row-search-depth` | Lines to search for metadata (default: 50, -1 for all) |

## Examples

```bash
# Filter to non-draft PRs only
gh-pulls-summary --owner myorg --repo myrepo --draft-filter no-drafts

# Filter PRs where review is requested for a specific user
gh-pulls-summary --owner myorg --repo myrepo --review-requested-for username

# Extract URLs and save to file
gh-pulls-summary --owner myorg --repo myrepo \
  --url-from-pr-content 'https://example.com/[^\s]+' \
  --output-markdown /tmp/summary.md

# Custom column titles and sorting
gh-pulls-summary --owner myorg --repo myrepo \
  --column-title date="Ready Date" \
  --column-title approvals="Approval Count" \
  --sort-column approvals

# Filter by changed files
gh-pulls-summary --owner myorg --repo myrepo \
  --file-include '.*\.py$' \
  --file-exclude 'test_.*\.py$'

# JIRA integration - extract issue keys and show rank
gh-pulls-summary --owner myorg --repo myrepo \
  --jira-url https://yourorg.atlassian.net \
  --jira-user you@example.com \
  --jira-token your_token \
  --jira-issue-pattern '(PROJECT-\d+)' \
  --include-rank \
  --sort-column rank
```

## Output Format

The tool outputs a Markdown table:

```markdown
| Date       | Title                                   | Author           | Change Requested | Approvals |
| ---------- | --------------------------------------- | ---------------- | ---------------- | --------- |
| 2025-05-01 | Add feature X #[123](https://github...) | [John](https...) | 1                | 2 of 3    |
| 2025-05-02 | Fix bug Y #[124](https://github...)     | [Jane](https...) | 0                | 1 of 1    |
```

Column titles and sort order can be customized via `--column-title` and `--sort-column`.
