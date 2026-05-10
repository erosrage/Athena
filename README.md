# Athena — Project Lifecycle CLI

Python-based CLI for managing the full project lifecycle across stacks, clouds, and teams.

📖 **[Complete Usage Guide →](GUIDE.md)**

---

## Full Workflow Overview

```mermaid
flowchart TD
    CC["Claude Code"]:::claude
    CLI["proj CLI"]:::entry
    CC -->|"slash commands + MCP tools"| CLI
    CLI --> PLAN["① proj plan"]:::stage
    CLI --> NEW["② proj new"]:::stage
    CLI --> DEV["③ proj dev"]:::stage
    CLI --> BUILD["④ proj build"]:::stage
    CLI --> RELEASE["⑤ proj release"]:::stage
    CLI --> STATUS["proj status"]:::stage
    PLAN --> LLM["claude CLI solutioning loop"]:::llm
    LLM --> PM["Write PLAN.md"]:::action
    LLM --> J4["Generate + create Jira stories"]:::jira
    PLAN -->|"scaffold now?"| NEW
    NEW --> S["Scaffold + git init + proj.yaml"]:::action
    NEW --> CG["Generate CLAUDE.md + .claude/"]:::claude
    NEW --> J1["Create or link Jira Epic"]:::jira
    DEV --> ENV["Load secrets + run dev server"]:::action
    BUILD --> PUSH["docker build + push registry"]:::action
    RELEASE --> VER["Bump version + CHANGELOG"]:::action
    VER --> DEPLOY["Deploy + story → Done · Epic → Done if complete"]:::jira
    STATUS --> JS["Show version + Jira Epic + tickets"]:::action
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef stage fill:#1e40af,stroke:#3b82f6,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef claude fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef llm fill:#4c1d95,stroke:#7c3aed,color:#e2e8f0
```

---

## proj new

```mermaid
flowchart TD
    A["proj new name"]:::entry
    A --> B["Prompt: pick stack"]:::prompt
    B --> C["Prompt: cloud target"]:::prompt
    C --> SB["Prompt: secrets backend"]:::prompt
    SB --> J{"Jira Epic"}:::decision
    J -->|"Use existing"| J1["Prompt: enter Epic key"]:::prompt
    J -->|"Create new"| J2["POST Jira API — create Epic"]:::jira
    J1 --> J3["Validate Epic exists"]:::jira
    J2 --> J3
    J3 --> J4["Add watchers + stakeholders"]:::jira
    J4 --> D["Copy template files"]:::action
    D --> E["Write proj.yaml"]:::action
    E --> F["git init + initial commit"]:::action
    F --> G["Create .env.example + .gitignore"]:::action
    G --> H["Generate CLAUDE.md + .claude/"]:::claude
    H --> Z["Ready to dev"]:::done
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef prompt fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef claude fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
```

---

## proj plan

```mermaid
flowchart TD
    A["proj plan"]:::entry
    A --> M{"proj.yaml exists?"}:::decision
    M -->|"no — new project"| NP1["Prompt: name + cloud target"]:::prompt
    M -->|"yes — existing project"| EP1["Read proj.yaml\nAuto-load PLAN.md if it exists"]:::action
    NP1 --> NR{"--resume flag?\nPLAN.md exists?"}:::decision
    NR -->|"yes"| RL["Load existing PLAN.md as context"]:::action
    NR -->|"no"| CC
    RL --> CC
    EP1 --> CC["Open Claude Code — planning mode\nOnly Write tool allowed"]:::llm
    CC --> CH["Developer chats freely\nClaude cannot run commands or write code"]:::llm
    CH --> WP["Claude writes PLAN.md via Write tool"]:::llm
    WP --> EX["Developer exits session"]:::action
    EX --> MX{"Mode?"}:::decision
    MX -->|"new project"| MS["Multi-stack picker\ncomma-separated numbers"]:::prompt
    MS --> SN["Name each service"]:::prompt
    SN --> SC["proj new per service\n--stack + --cloud pre-filled"]:::action
    SC --> JS{"Jira configured\nin first service?"}:::decision
    JS -->|"yes"| SM
    JS -->|"no"| Z["Done"]:::done
    MX -->|"existing project"| SM{"Story method"}:::decision
    SM -->|"1 — extract via Claude"| H["claude -p extracts stories\nfrom PLAN.md"]:::llm
    SM -->|"2 — enter manually"| MN["Prompt: enter stories one by one"]:::prompt
    SM -->|"3 — skip"| Z
    H --> EX2["Show existing Jira stories\n(all statuses)"]:::jira
    MN --> EX2
    EX2 --> CR{"Create all?"}:::decision
    CR -->|"yes"| K["POST all stories to Jira Epic"]:::jira
    CR -->|"no — select"| SEL["Number picker\ne.g. 3,4 for only new stories"]:::prompt
    SEL --> K
    K --> Z
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef prompt fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef llm fill:#4c1d95,stroke:#7c3aed,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
```

