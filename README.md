# Athena — Project Lifecycle CLI

Python-based CLI for managing the full project lifecycle across stacks, clouds, and teams.

📖 **[Complete Usage Guide →](GUIDE.md)**

---

## Full Workflow Overview

```mermaid
flowchart TD
    CC["Claude Code"]:::claude
    CLI["athena CLI"]:::entry
    CC -->|"/athena-* skills + MCP tools"| CLI
    CLI --> PLAN["① athena plan"]:::stage
    CLI --> NEW["② athena new"]:::stage
    CLI --> DEV["③ athena dev"]:::stage
    CLI --> BUILD["④ athena build"]:::stage
    CLI --> RELEASE["⑤ athena release"]:::stage
    CLI --> STATUS["athena status"]:::stage
    CLI --> AGENT["athena agent"]:::stage
    CLI --> SKILLS["athena skills"]:::stage
    CLI --> SETTINGS["athena settings"]:::stage
    PLAN --> LLM["claude CLI solutioning loop"]:::llm
    LLM --> PM["Write PLAN.md"]:::action
    LLM --> J4["Generate + create Jira stories"]:::jira
    PLAN -->|"scaffold now?"| NEW
    NEW --> S["Scaffold + git init + athena.yaml"]:::action
    NEW --> CG["Generate CLAUDE.md + .claude/"]:::claude
    NEW --> J1["Create or link Jira Epic"]:::jira
    DEV --> J5["Jira: pick ticket → In Progress"]:::jira
    J5 --> ENV["Load secrets + run dev server"]:::action
    ENV -.->|"cmux workspace"| CMUX["cmux status / log / notify"]:::cmux
    BUILD --> PUSH["docker build + push registry"]:::action
    PUSH -.->|"cmux workspace"| CMUX
    RELEASE --> VER["Bump version + CHANGELOG"]:::action
    VER --> DEPLOY["Deploy + story → Done · Epic → Done if complete"]:::jira
    STATUS --> JS["Show version + Jira Epic + tickets"]:::action
    AGENT --> AL["Anthropic SDK agentic loop\nathena_build · athena_release · jira_* · shell"]:::llm
    SKILLS --> SK["Install /athena-* skills\n→ ~/.claude/commands/athena/"]:::claude
    SETTINGS --> SET["View/edit ~/.athena/settings.yml"]:::action
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef stage fill:#1e40af,stroke:#3b82f6,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef claude fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef llm fill:#4c1d95,stroke:#7c3aed,color:#e2e8f0
    classDef cmux fill:#7f1d1d,stroke:#ef4444,color:#fecaca
```

---

## athena new

```mermaid
flowchart TD
    A["athena new name"]:::entry
    A --> B["Prompt: pick stack"]:::prompt
    B --> C["Prompt: cloud target"]:::prompt
    C --> SB["Prompt: secrets backend"]:::prompt
    SB --> J{"Jira Epic"}:::decision
    J -->|"Use existing"| J1["Prompt: enter Epic key"]:::prompt
    J -->|"Create new"| J2["POST Jira API — create Epic"]:::jira
    J1 --> J3["Validate Epic exists"]:::jira
    J2 --> J3
    J3 --> J4["Add watchers + stakeholders"]:::jira
    J4 --> JC["Post comment: project scaffolded (stack/cloud/secrets)"]:::jira
    JC --> D["Copy template files"]:::action
    D --> E["Write athena.yaml"]:::action
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

## athena plan

```mermaid
flowchart TD
    A["athena plan"]:::entry
    A --> M{"athena.yaml exists?"}:::decision
    M -->|"no — new project"| NP1["name arg + --cloud flag\n(prompted if omitted)"]:::prompt
    M -->|"yes — existing project"| EP1["Read athena.yaml\nAuto-load PLAN.md if it exists"]:::action
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
    SN --> SC["athena new per service\n--stack + --cloud pre-filled"]:::action
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
    K --> KC["Post comment: planning complete + story keys"]:::jira
    KC --> Z
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef prompt fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef llm fill:#4c1d95,stroke:#7c3aed,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
```

---

## athena dev

```mermaid
flowchart TD
    A["athena dev\n[--ticket KEY] [--skip-jira]"]:::entry
    A --> B["Read athena.yaml"]:::action
    B --> SJ{"--skip-jira?"}:::decision
    SJ -->|"yes"| ST
    SJ -->|"no"| TK{"--ticket flag?"}:::decision
    TK -->|"yes — e.g. PROJ-42"| JI["Transition specified ticket → In Progress"]:::jira
    TK -->|"no"| JT["Fetch open Epic tickets"]:::jira
    JT --> JP["Pick active ticket"]:::jira
    JP --> JI
    JI --> JIC["Post comment: dev started, branch + date"]:::jira
    JIC --> CMUX["cmux: set-status + log\n(if cmux workspace)"]:::cmux
    CMUX --> ST{"Stack"}:::decision
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
    F -->|"flask/fastapi/django\nstreamlit/gradio/litestar…"| G1["python dev server\n(uvicorn / flask run / streamlit run…)"]:::run
    F -->|"react/nextjs/vue\nsvelte/astro/remix…"| G2["npm run dev"]:::run
    F -->|"express/nestjs\nfastify/bun/hono/ts-node"| G3["nodemon / tsx watch / bun --watch"]:::run
    F -->|"go / fiber"| G4["air live reload"]:::run
    F -->|"rust"| G5["cargo watch"]:::run
    F -->|"electron/tauri\nreact-native/flutter"| G6["npm run dev / flutter run"]:::run
    F -->|"langchain/llamaindex\ncrewai/anthropic-sdk"| G7["python main.py"]:::run
    F -->|"spring-boot/rails\nlaravel/phoenix"| G8["platform dev server"]:::run
    F -->|"terraform/pulumi"| G9["plan / preview only"]:::run
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef prompt fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef run fill:#1e3a5f,stroke:#3b82f6,color:#e2e8f0
    classDef dbx fill:#e25a1c,stroke:#ff6b35,color:#fff
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef cmux fill:#7f1d1d,stroke:#ef4444,color:#fecaca
```

---

## athena build

```mermaid
flowchart TD
    A["athena build"]:::entry
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
    JOK --> JBC["Post comment: build success + image tag + registry"]:::jira
    JBC --> Z["Done"]:::done
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

