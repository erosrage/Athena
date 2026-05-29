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
    CLI --> START["① athena start"]:::stage
    CLI --> DEV["② athena dev"]:::stage
    CLI --> BUILD["③ athena build"]:::stage
    CLI --> RELEASE["④ athena release"]:::stage
    CLI --> STATUS["athena status"]:::stage
    CLI --> AGENT["athena agent"]:::stage
    CLI --> SKILLS["athena skills"]:::stage
    CLI --> SETTINGS["athena settings"]:::stage
    START --> WIKI["Link / create Confluence wiki"]:::wiki
    START --> LLM["claude CLI — planning session (opt-in)"]:::llm
    LLM --> PM["Write PLAN.md"]:::action
    LLM --> J4["Generate + create Jira stories"]:::jira
    PM -.->|"publish plan"| CONF["Confluence\nwiki"]:::wiki
    START --> S["Scaffold + git init + athena.yaml"]:::action
    START --> CG["Generate CLAUDE.md + .claude/"]:::claude
    START --> J1["Link Jira Epic + epic_key"]:::jira
    S -.->|"project home page"| CONF
    DEV --> J5["Jira: pick ticket → In Progress"]:::jira
    J5 --> ENV["Load secrets + run dev server"]:::action
    ENV -.->|"cmux workspace"| CMUX["cmux status / log / notify"]:::cmux
    BUILD --> PUSH["docker build + push registry"]:::action
    PUSH -.->|"cmux workspace"| CMUX
    RELEASE --> VER["Bump version + CHANGELOG"]:::action
    VER --> DEPLOY["Deploy + story → Done · Epic → Done if complete"]:::jira
    VER -.->|"release notes"| CONF
    STATUS --> JS["Show version + Jira Epic + tickets"]:::action
    AGENT --> AL["Anthropic SDK agentic loop\nathena_build · athena_release · jira_* · confluence_* · shell"]:::llm
    SKILLS --> SK["Install /athena-* skills\n→ ~/.claude/commands/athena/"]:::claude
    SETTINGS --> SET["View/edit ~/.athena/settings.yml"]:::action
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef stage fill:#1e40af,stroke:#3b82f6,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef claude fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef llm fill:#4c1d95,stroke:#7c3aed,color:#e2e8f0
    classDef cmux fill:#7f1d1d,stroke:#ef4444,color:#fecaca
    classDef wiki fill:#1a4731,stroke:#22c55e,color:#bbf7d0
```

---

## athena start

```mermaid
flowchart TD
    A["athena start [name] [--cloud]"]:::entry
    A --> M{"athena.yaml\nexists?"}:::decision
    M -->|"no — new project"| NP["Name + cloud picker"]:::prompt
    M -->|"yes — existing project"| EP["Load config\nAuto-load PLAN.md"]:::action

    NP --> WK["Step 2/4: Wiki documentation"]
    WK --> WKC{"Wiki choice"}:::decision
    WKC -->|"1 — link existing page"| WKL["Fetch page content\nas planning context"]:::wiki
    WKC -->|"2 — create new page"| WKN["Page created after planning"]:::wiki
    WKC -->|"3 — skip"| JR
    WKL --> JR
    WKN --> JR

    JR["Step 3/4: Jira\nbase URL · project key · epic key"]:::jira
    JR --> PLAN{"Step 4/4\nPlan with Claude?"}:::decision

    PLAN -->|"yes"| CC["Open Claude Code — planning mode\nOnly Write tool allowed\nWiki content injected as context"]:::llm
    CC --> CH["Developer chats — architecture,\ntrade-offs, tech choices"]:::llm
    CH --> PM["Claude writes plans/PLAN.md"]:::llm
    PM --> EX["Developer exits (/exit)"]:::action
    PLAN -->|"no — scaffold directly"| SK
    EX --> SK

    SK["Stack picker — comma-separated numbers"]:::prompt
    SK --> SN["Name each service"]:::prompt
    SN --> SC["Scaffold each service:\ntemplate · athena.yaml · CLAUDE.md\ngit init + commit · Jira Epic comment"]:::action

    SC --> JS{"Jira\nconfigured?"}:::decision
    JS -->|"yes"| SM{"Story method"}:::decision
    JS -->|"no"| WKP
    SM -->|"1 — extract via Claude"| H["claude -p extracts stories\nfrom PLAN.md"]:::llm
    SM -->|"2 — enter manually"| MN["Enter stories one by one"]:::prompt
    SM -->|"3 — skip"| WKP
    H --> CR{"Create all?"}:::decision
    MN --> CR
    CR -->|"yes"| K["POST all stories to Jira Epic"]:::jira
    CR -->|"no — select"| SEL["Number picker"]:::prompt
    SEL --> K
    K --> KC["Post comment: planning complete + story keys"]:::jira
    KC --> WKP

    WKP{"Confluence\nconfigured?"}:::decision
    WKP -->|"yes"| WKU["Create/update plan page\nor project home page"]:::wiki
    WKP -->|"no"| Z["Done → athena dev"]:::done
    WKU --> Z

    EP --> EWK{"Wiki linked?"}:::decision
    EWK -->|"no — settings available"| WK2["Wiki setup"]:::wiki
    EWK -->|"yes / skip"| RPL
    WK2 --> RPL{"Re-plan?"}:::decision
    RPL -->|"yes"| CC
    RPL -->|"no"| Z

    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef prompt fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef llm fill:#4c1d95,stroke:#7c3aed,color:#e2e8f0
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef wiki fill:#1a4731,stroke:#22c55e,color:#bbf7d0
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
    DB2 -->|"no"| WK
    DB3 --> WK
    ST -->|"other"| G{"Deploy target"}:::decision
    G -->|"Kubernetes"| H1["kubectl rollout"]:::deploy
    G -->|"Azure"| H2["az webapp deploy"]:::deploy
    G -->|"AWS"| H3["ecs update-service"]:::deploy
    G -->|"GCP"| H4["gcloud run deploy"]:::deploy
    H1 & H2 & H3 & H4 --> WK["Append release notes\nto Confluence page"]:::wiki
    WK --> NJ{"--no-jira?"}:::decision
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
    classDef wiki fill:#1a4731,stroke:#22c55e,color:#bbf7d0
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
    TOOLS -->|"confluence_get_page"| T10["Read Confluence page"]:::wiki
    TOOLS -->|"confluence_update_page"| T11["Write / append\nConfluence page"]:::wiki
    T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9 & T10 & T11 --> RES["Return tool result"]:::action
    RES --> LOOP
    classDef entry fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef action fill:#1e293b,stroke:#475569,color:#cbd5e1
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef llm fill:#4c1d95,stroke:#7c3aed,color:#e2e8f0
    classDef cli fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef done fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef wiki fill:#1a4731,stroke:#22c55e,color:#bbf7d0