---

## proj dev

```mermaid
flowchart TD
    A["proj dev"]:::entry
    A --> B["Read proj.yaml"]:::action
    B --> JT["Fetch open Jira tickets in Epic"]:::jira
    JT --> JP["Prompt: pick ticket to work on"]:::prompt
    JP --> JI["Transition ticket → In Progress"]:::jira
    JI --> ST{"Stack"}:::decision
    ST -->|"databricks"| SEC2["Load secrets"]:::action
    SEC2 --> DB["databricks repos update"]:::dbx
    DB --> DBT{"run_tests_on_dev?"}:::decision
    DBT -->|"yes"| DBR["pytest tests/ on cluster"]:::dbx
    DBT -->|"no"| DBD["Done"]:::done
    DBR --> DBD
    ST -->|"other"| C{"Secrets backend"}:::decision
    C -->|"Azure Key Vault"| D1["az keyvault fetch"]:::action
    C -->|"AWS SSM"| D2["boto3 SSM fetch"]:::action
    C -->|"SOPS"| D3["sops decrypt"]:::action
    C -->|"dotenv"| D4["python-dotenv load"]:::action
    D1 & D2 & D3 & D4 --> E["Inject into environment"]:::action
    E --> F{"Stack"}:::decision
    F -->|"flask"| G1["flask run --reload"]:::run
    F -->|"electron"| G2["npm run dev"]:::run
    F -->|"go"| G3["air live reload"]:::run
    F -->|"rust"| G4["cargo watch"]:::run
    F -->|"ts-node"| G5["tsx watch"]:::run
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef prompt fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef run fill:#1e3a5f,stroke:#3b82f6,color:#e2e8f0
    classDef dbx fill:#e25a1c,stroke:#ff6b35,color:#fff
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
```

---

## proj build

```mermaid
flowchart TD
    A["proj build"]:::entry
    A --> BT{"Build archetype"}:::decision
    BT -->|"databricks"| DB1["python -m build --wheel"]:::dbx
    DB1 --> DB2["Upload wheel to DBFS"]:::dbx
    DB2 --> DB3["dbx deploy job definition"]:::dbx
    DB3 --> JOK
    BT -->|"iac"| IaC["terraform plan / pulumi preview"]:::action
    IaC --> JOK
    BT -->|"data"| DATA["Tag only — no artifact"]:::action
    DATA --> JOK
    BT -->|"native"| NAT["Platform toolchain — no Docker"]:::action
    NAT --> JOK
    BT -->|"swift_native"| SW["swift build -c release / xcodebuild archive"]:::swift
    SW --> JOK
    BT -->|"container"| C["Generate image tag (sha + version)"]:::action
    C --> D{"Multi-arch?"}:::decision
    D -->|"Yes"| E["docker buildx --platform linux/amd64,arm64"]:::action
    D -->|"No"| F["docker build"]:::action
    E & F --> R{"Build ok?"}:::decision
    R -->|"failure"| JF["Post failure comment to Jira"]:::jira
    JF --> FAIL["Exit 1"]:::done
    R -->|"success"| G{"Cloud target"}:::decision
    G -->|"Azure"| H1["push to ACR"]:::cloud
    G -->|"AWS"| H2["push to ECR"]:::cloud
    G -->|"GCP"| H3["push to GCR"]:::cloud
    G -->|"Local"| H4["keep local"]:::cloud
    H1 & H2 & H3 & H4 --> JOK["Transition active ticket → In Review"]:::jira
    JOK --> Z["Done"]:::done
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef cloud fill:#1e3a5f,stroke:#3b82f6,color:#e2e8f0
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef dbx fill:#e25a1c,stroke:#ff6b35,color:#fff
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef swift fill:#f05138,stroke:#c0392b,color:#fff
```

---

## proj release

```mermaid
flowchart TD
    A["proj release"]:::entry
    A --> B["Prompt: major / minor / patch"]:::prompt
    B --> C["Bump version in manifest"]:::action
    C --> D["Generate CHANGELOG"]:::action
    D --> E["git commit + tag"]:::action
    E --> F["git push + push tag"]:::action
    F --> ST{"Stack"}:::decision
    ST -->|"databricks"| DB1["dbx deploy"]:::dbx
    DB1 --> DB2{"launch_on_release?"}:::decision
    DB2 -->|"yes"| DB3["dbx launch smoke run"]:::dbx
    DB2 -->|"no"| N["Jira notify"]:::action
    DB3 --> N
    ST -->|"other"| G{"Deploy target"}:::decision
    G -->|"Kubernetes"| H1["kubectl rollout"]:::deploy
    G -->|"Azure"| H2["az webapp deploy"]:::deploy
    G -->|"AWS"| H3["ecs update-service"]:::deploy
    G -->|"GCP"| H4["gcloud run deploy"]:::deploy
    H1 & H2 & H3 & H4 --> N
    N --> JC["Post Jira comment + tag stakeholders"]:::jira
    JC --> JS["Active story → Done"]:::jira
    JS --> JE{"All stories done?"}:::decision
    JE -->|"yes"| JED["Epic → Done"]:::jira
    JE -->|"no"| Z["Released — Epic stays active"]:::done
    JED --> Z
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef prompt fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef deploy fill:#1e3a5f,stroke:#3b82f6,color:#e2e8f0
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef dbx fill:#e25a1c,stroke:#ff6b35,color:#fff
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
```

