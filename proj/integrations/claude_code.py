from __future__ import annotations
import json
from pathlib import Path


def scaffold(project_dir: Path, config: dict) -> None:
    """Generate CLAUDE.md and .claude/ folder inside a new project."""
    _write_claude_md(project_dir, config)
    _write_settings(project_dir, config)
    _write_commands(project_dir)


def _write_claude_md(project_dir: Path, config: dict) -> None:
    name       = config["name"]
    stack      = config["stack"]
    cloud      = config["cloud"]
    secrets    = config["secrets_backend"]
    jira       = config.get("jira", {})
    epic_key   = jira.get("epic_key", "")
    base_url   = jira.get("base_url", "")
    holders    = ", ".join(jira.get("stakeholders", [])) or "none"
    version    = config.get("version", "0.1.0")

    jira_line = f"{epic_key} ({base_url}/browse/{epic_key})" if epic_key else "not linked"

    content = f"""# {name}

## Project context
| Key | Value |
|---|---|
| Stack | `{stack}` |
| Cloud | `{cloud}` |
| Secrets | `{secrets}` |
| Version | `{version}` |
| Jira Epic | {jira_line} |
| Stakeholders | {holders} |

## Lifecycle commands
```bash
proj dev              # load secrets + start dev server
proj build            # docker build + push to {cloud} registry
proj build --multi-arch  # multi-platform build (amd64 + arm64)
proj release          # bump patch, deploy, notify Jira
proj release --bump minor
proj release --bump major
proj release --dry-run   # preview without changes
proj status           # show Jira Epic + open tickets
```

## Stack notes
"""

    stack_notes = {
        "flask":     "- Entry point: `app.py`\n- Run: `flask run --reload`\n- Deps: `requirements.txt`",
        "electron":  "- Entry point: `main.js`\n- Run: `npm run dev`\n- Build: `npm run build` via electron-builder",
        "go":        "- Entry point: `main.go`\n- Live reload: `air` (install with `go install github.com/air-verse/air@latest`)",
        "rust":      "- Entry point: `src/main.rs`\n- Live reload: `cargo watch -x run`",
        "ts-node":   "- Entry point: `src/index.ts`\n- Run: `npx tsx watch src/index.ts`",
        "bi-report":   "- Refresh pipeline: `scripts/refresh.py`\n- Reports: `reports/`\n- Exports: `exports/`",
        "databricks":  "- Entry point: `src/main.py`\n- Pipeline logic: `src/pipeline.py`\n- Notebooks: `notebooks/`\n- Job config: `conf/deployment.yml`\n- Tests: `pytest tests/`",
    }
    content += stack_notes.get(stack, "") + "\n\n"

    if stack == "databricks":
        dbx = config.get("databricks", {})
        content += f"""## Databricks
| Key | Value |
|---|---|
| Repo path | `{dbx.get("repo_path", "not set — add databricks.repo_path to proj.yaml")}` |
| Secret scope | `{dbx.get("secret_scope", name)}` |
| Wheel upload path | `{dbx.get("wheel_path", f"dbfs:/FileStore/wheels/{name}")}` |
| Job name | `{dbx.get("job_name", name)}` |
| Launch on release | `{dbx.get("launch_on_release", False)}` |

### Databricks commands
```bash
proj dev       # sync to Databricks Repos (databricks repos update)
proj build     # build wheel + upload to DBFS + dbx deploy
proj release   # bump version + dbx deploy + optional dbx launch smoke run
```
"""
    else:
        content += f"""## Deployment target
Cloud: `{cloud}`
- Images tagged as `{name}:<git-sha>` and `{name}:<version>`
- Registry pushed on `proj build --push`
- Deploy triggered on `proj release`
"""

    content += f"""## Secrets
Backend: `{secrets}`
- Copy `.env.example` → `.env` and fill in values (dotenv)
- Or store in your configured backend and run `proj dev` to auto-load
"""

    (project_dir / "CLAUDE.md").write_text(content)


def _write_settings(project_dir: Path, config: dict) -> None:
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(exist_ok=True)

    settings = {
        "permissions": {
            "allow": [
                "Bash(proj:*)",
                "Bash(git:*)",
                "Bash(docker:*)",
            ]
        },
        "hooks": {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python -c \"import subprocess,sys; r=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True); print('\\n[proj] Uncommitted changes detected. Run: proj build') if r.stdout.strip() else None\""
                        }
                    ]
                }
            ]
        }
    }

    (claude_dir / "settings.json").write_text(
        json.dumps(settings, indent=2)
    )


def _write_commands(project_dir: Path) -> None:
    commands_dir = project_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    # /build
    (commands_dir / "build.md").write_text(
        "Build and push the Docker image for this project.\n\n"
        "Run the following command and stream the output:\n\n"
        "```bash\nproj build\n```\n\n"
        "If the user passes `--multi-arch`, run `proj build --multi-arch` instead.\n"
        "Report any errors clearly and suggest fixes.\n"
    )

    # /release
    (commands_dir / "release.md").write_text(
        "Release a new version of this project.\n\n"
        "Ask the user: patch, minor, or major bump? Default is patch.\n\n"
        "Then run:\n\n"
        "```bash\nproj release --bump $BUMP_TYPE\n```\n\n"
        "Stream the output. After completion, summarise: new version, Jira Epic updated, "
        "deploy target, and which stakeholders were notified.\n"
    )

    # /status
    (commands_dir / "status.md").write_text(
        "Show the current project status.\n\n"
        "Run the following and display the output in a clean summary:\n\n"
        "```bash\nproj status\n```\n\n"
        "Include: current version, Jira Epic key + open ticket count, "
        "last git tag, and cloud target.\n"
    )

    # /jira-ticket
    (commands_dir / "jira-ticket.md").write_text(
        "Create a new Jira ticket linked to this project's Epic.\n\n"
        "Ask the user for:\n"
        "1. Ticket summary (one line)\n"
        "2. Description (optional)\n"
        "3. Assignee username (optional)\n\n"
        "Then run:\n\n"
        "```bash\nproj jira create --summary \"$SUMMARY\" --description \"$DESC\" --assignee \"$USER\"\n```\n\n"
        "Confirm the created ticket key and link back to Jira.\n"
    )
