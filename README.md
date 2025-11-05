# GitHub Pull Requests Summary Tool

[![Test](https://github.com/jewzaam/gh-pulls-summary/workflows/Test/badge.svg)](https://github.com/jewzaam/gh-pulls-summary/actions/workflows/test.yml)
[![Lint](https://github.com/jewzaam/gh-pulls-summary/workflows/Lint/badge.svg)](https://github.com/jewzaam/gh-pulls-summary/actions/workflows/lint.yml)
[![Coverage Check](https://github.com/jewzaam/gh-pulls-summary/workflows/Coverage%20Check/badge.svg)](https://github.com/jewzaam/gh-pulls-summary/actions/workflows/coverage.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A tool to fetch and summarize GitHub pull requests from a specified repository. Outputs data in Markdown table format for easy integration into documentation and reports.

---

## About This Project's Creation

This repository, including all code, tests, and documentation, was created with the assistance of GitHub Copilot and Cursor. All implementation, design, and documentation tasks involved AI-powered code generation and suggestions from these tools, but every change is carefully reviewed and manual updates are made where necessary.

---

## Features

- **PR Fetching**: Fetch pull requests from public or private repositories
- **Draft Filtering**: Filter by draft status (`only-drafts`, `no-drafts`, or no filter)
- **File Filtering**: Regex patterns to include/exclude PRs by changed file paths
- **URL Extraction**: Extract URLs from PR diffs using regex patterns
- **Flexible Output**: Markdown table format with customizable column titles and sorting
- **Comprehensive Details**:
  - Date the PR was marked ready for review
  - Title and number with links
  - Author details with links
  - Review counts and approvals

---

## 🚀 Quick Start

### Using uvx (No Installation Required)

The fastest way to try the tool:

```bash
# Get help
uvx --from git+https://github.com/jewzaam/gh-pulls-summary gh-pulls-summary --help

# Run against a public repository
uvx --from git+https://github.com/jewzaam/gh-pulls-summary gh-pulls-summary --owner jewzaam --repo gh-pulls-summary

# Run with authentication for private repos or higher rate limits
GITHUB_TOKEN=<your_token> uvx --from git+https://github.com/jewzaam/gh-pulls-summary gh-pulls-summary --owner myorg --repo myrepo
```

**Note**: Requires `uvx` (part of the `uv` Python packaging tool). See [uv installation instructions](https://github.com/astral-sh/uv#installation).

### Local Installation

```bash
# Clone the repository
git clone https://github.com/jewzaam/gh-pulls-summary.git
cd gh-pulls-summary

# Set up development environment (creates venv, installs dependencies)
make requirements-dev

# Install the package in editable mode
make install-package

# Verify installation
.venv/bin/gh-pulls-summary --help
```

---

## 📋 Requirements

- Python 3.10 or later
- Dependencies managed via `requirements.txt` and `requirements-dev.txt`

---

## 📁 Project Structure

```
gh-pulls-summary/
├── src/
│   └── gh_pulls_summary/        # Main package
│       ├── __init__.py           # Package metadata
│       └── main.py               # Application entry point
├── tests/
│   ├── unit/                     # Unit tests (96% coverage)
│   └── integration/              # Integration tests
├── make/                         # Modular Makefile components
│   ├── common.mk                 # Shared variables and constants
│   ├── env.mk                    # Environment setup
│   ├── lint.mk                   # Linting and formatting
│   └── test.mk                   # Testing targets
├── .github/
│   └── workflows/                # GitHub Actions CI/CD
│       ├── test.yml              # Test workflow
│       ├── lint.yml              # Lint workflow
│       └── coverage.yml          # Coverage check workflow
├── docs/                         # Documentation
├── Makefile                      # Main build file
├── pyproject.toml               # Python project configuration
├── requirements.txt             # Runtime dependencies
└── requirements-dev.txt         # Development dependencies
```

---

## 🛠️ Development

### Make Targets

Run `make help` to see all available targets. Key commands:

#### Environment Setup
```bash
make venv              # Create virtual environment
make requirements      # Install runtime dependencies
make requirements-dev  # Install all dependencies (runtime + dev)
make install-package   # Install package in editable mode
make clean             # Remove temporary files and artifacts
```

#### Testing
```bash
make test              # Run all tests (unit + integration)
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only
make coverage          # Run tests with coverage report and threshold check
make coverage-report   # Generate coverage report without threshold
```

#### Code Quality
```bash
make lint              # Run linting (ruff + mypy)
make format            # Format code with ruff
```

### Continuous Integration

The project uses GitHub Actions for CI/CD:

- **Test Workflow**: Runs tests on Python 3.10, 3.11, and 3.12
- **Lint Workflow**: Checks code quality with ruff and mypy
- **Coverage Workflow**: Enforces 90% coverage threshold

All workflows run on PRs and pushes to `main`.

---

## 📖 Usage

### Basic Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Run against a repository
gh-pulls-summary --owner microsoft --repo vscode
```

### Options

- `--owner`: Repository owner (defaults to current git config)
- `--repo`: Repository name (defaults to current git config)
- `--pr-number`: Query a single PR by number
- `--draft-filter`: Filter by draft status (`only-drafts` or `no-drafts`)
- `--file-include`: Regex pattern to include PRs by changed files (repeatable)
- `--file-exclude`: Regex pattern to exclude PRs by changed files (repeatable)
- `--url-from-pr-content`: Regex to extract URLs from PR diffs
- `--output-markdown`: Write output to file
- `--column-title`: Override column titles (format: `COLUMN=TITLE`)
- `--sort-column`: Sort by column (`date`, `title`, `author`, `changes`, `approvals`, `urls`)
- `--debug`: Enable debug logging

### Examples

```bash
# Filter to non-draft PRs only
gh-pulls-summary --owner myorg --repo myrepo --draft-filter no-drafts

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
```

---

## 🔐 Authentication

### Public Repositories

Works without authentication but is rate-limited to **60 requests/hour**.

### Private Repositories

Requires a GitHub Personal Access Token:

1. **Create a classic GitHub Token**:
   - Visit [Tokens (classic)](https://github.com/settings/tokens)
   - Select "Generate new token (classic)"
   - Check the `repo` scope
   - See [GitHub documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

2. **Set the Token**:
   ```bash
   export GITHUB_TOKEN=<your_personal_access_token>
   ```

3. **Run the Tool**:
   ```bash
   gh-pulls-summary --owner myorg --repo private-repo
   ```

With authentication, you get **5,000 requests/hour**.

### Secure Token Management

#### Environment Variables
```bash
# Linux/macOS
export GITHUB_TOKEN=<your_token>

# Windows (PowerShell)
$env:GITHUB_TOKEN="<your_token>"
```

#### .env Files
Create a `.env` file (already in `.gitignore`):
```env
GITHUB_TOKEN=<your_personal_access_token>
```

Load it:
```bash
# Linux/macOS
source .env

# Windows (PowerShell)
Get-Content .env | ForEach-Object { $name, $value = $_ -split '='; $env:$name = $value }
```

#### System Keyring

**Linux** (using `secret-tool`):
```bash
# Store
secret-tool store --label="GitHub Token" service gh-pulls-summary

# Use
GITHUB_TOKEN=$(secret-tool lookup service gh-pulls-summary) gh-pulls-summary --owner myorg --repo myrepo
```

**macOS** (using Keychain):
```bash
# Store
security add-generic-password -a "gh-pulls-summary" -s "GitHub Token" -w <your_token>

# Use
GITHUB_TOKEN=$(security find-generic-password -a "gh-pulls-summary" -s "GitHub Token" -w) gh-pulls-summary --owner myorg --repo myrepo
```

**Windows** (using SecretManagement):
```powershell
# Install and setup
Install-Module -Name Microsoft.PowerShell.SecretManagement -Force
Register-SecretVault -Name MySecretVault -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault

# Store
Set-Secret -Name GitHubToken -Secret "<your_token>"

# Use
$env:GITHUB_TOKEN = Get-Secret -Name GitHubToken
gh-pulls-summary --owner myorg --repo myrepo
```

---

## 🧪 Testing

This project includes comprehensive testing:

### Unit Tests
- **Fast**: No network connections, mocked dependencies
- **96% code coverage**: Comprehensive coverage of all core functionality
- **Default**: Run with `make test-unit`

### Integration Tests
- **Real API testing**: Tests against actual GitHub repositories
- **Rate limit aware**: Handles GitHub API rate limits automatically
- **Two-tier approach**: Basic and full test suites

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run with coverage
make coverage

# Generate coverage report only (no threshold check)
make coverage-report
```

**Note**: Integration tests work without authentication but are rate-limited to 60 requests/hour. For faster testing, set a `GITHUB_TOKEN` environment variable.

For detailed information, see [`docs/INTEGRATION_TESTS.md`](docs/INTEGRATION_TESTS.md).

---

## 📏 Code Quality

The project uses modern Python tooling:

- **ruff**: Fast linter and formatter (replaces black, isort, flake8)
- **mypy**: Static type checking
- **pytest**: Testing framework with coverage reporting

Configuration is in `pyproject.toml` with sensible defaults:
- Line length: 88 characters
- Python target: 3.10+
- 90% coverage threshold

```bash
# Check code quality
make lint

# Format code
make format
```

---

## 🤝 Contributing

### Development Workflow

```bash
# Set up environment
make requirements-dev
make install-package

# Set GitHub token for integration tests (REQUIRED)
export GITHUB_TOKEN=your_github_token_here

# Make changes
# ...

# Check quality before committing
make lint test coverage

# Format code
make format
```

**⚠️ Important**: Integration tests require a GitHub personal access token. Without it, tests will fail due to rate limiting (60 requests/hour). With a token, you get 5000 requests/hour.

To create a token:
1. Go to https://github.com/settings/tokens
2. Generate a new token (classic) with `repo` scope
3. Set it: `export GITHUB_TOKEN=your_token_here`

To run only unit tests (no token required):
```bash
make test-unit
```

### Pull Request Process

All PRs must pass:
- **Unit Tests**: 80% coverage requirement (automated in CI)
- **Linting**: ruff and mypy checks (automated in CI)
- **Coverage Check**: 80% threshold enforcement (automated in CI)

**Note**: CI runs only unit tests due to GitHub API rate limiting. Integration tests should be run locally with a GitHub token before submitting PRs.

Branch protection requires status checks to pass before merging.

---

## 📄 Output Format

The tool outputs a Markdown table:

```markdown
| Date 🔽    | Title                                   | Author          | Change Requested | Approvals |
| ---------- | --------------------------------------- | --------------- | ---------------- | --------- |
| 2025-05-01 | Add feature X #[123](https://github...) | [John](https...) | 1                | 2 of 3    |
| 2025-05-02 | Fix bug Y #[124](https://github...)     | [Jane](https...) | 0                | 1 of 1    |
```

Column titles and sort order can be customized via command-line options.

---

## 📚 Additional Resources

- [GitHub API Documentation](https://docs.github.com/en/rest)
- [pytest Documentation](https://docs.pytest.org/)
- [ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)

---

**Happy coding! 🎉**