---

## Claude Code Integration

```mermaid
flowchart TD
    CC["Claude Code session"]:::claude
    CC --> CM["Reads CLAUDE.md on open"]:::claude
    CC --> SC{"How you drive it"}:::decision
    SC -->|"slash"| S1["/build"]:::cmd
    SC -->|"slash"| S2["/release"]:::cmd
    SC -->|"slash"| S3["/status"]:::cmd
    SC -->|"slash"| S4["/jira-ticket"]:::cmd
    SC -->|"MCP"| M1["get_project_context"]:::mcp
    SC -->|"MCP"| M2["get_jira_epic"]:::mcp
    SC -->|"MCP"| M3["create_jira_ticket"]:::mcp
    SC -->|"MCP"| M4["run_build"]:::mcp
    SC -->|"MCP"| M5["run_release"]:::mcp
    S1 & M4 --> B["proj build"]:::cli
    S2 & M5 --> R["proj release"]:::cli
    S3 --> ST["proj status"]:::cli
    S4 & M3 --> JT["Jira ticket created"]:::cli
    CC --> HK["Stop hook - warns on dirty git"]:::hook
    classDef claude fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef cmd fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef mcp fill:#3b0764,stroke:#7c3aed,color:#e2e8f0
    classDef cli fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef hook fill:#1e293b,stroke:#475569,color:#94a3b8
```

---

## Install

```bash
pip install -e .
proj new my-project
```

## Commands

| Command | Description |
|---|---|
| `proj plan` | LLM-assisted solutioning via Claude Code CLI — writes PLAN.md, creates Jira stories |
| `proj new <name>` | Scaffold a new project — stack, cloud, secrets, Jira Epic |
| `proj dev` | Pick Jira ticket, load secrets, start dev server |
| `proj build` | Docker build + push to cloud registry (or Databricks wheel upload) |
| `proj release` | Bump version, deploy, close Jira story, notify stakeholders |
| `proj status` | Show version, git state, and live Jira Epic + tickets |
| `proj mcp` | Start MCP server for Claude Code integration |
| `proj help` | List all commands, lifecycle order, and common flags |

## Stacks

**Python:** `flask` · `fastapi` · `django` · `python-cli` · `streamlit`  
**Node/TS:** `express` · `nestjs` · `ts-node`  
**Frontend:** `react` · `nextjs` · `vue` · `svelte` · `angular`  
**Systems:** `go` · `rust` · `dotnet`  
**Desktop/Mobile:** `electron` · `tauri` · `react-native` · `flutter`  
**Data/ML:** `databricks` · `jupyter` · `mlflow` · `dbt` · `bi-report`  
**Other Backend:** `spring-boot` · `rails` · `laravel`  
**IaC:** `terraform` · `pulumi`  
**Swift/Apple:** `swift` · `vapor` · `swiftui` · `ios`

## Clouds

`azure` · `aws` · `gcp` · `local`

## Secrets backends

`dotenv` · `sops` · `azure-keyvault` · `aws-ssm` · `databricks-secrets`

## proj.yaml reference

```yaml
name: my-project
stack: flask           # flask | electron | go | rust | ts-node | bi-report | databricks
cloud: azure           # azure | aws | gcp | local
secrets_backend: dotenv
version: 0.1.0

jira:
  base_url: https://jira.corp.adobe.com
  project_key: BPOE
  epic_key: BPOE-84
  stakeholders:
    - john.doe
    - jane.smith

# Databricks only
databricks:
  repo_path: /Repos/you@adobe.com/my-project
  secret_scope: my-project
  wheel_path: dbfs:/FileStore/wheels/my-project
  job_name: my-project
  launch_on_release: false
```

## Claude Code integration

Each project scaffolded with `proj new` gets:
- `CLAUDE.md` — project context loaded automatically on session open
- `.claude/commands/` — `/build`, `/release`, `/status`, `/jira-ticket` slash commands
- `.claude/settings.json` — permissions and Stop hook

To connect the MCP server, add to `~/.claude/settings.json`:
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
