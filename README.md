# GitHub Pull Requests Summary Tool

This tool fetches and summarizes pull requests from a specified GitHub repository. It outputs the data in a Markdown table format, which can be easily copied into documentation or reports.

## Features
- Fetch pull requests from public or private repositories.
- Filter pull requests based on draft status (`only-drafts`, `no-drafts`, or no filter).
- Outputs pull request details, including:
  - Date the pull request was marked ready for review.
  - Title and number of the pull request.
  - Author details.
  - Number of reviews and approvals.

---

## Requirements
- Python 3.6 or later.
- `requests` library (install using `pip install requests`).

---

## Installation

### Prerequisites
- Ensure you have `make` installed on your system.
- Python 3.6 or later is required.

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/gh-pulls-summary.git
   cd gh-pulls-summary
   ```

2. Install the package and its dependencies:
   ```bash
   make install
   ```

   This will:
   - Install the required dependencies listed in `requirements.txt`.
   - Install the `gh-pulls-summary` command globally for the current user.

3. Verify the installation:
   ```bash
   gh-pulls-summary --help
   ```

   You should see the help message for the tool.

---

## Usage

### Running Against a Public Repository (No Authentication)
You can run the tool against a public repository without authentication. However, note that the GitHub API imposes a rate limit of **60 requests per hour** for unauthenticated requests.

```bash
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
   Use the same command as for public repositories:
   ```bash
   gh-pulls-summary --owner <owner> --repo <repo>
   ```

Example:
```bash
export GITHUB_TOKEN=ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXX
gh-pulls-summary --owner my-org --repo private-repo
```

**NOTE**: The _classic_ scope of `repo` is required for this to work. Any other permissions have yet to work correctly. PRs are welcome to fix this in the documentation if there's another way.

---

## Optional Arguments
- `--draft-filter`: Filter pull requests based on draft status.
  - `only-drafts`: Include only draft pull requests.
  - `no-drafts`: Exclude draft pull requests.
  - If not specified, all pull requests are included regardless of draft status.

Example:
```bash
gh-pulls-summary --owner jewzaam --repo gh-pulls-summary --draft-filter no-drafts
```

- `--debug`: Enable debug logging to output detailed information about the script's execution.

Example:
```bash
gh-pulls-summary --owner jewzaam --repo gh-pulls-summary --debug
```

---

## Output
The tool outputs a Markdown table with the following columns:
- **Date 🔽**: The date the pull request was marked ready for review.
- **Title**: The title of the pull request, with a link to the pull request.
- **Author**: The name of the author, with a link to their GitHub profile.
- **Reviews**: The number of unique reviewers.
- **Approvals**: The number of unique approvals.

Example Output:
````markdown
| Date 🔽    | Title                                   | Author          | Reviews | Approvals |
| ---------- | --------------------------------------- | --------------- | ------- | --------- |
| 2025-05-01 | Add feature X #[123](https://github.com/...) | [John Doe](https://github.com/johndoe) | 3       | 2         |
| 2025-05-02 | Fix bug Y #[124](https://github.com/...) | [Jane Smith](https://github.com/janesmith) | 1       | 1         |
`

