# Development

## Requirements

- Python 3.10 or later
- Dependencies managed via `requirements.txt` and `requirements-dev.txt`

## Environment Setup

```bash
make venv              # Create virtual environment
make requirements      # Install runtime dependencies
make requirements-dev  # Install all dependencies (runtime + dev)
make install-package   # Install package in editable mode
make clean             # Remove temporary files and artifacts
```

## Testing

### Unit Tests
- No network connections, fully mocked dependencies
- Run with `make test-unit`

### Integration Tests
- Tests against actual GitHub repositories
- Handles GitHub API rate limits automatically
- See [Integration Tests](INTEGRATION_TESTS.md) for details

```bash
make test              # Run all tests (unit + integration)
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only
make coverage          # Run tests with coverage report and threshold check
make coverage-report   # Generate coverage report without threshold
```

Integration tests work without authentication but are rate-limited to 60 requests/hour. Set `GITHUB_TOKEN` for faster testing.

## Code Quality

```bash
make default           # Run all validation steps (format, lint, typecheck, test, coverage)
make lint              # Run linting (ruff)
make typecheck         # Run type checking (mypy)
make format            # Format code with ruff
```

Configuration is in `pyproject.toml`:
- Line length: 88 characters
- Python target: 3.10+
- 90% coverage threshold

## Continuous Integration

GitHub Actions workflows:

| Workflow | Purpose |
| --- | --- |
| `test.yml` | Runs tests on Python 3.10, 3.11, 3.12 |
| `lint.yml` | Checks code quality with ruff |
| `typecheck.yml` | Runs mypy static type checking |
| `format.yml` | Verifies code formatting with ruff |
| `coverage.yml` | Enforces 90% coverage threshold |

All workflows run on PRs and pushes to `main`. CI runs only unit tests due to GitHub API rate limiting.

## Project Structure

```
gh-pulls-summary/
├── src/gh_pulls_summary/
│   ├── __init__.py           # Package metadata and version
│   ├── main.py               # Core application logic
│   └── jira_client.py        # JIRA REST API client
├── tests/
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests (real API calls)
├── make/                     # Modular Makefile components
│   ├── common.mk
│   ├── env.mk
│   ├── lint.mk
│   ├── test.mk
│   └── typecheck.mk
├── .github/workflows/        # CI/CD
├── docs/                     # Documentation
├── Makefile                  # Build automation
├── pyproject.toml            # Python project config
├── requirements.txt          # Runtime dependencies
└── requirements-dev.txt      # Development dependencies
```
