# GitHub Pull Requests Summary Tool

[![PR Check](https://github.com/jewzaam/gh-pulls-summary/actions/workflows/pr-check.yml/badge.svg)](https://github.com/jewzaam/gh-pulls-summary/actions/workflows/pr-check.yml)

This tool fetches and summarizes pull requests from a specified GitHub repository. It outputs the data in a Markdown table format, which can be easily copied into documentation or reports.

---

## About This Project's Creation

This repository, including all code, tests, and documentation, was created with the assistance of GitHub Copilot and Cursor. All implementation, design, and documentation tasks involved AI-powered code generation and suggestions from these tools, but every change is carefully reviewed and manual updates are made where necessary. Suggestions are never taken as-is; all code and documentation are edited and refined to ensure correctness and quality.

---

## Features
- Fetch pull requests from public or private repositories.
- Filter pull requests based on draft status (`only-drafts`, `no-drafts`, or no filter).
- Outputs pull request details, including:
  - Date the pull request was marked ready for review.
  - Title and number of the pull request.
  - Author details.
  - Number of reviews and approvals.
- `--file-include` / `--file-exclude`: Regex patterns to filter PRs by changed file paths.
- `--url-from-pr-content`: Regex pattern to extract URLs from added lines in the PR diff. If set, adds a column to the output table with the matched URLs.

---

## Requirements
- Python 3.6 or later.
- See `requirements.txt`.

---

## Testing

This project includes both unit tests and integration tests:

### Unit Tests
- **Fast**: Run without network connections using mocked dependencies
- **96% code coverage**: Comprehensive test coverage of all core functionality
- **Default**: Run with `make test`

### Integration Tests
- **Real API testing**: Test against actual GitHub repositories
- **Rate limit aware**: Automatically handle GitHub API rate limits
- **Two-tier approach**: Basic and full test suites

```bash
# Run basic integration tests (recommended for development)
make test-integration

# Run full integration tests (requires higher rate limits or GitHub token)
make test-integration-full

# Run with convenience script
python run_integration_tests.py

# Run all tests (unit + integration)
make test-all
```

**Note**: Integration tests work without authentication but are rate limited to 60 requests/hour. For faster testing, set a `GITHUB_TOKEN` environment variable.

For detailed information, see [`docs/INTEGRATION_TESTS.md`](docs/INTEGRATION_TESTS.md).

---

## Table of Contents

<!--TOC-->

- [GitHub Pull Requests Summary Tool](#github-pull-requests-summary-tool)
  - [About This Project's Creation](#about-this-projects-creation)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Steps](#steps)
  - [Usage](#usage)
    - [Options](#options)
    - [Example](#example)
    - [Running Against a Public Repository (No Authentication)](#running-against-a-public-repository-no-authentication)
    - [Running Against a Private Repository (Requires Authentication)](#running-against-a-private-repository-requires-authentication)
  - [Managing GitHub Token Securely](#managing-github-token-securely)
    - [1. Use Environment Variables](#1-use-environment-variables)
      - [Linux/macOS](#linuxmacos)
      - [Windows (Command Prompt)](#windows-command-prompt)
      - [Windows (PowerShell)](#windows-powershell)
    - [2. Using `.env` Files](#2-using-env-files)
      - [Linux/macOS](#linuxmacos-1)
      - [Windows (PowerShell)](#windows-powershell-1)
    - [3. Use System Keyring](#3-use-system-keyring)
      - [Linux](#linux)
        - [Storing the Token](#storing-the-token)
        - [Retrieving and Using the Token](#retrieving-and-using-the-token)
        - [Updating the Token](#updating-the-token)
      - [macOS](#macos)
        - [Storing the Token](#storing-the-token-1)
        - [Retrieving and Using the Token](#retrieving-and-using-the-token-1)
        - [Updating the Token](#updating-the-token-1)
      - [Windows](#windows)
        - [Storing the Token](#storing-the-token-2)
        - [Retrieving and Using the Token](#retrieving-and-using-the-token-2)
        - [Updating the Token](#updating-the-token-2)
  - [Optional Arguments](#optional-arguments)
  - [Output](#output)

<!--TOC-->

## Installation

### Prerequisites
- Python 3.6 or later is required.
- Ensure you have `make` installed on your system (optional, for automated setup).

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/gh-pulls-summary.git
   cd gh-pulls-summary
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Linux/macOS:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. Install the package and its dependencies:
   ```bash
   # Option 1: Using make (if available)
   make install
   
   # Option 2: Using pip directly
   pip install -r requirements.txt
   pip install -e .
   ```

   This will:
   - Install the required dependencies listed in `requirements.txt`.
   - Install the `gh-pulls-summary` command in your virtual environment.

4. Verify the installation:
   ```bash
   gh-pulls-summary --help
   ```

   You should see the help message for the tool.

**Note**: Remember to activate the virtual environment (`source venv/bin/activate` on Linux/macOS or `venv\Scripts\activate` on Windows) each time you want to use the tool in a new terminal session.

---

## Usage

**Note**: Make sure your virtual environment is activated before running the tool:
```bash
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

Then run the tool using either:
```bash
# Option 1: Using the installed command
gh-pulls-summary [OPTIONS]

# Option 2: Running the script directly
python gh_pulls_summary.py [OPTIONS]
```

### Options

- `--owner`: The owner of the repository (e.g., 'microsoft'). If not specified, defaults to the owner from the current directory's Git config.
- `--repo`: The name of the repository (e.g., 'vscode'). If not specified, defaults to the repo name from the current directory's Git config.
- `--pr-number`: Specify a single pull request number to query.
- `--draft-filter`: Filter pull requests based on draft status. Use 'only-drafts' to include only drafts, or 'no-drafts' to exclude drafts.
- `--file-include`: Regex pattern to include pull requests based on changed file paths. Can be specified multiple times.
- `--file-exclude`: Regex pattern to exclude pull requests based on changed file paths. Can be specified multiple times.
- `--url-from-pr-content`: Regex pattern to extract all unique URLs from added lines in the PR diff. If set, adds a column to the output table with the matched URLs.
- `--output-markdown`: Path to write the generated Markdown output (with timestamp) to a file. If not set, output is printed to stdout only.
- `--debug`: Enable debug logging and show tracebacks on error.
- `--column-title`: Override the title for any output column. Format: `COLUMN=TITLE`. Valid COLUMN values: `date`, `title`, `author`, `changes`, `approvals`, `urls`. Can be specified multiple times.
- `--sort-column`: Specify which output column to sort by. Valid values: `date`, `title`, `author`, `changes`, `approvals`, `urls`. Default is `date`.

### Example

Extract all unique URLs from PR diffs, write the summary to a file, override the column titles, and sort by approvals:

```bash
# Ensure virtual environment is activated first
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

gh-pulls-summary --owner myorg --repo myrepo \
  --url-from-pr-content 'https://example.com/[^\s]+' \
  --output-markdown /tmp/summary.md \
  --column-title date="Ready Date" --column-title approvals="Total Approvals" \
  --sort-column approvals
```

If you do not specify `--output-markdown`, the Markdown summary (with timestamp) will be printed to the terminal.

### Running Against a Public Repository (No Authentication)
You can run the tool against a public repository without authentication. However, note that the GitHub API imposes a rate limit of **60 requests per hour** for unauthenticated requests.

```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

gh-pulls-summary --owner jewzaam --repo gh-pulls-summary
```

### Running Against a Private Repository (Requires Authentication)
To access private repositories or increase the API rate limit to **5,000 requests per hour**, you need to authenticate using a GitHub personal access token.

1. **Set Up a classic GitHub Token**:
   - [Tokens (classic)](https://github.com/settings/tokens)
   - Select "Generate new token" then "Generate new token (classic)"
   - Check the scope `repo`
   - For more info see [GitHub documentation on creating a personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token).   

2. **Set the Token as an Environment Variable**:
   Export the token as an environment variable:
   ```bash
   export GITHUB_TOKEN=<your_personal_access_token>
   ```

3. **Run the Tool**:
   Activate your virtual environment and use the same command as for public repositories:
   ```bash
   # Activate virtual environment first
   source venv/bin/activate  # Linux/macOS
   # or: venv\Scripts\activate  # Windows
   
   gh-pulls-summary --owner <owner> --repo <repo>
   ```

Example:
```bash
# Activate virtual environment and set token
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

export GITHUB_TOKEN=ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXX
gh-pulls-summary --owner my-org --repo private-repo
```

**NOTE**: The _classic_ scope of `repo` is required for this to work. Any other permissions have yet to work correctly. PRs are welcome to fix this in the documentation if there's another way.

---

## Managing GitHub Token Securely

Security is critical when managing your GitHub token. Tokens grant access to your repositories and should be handled with care to prevent unauthorized access. Below are instructions tailored for different operating systems to securely manage your token.

### 1. Use Environment Variables

#### Linux/macOS
Store the token in an environment variable to avoid hardcoding it in scripts or files. For example:

```bash
export GITHUB_TOKEN=<your_personal_access_token>
```

You can then use the token when running the tool:

```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

gh-pulls-summary --owner <owner> --repo <repo>
```

#### Windows (Command Prompt)
Use the `set` command to set the environment variable:

```cmd
set GITHUB_TOKEN=<your_personal_access_token>
```

Run the tool:

```cmd
REM Activate virtual environment first
venv\Scripts\activate

gh-pulls-summary --owner <owner> --repo <repo>
```

#### Windows (PowerShell)
Use the `$env:` syntax to set the environment variable:

```powershell
$env:GITHUB_TOKEN="<your_personal_access_token>"
```

Run the tool:

```powershell
# Activate virtual environment first
venv\Scripts\activate

gh-pulls-summary --owner <owner> --repo <repo>
```

### 2. Using `.env` Files
You can use a `.env` file to manage environment variables locally. Create a `.env` file:

```env
GITHUB_TOKEN=<your_personal_access_token>
```

Load the `.env` file in your shell before running the tool:

#### Linux/macOS
```bash
source .env
```

#### Windows (PowerShell)
```powershell
Get-Content .env | ForEach-Object { $name, $value = $_ -split '='; $env:$name = $value }
```

**Note**: The `.env` file is excluded in the repository's `.gitignore` file.

### 3. Use System Keyring

#### Linux
On Linux, you can use `secret-tool` to securely store and retrieve the token:

##### Storing the Token
```bash
secret-tool store --label="GitHub Token" service gh-pulls-summary
```

##### Retrieving and Using the Token
```bash
# Activate virtual environment first
source venv/bin/activate

GITHUB_TOKEN=$(secret-tool lookup service gh-pulls-summary) gh-pulls-summary --owner <owner> --repo <repo>
```

##### Updating the Token
If you need to update the token, re-run the `secret-tool store` command:

```bash
secret-tool store --label="GitHub Token" service gh-pulls-summary
```

#### macOS
On macOS, you can use the Keychain to securely store and retrieve the token:

##### Storing the Token
```bash
security add-generic-password -a "gh-pulls-summary" -s "GitHub Token" -w <your_personal_access_token>
```

##### Retrieving and Using the Token
```bash
# Activate virtual environment first
source venv/bin/activate

GITHUB_TOKEN=$(security find-generic-password -a "gh-pulls-summary" -s "GitHub Token" -w) gh-pulls-summary --owner <owner> --repo <repo>
```

##### Updating the Token
If you need to update the token, re-run the `security add-generic-password` command.

#### Windows
On Windows, you can use the SecretManagement module in PowerShell to securely store and retrieve the token:

##### Storing the Token
1. Install the SecretManagement module:
   ```powershell
   Install-Module -Name Microsoft.PowerShell.SecretManagement -Force
   ```

2. Register a vault (e.g., SecretStore):
   ```powershell
   Register-SecretVault -Name MySecretVault -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault
   ```

3. Store the token:
   ```powershell
   Set-Secret -Name GitHubToken -Secret "<your_personal_access_token>"
   ```

##### Retrieving and Using the Token
Retrieve the token and set it as an environment variable:
```powershell
# Activate virtual environment first
venv\Scripts\activate

$env:GITHUB_TOKEN = Get-Secret -Name GitHubToken
gh-pulls-summary --owner <owner> --repo <repo>
```

##### Updating the Token
To update the token, re-run the `Set-Secret` command:
```powershell
Set-Secret -Name GitHubToken -Secret "<new_personal_access_token>"
```

---

## Optional Arguments
- `--draft-filter`: Filter pull requests based on draft status.
  - `only-drafts`: Include only draft pull requests.
  - `no-drafts`: Exclude draft pull requests.
  - If not specified, all pull requests are included regardless of draft status.

Example:
```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

gh-pulls-summary --owner jewzaam --repo gh-pulls-summary --draft-filter no-drafts
```

- `--debug`: Enable debug logging to output detailed information about the script's execution.

Example:
```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

gh-pulls-summary --owner jewzaam --repo gh-pulls-summary --debug
```

---

## Output
The tool outputs a Markdown table with the following columns:
- **Date**: The date the pull request was marked ready for review.
- **Title**: The title of the pull request, with a link to the pull request.
- **Author**: The name of the author, with a link to their GitHub profile.
- **Change Requested**: The number of reviews requesting changes.
- **Approvals**: The number of approvals out of total reviews (e.g., "2 of 5").

Example Output:
````markdown
| Date 🔽    | Title                                   | Author          | Change Requested | Approvals |
| ---------- | --------------------------------------- | --------------- | ---------------- | --------- |
| 2025-05-01 | Add feature X #[123](https://github.com/...) | [John Doe](https://github.com/johndoe) | 1            | 2 of 3    |
| 2025-05-02 | Fix bug Y #[124](https://github.com/...) | [Jane Smith](https://github.com/janesmith) | 0            | 1 of 1    |
````

---

## Contributing

For local development, you can run the tests using:

```bash
make test
```

The tests include comprehensive unit tests with mocking and integration tests against real GitHub repositories.

### Pull Request Process

All pull requests must pass the automated PR check which includes:
- **Unit Tests**: Fast tests with mocked dependencies (96% code coverage)
- **Simple Integration Tests**: Real API tests against GitHub repositories
- **Coverage Report**: Automatic coverage reporting

To set up branch protection (repository admin required):
1. Go to `Settings > Branches` in your GitHub repository
2. Add rule for `main` branch with these requirements:
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Select the "test" status check from the PR Check workflow