## athena release

```mermaid
flowchart TD
    A["athena release\n[--bump patch|minor|major] [--no-deploy] [--no-jira]"]:::entry
    A --> B["--bump flag (default: patch)"]:::action
    B --> C["Bump version in manifest"]:::action
    C --> D["Generate CHANGELOG"]:::action
    D --> E["git commit + tag"]:::action
    E --> F["git push + push tag"]:::action
    F --> ND{"--no-deploy?"}:::decision
    ND -->|"yes"| NJ
    ND -->|"no"| ST{"Stack"}:::decision
    ST -->|"databricks"| DB1["dbx deploy"]:::dbx
    DB1 --> DB2{"launch_on_release?"}:::decision
    DB2 -->|"yes"| DB3["dbx launch smoke run"]:::dbx
    DB2 -->|"no"| NJ
    DB3 --> NJ
    ST -->|"other"| G{"Deploy target"}:::decision
    G -->|"Kubernetes"| H1["kubectl rollout"]:::deploy
    G -->|"Azure"| H2["az webapp deploy"]:::deploy
    G -->|"AWS"| H3["ecs update-service"]:::deploy
    G -->|"GCP"| H4["gcloud run deploy"]:::deploy
    H1 & H2 & H3 & H4 --> NJ{"--no-jira?"}:::decision
    NJ -->|"yes"| Z["Released"]:::done
    NJ -->|"no"| JC["Post Jira comment + tag stakeholders"]:::jira
    JC --> JS["Active story → Done"]:::jira
    JS --> JE{"All stories done?"}:::decision
    JE -->|"yes"| JED["Epic → Done"]:::jira
    JE -->|"no"| Z
    JED --> Z
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef deploy fill:#1e3a5f,stroke:#3b82f6,color:#e2e8f0
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef dbx fill:#e25a1c,stroke:#ff6b35,color:#fff
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
```

---

## athena agent

```mermaid
flowchart TD
    A["athena agent &quot;<goal>&quot;\n[--max-turns N] [--model MODEL]"]:::entry
    A --> CTX["Load athena.yaml\n(project context for system prompt)"]:::action
    CTX --> LOOP["Anthropic SDK message loop\nclaude-opus-4-5 · up to N turns"]:::llm
    LOOP --> TC{"tool_use?"}:::decision
    TC -->|"end_turn"| DONE["Print summary\nAgent complete"]:::done
    TC -->|"tool call"| TOOLS{"Tool"}:::decision
    TOOLS -->|"athena_status"| T1["athena status"]:::cli
    TOOLS -->|"athena_build"| T2["athena build [flags]"]:::cli
    TOOLS -->|"athena_release"| T3["athena release [flags]"]:::cli
    TOOLS -->|"jira_list_tickets"| T4["Fetch open Epic tickets"]:::jira
    TOOLS -->|"jira_create_ticket"| T5["POST new story to Jira"]:::jira
    TOOLS -->|"jira_transition_ticket"| T6["Transition ticket status"]:::jira
    TOOLS -->|"jira_comment"| T7["Post comment on ticket / Epic"]:::jira
    TOOLS -->|"read_file"| T8["Read file (PLAN.md, CHANGELOG…)"]:::action
    TOOLS -->|"shell"| T9["Run git / docker / diagnostic cmd"]:::action
    T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9 --> RES["Return tool result"]:::action
    RES --> LOOP
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef llm fill:#4c1d95,stroke:#7c3aed,color:#e2e8f0
    classDef cli fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
```

---

## Claude Code Integration

