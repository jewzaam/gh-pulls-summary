# GitHub Pull Requests Summary Tool

[![Test](https://github.com/jewzaam/gh-pulls-summary/workflows/Test/badge.svg)](https://github.com/jewzaam/gh-pulls-summary/actions/workflows/test.yml)
[![Lint](https://github.com/jewzaam/gh-pulls-summary/workflows/Lint/badge.svg)](https://github.com/jewzaam/gh-pulls-summary/actions/workflows/lint.yml)
[![Coverage Check](https://github.com/jewzaam/gh-pulls-summary/workflows/Coverage%20Check/badge.svg)](https://github.com/jewzaam/gh-pulls-summary/actions/workflows/coverage.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A CLI tool that fetches open pull requests from a GitHub repository and generates a Markdown summary table. Supports filtering by draft status, reviewer, and changed files. Optionally integrates with JIRA to rank PRs by issue priority.

## Features

- Fetch and summarize open PRs from any GitHub repository
- Filter by draft status, requested reviewer, or changed file paths
- Extract URLs from PR diffs using regex
- Optional JIRA integration with rank-based sorting and hierarchy traversal
- Customizable Markdown table output with configurable columns and sort order

## Quick Start

### Using uvx (no install required)

```bash
# Run against a public repository
uvx --from git+https://github.com/jewzaam/gh-pulls-summary gh-pulls-summary \
  --owner microsoft --repo vscode

# With authentication for private repos or higher rate limits
GITHUB_TOKEN=$(gh auth token) uvx --from git+https://github.com/jewzaam/gh-pulls-summary gh-pulls-summary \
  --owner myorg --repo myrepo
```

Requires [uv](https://github.com/astral-sh/uv#installation).

### Local Installation

```bash
git clone https://github.com/jewzaam/gh-pulls-summary.git
cd gh-pulls-summary
make requirements-dev
make install-package
.venv/bin/gh-pulls-summary --help
```

### Example Output

```markdown
| Date       | Title                                   | Author           | Change Requested | Approvals |
| ---------- | --------------------------------------- | ---------------- | ---------------- | --------- |
| 2025-05-01 | Add feature X #[123](https://github...) | [John](https...) | 1                | 2 of 3    |
| 2025-05-02 | Fix bug Y #[124](https://github...)     | [Jane](https...) | 0                | 1 of 1    |
```

## Documentation

| Topic | Description |
| --- | --- |
| [Usage](docs/USAGE.md) | Full CLI options, examples, and output format |
| [JIRA Integration](docs/JIRA.md) | JIRA rank-based sorting, hierarchy traversal, and configuration |
| [Authentication](docs/AUTHENTICATION.md) | GitHub and JIRA token setup, secure storage options |
| [Development](docs/DEVELOPMENT.md) | Testing, code quality, CI/CD, and project structure |
| [Integration Tests](docs/INTEGRATION_TESTS.md) | Running integration tests against live APIs |

## Contributing

```bash
# Set up environment
make requirements-dev
make install-package

# Run all checks
make default

# Or run individually
make test-unit         # Unit tests (no token required)
make lint              # Linting
make typecheck         # Type checking
make format            # Code formatting
make coverage          # Coverage check (90% threshold)
```

Integration tests require a `GITHUB_TOKEN` with `repo` scope. See [Authentication](docs/AUTHENTICATION.md) for setup.

All PRs must pass CI checks (test, lint, typecheck, format, coverage) before merging.