```

---

## Claude Code Integration

```mermaid
flowchart TD
    CC["Claude Code session"]:::claude
    CC --> CM["Reads CLAUDE.md on open"]:::claude
    CC --> SC{"How you drive it"}:::decision
    SC -->|"skill"| SK1["/athena-status"]:::cmd
    SC -->|"skill"| SK2["/athena-start"]:::cmd
    SC -->|"skill"| SK3["/athena-dev"]:::cmd
    SC -->|"skill"| SK4["/athena-build"]:::cmd
    SC -->|"skill"| SK5["/athena-release"]:::cmd
    SC -->|"skill"| SK6["/athena-tickets"]:::cmd
    SC -->|"skill"| SK7["/athena-agent"]:::cmd
    SC -->|"MCP"| M1["get_project_context\nlist_stacks · get_plan\nget_changelog · get_git_status\nrun_status"]:::mcp
    SC -->|"MCP"| M2["get_jira_epic · list_open_tickets\nget_active_ticket · set_active_ticket\ncreate_jira_ticket · start_ticket\ncomplete_ticket · add_jira_comment"]:::mcp
    SC -->|"MCP"| M3["run_build\nrun_release"]:::mcp
    SC -->|"MCP"| M4["confluence_get_page\nconfluence_update_page\nconfluence_create_page\nget_confluence_links"]:::mcp
    SC -->|"skill"| SK8["/athena-wiki"]:::cmd
    SK1 & M1 --> ST["athena status"]:::cli
    SK4 & M3 --> B["athena build"]:::cli
    SK5 & M3 --> R["athena release"]:::cli
    SK2 --> ST2["athena start"]:::cli
    SK3 --> DV["athena dev"]:::cli
    SK6 & M2 --> JT["Jira ticket ops"]:::jira
    SK7 --> AG["athena agent"]:::cli
    M4 & SK8 --> WKOP["Confluence wiki ops"]:::wiki
    CC --> HK["Stop hook — warns on dirty git"]:::hook
    CC --> INST["athena skills install\n→ installs /athena-* into\n~/.claude/commands/athena/"]:::claude
    classDef claude fill:#065f46,stroke:#059669,color:#e2e8f0
    classDef decision fill:#78350f,stroke:#d97706,color:#fef3c7
    classDef cmd fill:#0f4c75,stroke:#1b6ca8,color:#e2e8f0
    classDef mcp fill:#3b0764,stroke:#7c3aed,color:#e2e8f0
    classDef cli fill:#a78bfa,stroke:#7c3aed,color:#0f1117
    classDef hook fill:#1e293b,stroke:#475569,color:#94a3b8
    classDef jira fill:#0369a1,stroke:#0ea5e9,color:#e2e8f0
    classDef wiki fill:#1a4731,stroke:#22c55e,color:#bbf7d0
```

---

## Install

```bash
pip install -e .
athena start my-project
```

## Commands

| Command | Description |
|---|---|
| `athena start [name] [--cloud]` | Wiki, plan, and scaffold a project — replaces `athena plan` + `athena new` |
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
| `athena plan` | *(Deprecated)* Use `athena start` instead |
| `athena new` | *(Deprecated)* Use `athena start` instead |

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

confluence:
  base_url: https://wiki.corp.adobe.com
  token: ${CONFLUENCE_TOKEN}
  space_key: ENG
  project_page_id: "123456"   # auto-set by athena start
  plan_page_id: "123457"      # auto-set by athena start
  release_page_id: "123458"   # auto-set by athena release

# Databricks only
databricks:
  repo_path: /Repos/you@adobe.com/my-project
  secret_scope: my-project
  wheel_path: dbfs:/FileStore/wheels/my-project
  job_name: my-project
  launch_on_release: false
```

## Claude Code integration

Each project scaffolded with `athena start` gets:
- `CLAUDE.md` — project context loaded automatically on session open
- `.claude/settings.json` — permissions and Stop hook

To install global `/athena-*` skills usable in **any** Claude Code session:
```bash
athena skills install
```
This writes 10 skill files to `~/.claude/commands/athena/`:
`/athena-status` · `/athena-start` · `/athena-dev` · `/athena-build` · `/athena-release` · `/athena-tickets` · `/athena-lazy` · `/athena-agent` · `/athena-wiki`

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