```mermaid
flowchart TD
    CC["Claude Code session"]:::claude
    CC --> CM["Reads CLAUDE.md on open"]:::claude
    CC --> SC{"How you drive it"}:::decision
    SC -->|"skill"| SK1["/athena-status"]:::cmd
    SC -->|"skill"| SK2["/athena-plan"]:::cmd
    SC -->|"skill"| SK3["/athena-dev"]:::cmd
    SC -->|"skill"| SK4["/athena-build"]:::cmd
    SC -->|"skill"| SK5["/athena-release"]:::cmd
    SC -->|"skill"| SK6["/athena-tickets"]:::cmd
    SC -->|"skill"| SK7["/athena-agent"]:::cmd
    SC -->|"MCP"| M1["get_project_context\nlist_stacks · get_plan\nget_changelog · get_git_status\nrun_status"]:::mcp
    SC -->|"MCP"| M2["get_jira_epic · list_open_tickets\nget_active_ticket · set_active_ticket\ncreate_jira_ticket · start_ticket\ncomplete_ticket · add_jira_comment"]:::mcp
    SC -->|"MCP"| M3["run_build\nrun_release"]:::mcp
    SK1 & M1 --> ST["athena status"]:::cli
    SK4 & M3 --> B["athena build"]:::cli
    SK5 & M3 --> R["athena release"]:::cli
    SK2 --> PL["athena plan"]:::cli
    SK3 --> DV["athena dev"]:::cli
    SK6 & M2 --> JT["Jira ticket ops"]:::jira
    SK7 --> AG["athena agent"]:::cli
    CC --> HK["Stop hook — warns on dirty git"]:::hook
    CC --> INST["athena skills install\n→ installs /athena-* into\n~/.claude/commands/athena/"]:::claude
    classDef claude fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef cmd fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef mcp fill:#3b0764,stroke:#7c3aed,color:#e2e8f0
    classDef cli fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef hook fill:#1e293b,stroke:#475569,color:#94a3b8
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
```

---

## Install

```bash
pip install -e .
athena new my-project
```

## Commands

| Command | Description |
|---|---|
| `athena plan [name] [--cloud] [--resume]` | LLM-assisted solutioning via Claude Code CLI — writes PLAN.md, creates Jira stories |
| `athena new <name> [--stack] [--cloud]` | Scaffold a new project — stack, cloud, secrets, Jira Epic |
| `athena dev [--ticket KEY] [--skip-jira]` | Pick Jira ticket, load secrets, start dev server |
| `athena build [--multi-arch] [--no-push] [--no-jira]` | Docker build + push to cloud registry (or Databricks wheel upload) |
| `athena release [--bump patch\|minor\|major] [--no-deploy] [--no-jira] [--dry-run]` | Bump version, deploy, close Jira story, notify stakeholders |
| `athena status` | Show version, git state, and live Jira Epic + tickets |
| `athena agent "<goal>" [--max-turns N] [--model MODEL]` | Autonomous agent — describe a goal, runs the full lifecycle via Anthropic SDK |
| `athena skills install\|uninstall\|list` | Install `/athena-*` slash commands into `~/.claude/commands/athena/` |
| `athena settings set\|get\|unset\|list` | View and edit global user settings in `~/.athena/settings.yml` |
| `athena lazymode` | Full-screen retro TUI dashboard — all commands one keypress away |
| `athena mcp` | Start MCP server for Claude Code integration (stdio) |
| `athena help` | List all commands, lifecycle order, and common flags |

## Stacks

**Python:** `flask` · `fastapi` · `django` · `python-cli` · `streamlit` · `gradio` · `litestar` · `fasthtml` · `celery`  
**Node/TS:** `express` · `nestjs` · `ts-node` · `fastify` · `bun` · `hono`  
**Frontend:** `react` · `nextjs` · `vue` · `svelte` · `angular` · `astro` · `remix` · `solidjs`  
**Systems:** `go` · `rust` · `dotnet` · `zig` · `kotlin` · `java`  
**Desktop/Mobile:** `electron` · `tauri` · `react-native` · `flutter` · `wails` · `expo`  
**Data/ML:** `databricks` · `jupyter` · `mlflow` · `dbt` · `bi-report` · `airflow` · `huggingface` · `pytorch` · `spark`  
**AI/LLM:** `langchain` · `llamaindex` · `crewai` · `anthropic-sdk`  
**Other Backend:** `spring-boot` · `rails` · `laravel` · `fiber` · `phoenix` · `graphql` · `grpc`  
**IaC:** `terraform` · `pulumi` · `ansible` · `helm` · `cdk` · `bicep`  
**Swift/Apple:** `swift` · `vapor` · `swiftui` · `ios`

## Clouds

`azure` · `aws` · `gcp` · `local`

## Secrets backends

`dotenv` · `sops` · `azure-keyvault` · `aws-ssm` · `databricks-secrets`

## athena.yaml reference

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

Each project scaffolded with `athena new` gets:
- `CLAUDE.md` — project context loaded automatically on session open
- `.claude/settings.json` — permissions and Stop hook

To install global `/athena-*` skills usable in **any** Claude Code session:
```bash
athena skills install
```
This writes 9 skill files to `~/.claude/commands/athena/`:
`/athena-status` · `/athena-plan` · `/athena-dev` · `/athena-build` · `/athena-release` · `/athena-tickets` · `/athena-new` · `/athena-lazy` · `/athena-agent`

To connect the MCP server, add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "athena": {
      "command": "athena",
      "args": ["mcp"]
    }
  }
}
```
