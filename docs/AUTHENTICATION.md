# Authentication

## GitHub

### Public Repositories

Works without authentication but is rate-limited to **60 requests/hour**.

### Private Repositories

Requires a GitHub Personal Access Token:

1. **Create a classic GitHub Token**:
   - Visit [Tokens (classic)](https://github.com/settings/tokens)
   - Select "Generate new token (classic)"
   - Check the `repo` scope
   - See [GitHub documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

2. **Provide the Token** (choose one method):

   **Option A: Use the GitHub CLI** (easiest, no token to manage):
   ```bash
   GITHUB_TOKEN=$(gh auth token) gh-pulls-summary --owner myorg --repo private-repo
   ```
   If you already have `gh` authenticated, this reuses that session token with no extra setup.

   **Option B: Command-line argument**:
   ```bash
   gh-pulls-summary --owner myorg --repo private-repo --github-token <your_token>
   ```

   **Option C: Environment variable**:
   ```bash
   export GITHUB_TOKEN=<your_token>
   gh-pulls-summary --owner myorg --repo private-repo
   ```

With authentication, you get **5,000 requests/hour** (vs 60 without).

## JIRA

Uses Atlassian Cloud Basic Auth (email + API token). See [JIRA Integration](JIRA.md) for details.

## Secure Token Management

### Environment Variables
```bash
# Linux/macOS
export GITHUB_TOKEN=<your_token>

# Windows (PowerShell)
$env:GITHUB_TOKEN="<your_token>"
```

### .env Files
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

### System Keyring

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
