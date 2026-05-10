# Athena — Complete Usage Guide

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [proj new — Scaffold a Project](#4-proj-new--scaffold-a-project)
5. [proj dev — Start the Dev Loop](#5-proj-dev--start-the-dev-loop)
6. [proj build — Build and Package](#6-proj-build--build-and-package)
7. [proj release — Version, Deploy, Notify](#7-proj-release--version-deploy-notify)
8. [proj status — Project Health](#8-proj-status--project-health)
9. [proj mcp — Claude Code MCP Server](#9-proj-mcp--claude-code-mcp-server)
10. [Claude Code Integration](#10-claude-code-integration)
11. [Secrets Backends](#11-secrets-backends)
12. [Jira Setup](#12-jira-setup)
13. [Databricks Setup](#13-databricks-setup)
14. [proj.yaml Reference](#14-projyaml-reference)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Prerequisites

### Required
| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| Git | any | [git-scm.com](https://git-scm.com) |
| pipx | any | `pip install pipx` |

### Per stack (install what you use)
| Stack | Tool | Install |
|---|---|---|
| `flask` | — | included via pip |
| `electron` | Node.js + npm | [nodejs.org](https://nodejs.org) |
| `go` | Go + air | `go install github.com/air-verse/air@latest` |
| `rust` | Rust + cargo-watch | `cargo install cargo-watch` |
| `ts-node` | Node.js + tsx | `npm install -g tsx` |
| `databricks` | Databricks CLI + dbx | `pip install databricks-cli dbx` |

### Per cloud (install what you use)
| Cloud | Tool | Install |
|---|---|---|
| Azure | Azure CLI | `winget install Microsoft.AzureCLI` |
| AWS | AWS CLI + boto3 | `winget install Amazon.AWSCLI` |
| GCP | gcloud CLI | [cloud.google.com/sdk](https://cloud.google.com/sdk) |

### Per secrets backend (install what you use)
| Backend | Tool | Install |
|---|---|---|
| `sops` | SOPS | `winget install mozilla.sops` |
| `azure-keyvault` | azure-identity | included in Athena deps |
| `aws-ssm` | boto3 | included in Athena deps |
| `databricks-secrets` | Databricks CLI | `pip install databricks-cli` |

---

## 2. Installation

### Option A — pipx (recommended, installs as a global command)

```bash
git clone https://github.com/erosrage/Athena.git
cd Athena
pipx install .
```

Verify:
```bash
proj --help
```

### Option B — editable install (for development on Athena itself)

```bash
git clone https://github.com/erosrage/Athena.git
cd Athena
pip install -e .
```

### Upgrade after pulling changes

```bash
cd Athena
git pull
pipx reinstall athena-proj   # Option A
# or
pip install -e .              # Option B
```

---

## 3. Quick Start

```bash
# 1. Scaffold a new Flask project
proj new my-api

# 2. Follow the prompts (stack, cloud, secrets, Jira)

# 3. Enter the project
cd my-api

# 4. Start dev server
proj dev

# 5. Build a Docker image
proj build

# 6. Release v0.1.1
proj release --bump patch
```

---

## 4. proj new — Scaffold a Project

```bash
proj new <name>
proj new <name> --dir /path/to/parent   # create in a specific directory
```

### What it does

Walks you through 4 prompts, then creates a fully configured project.

### Prompt 1 — Stack

```
Step 1/4 Pick a stack:
  1. flask
  2. electron
  3. go
  4. rust
  5. ts-node
  6. bi-report
  7. databricks
```

| Stack | Language | Use for |
|---|---|---|
| `flask` | Python | REST APIs, web backends |
| `electron` | JS/TS | Desktop apps |
| `go` | Go | CLIs, microservices |
| `rust` | Rust | Performance-critical tools |
| `ts-node` | TypeScript | Node APIs, scripts |
| `bi-report` | Python | Power BI, Tableau, Excel pipelines |
| `databricks` | Python/PySpark | ETL, ML, Spark jobs |

### Prompt 2 — Cloud target

```
Step 2/4 Pick a cloud target:
  1. azure
  2. aws
  3. gcp
  4. local
```

This sets where `proj build` pushes images and `proj release` deploys.

### Prompt 3 — Secrets backend

```
Step 3/4 Pick a secrets backend:
  1. dotenv
  2. sops
  3. azure-keyvault
  4. aws-ssm
  5. databricks-secrets
```

See [Secrets Backends](#11-secrets-backends) for setup instructions per option.

### Prompt 4 — Jira Epic

```
Step 4/4 Jira Epic
  Jira base URL: https://jira.corp.adobe.com
  Jira personal access token: ****
  Jira project key: BPOE
  Link to an existing Epic? [y/n]
```

- **Existing Epic** — enter the key (e.g. `BPOE-84`), it validates against Jira
- **New Epic** — creates one via the Jira API and stores the key in `proj.yaml`

See [Jira Setup](#12-jira-setup) for how to generate a PAT.

### What gets created

```
my-api/
├── proj.yaml               ← project manifest (stack, cloud, secrets, Jira)
├── CLAUDE.md               ← Claude Code reads this on session open
├── .claude/
│   ├── settings.json       ← permissions + Stop hook
│   └── commands/
│       ├── build.md        ← /build slash command
│       ├── release.md      ← /release slash command
│       ├── status.md       ← /status slash command
│       └── jira-ticket.md  ← /jira-ticket slash command
├── .env.example            ← copy to .env and fill in
├── .gitignore
└── <stack files>           ← app.py, main.go, src/index.ts, etc.
```

---

## 5. proj dev — Start the Dev Loop

```bash
# From inside a project directory
proj dev
```

### What it does

1. Reads `proj.yaml` to detect stack and secrets backend
2. Loads secrets into the environment
3. Starts the appropriate dev server

### Per-stack dev commands

| Stack | Command run |
|---|---|
| `flask` | `flask run --reload` |
| `electron` | `npm run dev` |
| `go` | `air` (live reload) |
| `rust` | `cargo watch -x run` |
| `ts-node` | `npx tsx watch src/index.ts` |
| `bi-report` | `python scripts/refresh.py` |
| `databricks` | `databricks repos update` (syncs to Databricks Repos) |

### Databricks dev mode

Instead of running locally, `proj dev` syncs your local code to Databricks Repos on the current git branch:

```bash
proj dev
# → databricks repos update --path /Repos/you@adobe.com/my-project --branch main
```

Optionally runs tests against a live cluster if `databricks.run_tests_on_dev: true` in `proj.yaml`.

---

## 6. proj build — Build and Package

```bash
proj build                  # standard build + push
proj build --no-push        # build only, keep image local
proj build --multi-arch     # build for linux/amd64 + linux/arm64
```

### Docker stacks (flask, electron, go, rust, ts-node, bi-report)

1. Builds Docker image tagged as `<name>:<git-sha>` and `<name>:<version>`
2. Authenticates with the configured cloud registry
3. Pushes both tags

| Cloud | Registry | Auth command |
|---|---|---|
| `azure` | `<acr-name>.azurecr.io` | `az acr login` |
| `aws` | `<account>.dkr.ecr.<region>.amazonaws.com` | `aws ecr get-login-password` |
| `gcp` | `gcr.io/<project>` | `gcloud auth configure-docker` |
| `local` | local Docker daemon | no push |

**Required fields in `proj.yaml` per cloud:**

```yaml
# Azure
acr_name: myregistry

# AWS
aws_account_id: "123456789012"
aws_region: us-east-1

# GCP
gcp_project: my-gcp-project
```

### Databricks stack

1. Builds a Python wheel: `python -m build --wheel`
2. Uploads wheel to DBFS: `databricks fs cp dist/*.whl dbfs:/FileStore/wheels/<name>/`
3. Deploys job definition: `dbx deploy --deployment-file conf/deployment.yml`

---

## 7. proj release — Version, Deploy, Notify

```bash
proj release                        # patch bump (0.1.0 → 0.1.1)
proj release --bump minor           # minor bump (0.1.0 → 0.2.0)
proj release --bump major           # major bump (0.1.0 → 1.0.0)
proj release --dry-run              # preview without making changes
```

### What it does

1. **Bumps version** in `proj.yaml` and the stack's manifest file (`pyproject.toml`, `package.json`, `Cargo.toml`)
2. **Updates CHANGELOG.md** with commits since the last tag
3. **Commits and tags**: `git commit -m "chore: release vX.Y.Z"` + `git tag vX.Y.Z`
4. **Pushes** branch and tag to remote
5. **Deploys** to the configured cloud target
6. **Posts a Jira comment** on the Epic with release notes and `@mentions` for stakeholders
7. **Posts a webhook** (Slack, Teams, or custom) if `webhook_url` is set in `proj.yaml`

### Jira release comment

The comment posted to your Epic looks like:

```
*Released: my-api v0.1.1*

[~john.doe] [~jane.smith]

{noformat}
abc1234 feat: add user endpoint
def5678 fix: handle null session
{noformat}
```

Jira emails all `@mentioned` users and watchers automatically.

### Webhook payload

```json
{ "project": "my-api", "version": "0.1.1", "cloud": "azure" }
```

Add to `proj.yaml`:
```yaml
webhook_url: https://hooks.slack.com/services/xxx/yyy/zzz
```

---

## 8. proj status — Project Health

```bash
proj status
```

Displays a live summary:

```
proj status — my-api

  Name     my-api
  Version  0.1.1
  Stack    flask
  Cloud    azure
  Secrets  azure-keyvault
  Git tag  v0.1.1
  Branch   main

Jira Epic: BPOE-84
https://jira.corp.adobe.com/browse/BPOE-84

  Summary: My API project
  Status:  In Progress

  Key       Summary                    Status       Assignee
  BPOE-85   Add auth middleware         In Progress  john.doe
  BPOE-86   Write integration tests     To Do        Unassigned
  BPOE-87   Deploy to staging           Done         jane.smith

  3 ticket(s) in Epic
```

---

## 9. proj mcp — Claude Code MCP Server

```bash
proj mcp          # starts on stdio (default)
proj mcp --port 7777
```

Exposes your project workflow as tools Claude Code can call natively mid-session.

### Available MCP tools

| Tool | What it does |
|---|---|
| `get_project_context` | Returns stack, cloud, version, Jira Epic from `proj.yaml` |
| `get_jira_epic` | Fetches Epic details + all open tickets live from Jira |
| `create_jira_ticket` | Creates a new ticket in the Epic |
| `run_build` | Triggers `proj build` and returns output |
| `run_release` | Triggers `proj release` with bump type |
| `get_git_status` | Returns branch, last tag, uncommitted file count |

### Wire it into Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "proj": {
      "command": "proj",
      "args": ["mcp"]
    }
  }
}
```

Restart Claude Code. You can now say things like:
- *"Check the Jira Epic status"*
- *"Create a bug ticket for the null session issue and assign it to john.doe"*
- *"Run a dry-run release"*
- *"What's the current version and branch?"*

---

## 10. Claude Code Integration

Every project created with `proj new` is pre-wired for Claude Code.

### CLAUDE.md

Automatically generated at project root. Claude Code reads this on every session open — no need to re-explain the project each time.

```markdown
# my-api

## Project context
| Key | Value |
|---|---|
| Stack | flask |
| Cloud | azure |
| Jira Epic | BPOE-84 (https://jira.corp.adobe.com/browse/BPOE-84) |
| Stakeholders | john.doe, jane.smith |

## Lifecycle commands
proj dev / proj build / proj release / proj status
...
```

### Slash commands

Available inside any Claude Code session in the project:

| Command | What happens |
|---|---|
| `/build` | Claude runs `proj build` and reports the result |
| `/release` | Claude asks patch/minor/major, runs `proj release`, summarises |
| `/status` | Claude runs `proj status` and displays a clean summary |
| `/jira-ticket` | Claude prompts for summary/description/assignee, creates ticket |

### Stop hook

When you end a Claude Code session with uncommitted changes, the terminal prints:

```
[proj] Uncommitted changes detected. Run: proj build
```

---

## 11. Secrets Backends

### dotenv (default)

1. Copy `.env.example` to `.env`
2. Fill in values
3. `proj dev` loads them automatically

```bash
cp .env.example .env
# edit .env
proj dev
```

### SOPS (encrypted .env)

1. Install SOPS and configure a key (age, PGP, or cloud KMS)
2. Encrypt: `sops -e .env > .env.enc` then delete `.env`
3. Add to `proj.yaml`:

```yaml
secrets_backend: sops
sops_file: .env.enc
```

### Azure Key Vault

1. Create a Key Vault and store secrets there
2. Log in: `az login`
3. Add to `proj.yaml`:

```yaml
secrets_backend: azure-keyvault
keyvault_url: https://my-vault.vault.azure.net
```

Secret names like `DATABASE-URL` become env var `DATABASE_URL`.

### AWS SSM Parameter Store

1. Store parameters under a path prefix (e.g. `/my-api/`)
2. Configure AWS credentials: `aws configure`
3. Add to `proj.yaml`:

```yaml
secrets_backend: aws-ssm
ssm_prefix: /my-api/
aws_region: us-east-1
```

### Databricks Secrets

1. Create a secret scope: `databricks secrets create-scope --scope my-api`
2. Add secrets: `databricks secrets put --scope my-api --key DATABASE_URL`
3. Add to `proj.yaml`:

```yaml
secrets_backend: databricks-secrets
databricks:
  secret_scope: my-api
  secret_keys:
    - DATABASE_URL
    - API_KEY
```

---

## 12. Jira Setup

### Generate a Personal Access Token

1. Go to `https://jira.corp.adobe.com/secure/ViewProfile.jspa`
2. Click **Personal Access Tokens** in the left sidebar
3. Click **Create token** → give it a name → copy the token

> Store this token in your secrets backend — never commit it to git.

### Store the token securely

Add to your `.env` (or secrets backend):
```
JIRA_TOKEN=your-token-here
```

Then reference it in `proj.yaml`:
```yaml
jira:
  base_url: https://jira.corp.adobe.com
  token: ${JIRA_TOKEN}    # or paste directly for local use only
  project_key: BPOE
  epic_key: BPOE-84
  stakeholders:
    - john.doe
    - jane.smith
```

### Finding your project key

The project key is the prefix in ticket numbers. In `BPOE-84`, the key is `BPOE`. Find it at:
`https://jira.corp.adobe.com/secure/BrowseProjects.jspa`

---

## 13. Databricks Setup

### 1. Configure the Databricks CLI

```bash
databricks configure --token
# Enter: https://your-workspace.azuredatabricks.net
# Enter: your personal access token
```

Generate a PAT in Databricks: **Settings → Developer → Access Tokens → Generate new token**

### 2. Create a Databricks Repo

In Databricks workspace: **Repos → Add Repo** → connect to your GitHub repo.

Note the repo path (e.g. `/Repos/you@adobe.com/my-project`).

### 3. Update proj.yaml

```yaml
stack: databricks
cloud: azure           # or aws/gcp where your workspace lives
secrets_backend: databricks-secrets

databricks:
  repo_path: /Repos/you@adobe.com/my-project
  secret_scope: my-project
  secret_keys:
    - DATABASE_URL
    - STORAGE_KEY
  wheel_path: dbfs:/FileStore/wheels/my-project
  job_name: my-project
  launch_on_release: false    # set true to auto smoke-run on proj release
  run_tests_on_dev: false     # set true to run pytest on proj dev
```

### 4. Update the job definition

Edit `conf/deployment.yml` and replace the placeholders:

```yaml
environments:
  default:
    workflows:
      - name: "my-project"
        tasks:
          - task_key: main
            existing_cluster_id: "0123-456789-abc123"   # your cluster ID
            python_wheel_task:
              package_name: "my-project"
              entry_point: main
```

Find your cluster ID in Databricks: **Compute → your cluster → Configuration → Cluster ID**.

### 5. Dev/build/release flow

```bash
proj dev      # syncs code to /Repos/you@adobe.com/my-project on current branch
proj build    # builds wheel → uploads to DBFS → dbx deploy
proj release  # bumps version → dbx deploy → optional smoke run → Jira notify
```

---

## 14. proj.yaml Reference

```yaml
# ── Core ────────────────────────────────────────────────────
name: my-project
stack: flask              # flask|electron|go|rust|ts-node|bi-report|databricks
cloud: azure              # azure|aws|gcp|local
secrets_backend: dotenv   # dotenv|sops|azure-keyvault|aws-ssm|databricks-secrets
version: 0.1.0

# ── Jira ────────────────────────────────────────────────────
jira:
  base_url: https://jira.corp.adobe.com
  project_key: BPOE
  epic_key: BPOE-84
  token: ${JIRA_TOKEN}      # load from env or paste directly
  stakeholders:
    - john.doe
    - jane.smith

# ── Notifications ────────────────────────────────────────────
webhook_url: https://hooks.slack.com/services/xxx   # optional

# ── Azure ────────────────────────────────────────────────────
acr_name: myregistry         # Azure Container Registry name (without .azurecr.io)

# ── AWS ──────────────────────────────────────────────────────
aws_account_id: "123456789012"
aws_region: us-east-1
ecs_cluster: default
ssm_prefix: /my-project/    # for aws-ssm secrets backend

# ── GCP ──────────────────────────────────────────────────────
gcp_project: my-gcp-project

# ── Secrets: SOPS ────────────────────────────────────────────
sops_file: .env.enc

# ── Secrets: Azure Key Vault ──────────────────────────────────
keyvault_url: https://my-vault.vault.azure.net

# ── Databricks ───────────────────────────────────────────────
databricks:
  repo_path: /Repos/you@adobe.com/my-project
  secret_scope: my-project
  secret_keys:
    - DATABASE_URL
    - API_KEY
  wheel_path: dbfs:/FileStore/wheels/my-project
  job_name: my-project
  deployment_file: conf/deployment.yml
  launch_on_release: false
  run_tests_on_dev: false
```

---

## 15. Troubleshooting

### `proj: command not found`

```bash
pipx ensurepath        # adds pipx bin dir to PATH
# restart terminal, then retry
```

### `No proj.yaml found`

You're not inside a project directory. Either `cd` into one or run `proj new` to create a new project.

### `proj dev` — command not found for stack tool

Install the missing tool for your stack (see [Prerequisites](#1-prerequisites)).

### Jira: 401 Unauthorized

Your PAT has expired or is incorrect. Generate a new one at:
`https://jira.corp.adobe.com/secure/ViewProfile.jspa` → Personal Access Tokens

### Jira: Epic not found

- Confirm the Epic key exists: `https://jira.corp.adobe.com/browse/BPOE-84`
- Confirm the issue type is actually **Epic** (not Story/Task)
- Confirm your token has read access to that project

### Docker push fails

Ensure you're authenticated to the registry before building:

```bash
az acr login --name myregistry          # Azure
aws ecr get-login-password | docker login ...   # AWS
gcloud auth configure-docker            # GCP
```

### Databricks: `repos update` fails

- Confirm `repo_path` in `proj.yaml` matches exactly what's in Databricks Repos
- Confirm the Databricks CLI is configured: `databricks workspace ls /`
- Confirm the branch exists remotely: `git push origin <branch>`

### MCP server not showing tools in Claude Code

- Confirm `proj mcp` is in `~/.claude/settings.json` under `mcpServers`
- Restart Claude Code after changing settings
- Run `proj mcp` manually in a terminal to check for startup errors
