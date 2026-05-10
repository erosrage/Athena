from __future__ import annotations
import json
from pathlib import Path

from proj.config import STACK_META


def scaffold(project_dir: Path, config: dict) -> None:
    """Generate CLAUDE.md and .claude/ folder inside a new project."""
    _write_claude_md(project_dir, config)
    _write_settings(project_dir, config)
    _write_commands(project_dir, config)


def _write_claude_md(project_dir: Path, config: dict) -> None:
    name     = config["name"]
    stack    = config["stack"]
    cloud    = config["cloud"]
    secrets  = config["secrets_backend"]
    jira     = config.get("jira", {})
    epic_key = jira.get("epic_key", "")
    base_url = jira.get("base_url", "")
    holders  = ", ".join(jira.get("stakeholders", [])) or "none"
    version  = config.get("version", "0.1.0")

    meta       = STACK_META.get(stack, {})
    build_type = meta.get("build", "container")
    notes      = meta.get("notes", f"- Stack: `{stack}`")
    entry      = meta.get("entry", "")

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
proj build            # build + package ({build_type})
proj release          # bump patch, deploy, notify Jira
proj release --bump minor
proj release --bump major
proj release --dry-run   # preview without changes
proj status           # show Jira Epic + open tickets
```

## Stack notes
{notes}

"""

    # Build-type-specific deployment section
    if build_type == "databricks":
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
    elif build_type == "iac":
        content += f"""## Deployment
Stack: `{stack}` — infrastructure as code, no container image.
- `proj build` → runs plan/preview
- `proj release` → tags the release; run `{'terraform apply' if stack == 'terraform' else 'pulumi up'}` to apply
- State backend: configure in `{'backend.tf' if stack == 'terraform' else 'Pulumi.yaml'}`
"""
    elif build_type == "data":
        content += f"""## Deployment
Stack: `{stack}` — no deployable artifact.
- `proj build` → no-op (tag only)
- `proj release` → bumps version and tags the repo
- Execution: schedule via your platform (Airflow, cron, dbt Cloud, etc.)
"""
    elif build_type == "swift_native":
        content += f"""## Deployment
Stack: `{stack}` — native Apple platform build.
- `proj build` → `{'swift build -c release' if stack == 'swift' else 'xcodebuild archive'}`
- `proj release` → tags the release
- Distribution: App Store Connect / TestFlight / direct binary
- Signing: configure in Xcode project settings
"""
    elif build_type == "native":
        content += f"""## Deployment
Stack: `{stack}` — platform-native build (no Docker image).
- `proj build` → informational only; use platform toolchain
- `proj release` → tags the release
- Entry point: `{entry}`
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

    stack      = config.get("stack", "")
    meta       = STACK_META.get(stack, {})
    build_type = meta.get("build", "container")

    allowed = ["Bash(proj:*)", "Bash(git:*)"]
    if build_type == "container":
        allowed.append("Bash(docker:*)")
    elif build_type == "databricks":
        allowed += ["Bash(databricks:*)", "Bash(dbx:*)"]
    elif build_type == "iac":
        allowed += [f"Bash({stack}:*)"]
    elif build_type == "swift_native":
        allowed += ["Bash(swift:*)", "Bash(xcodebuild:*)"]

    settings = {
        "permissions": {"allow": allowed},
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

    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))


def _write_commands(project_dir: Path, config: dict) -> None:
    commands_dir = project_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    stack      = config.get("stack", "")
    meta       = STACK_META.get(stack, {})
    build_type = meta.get("build", "container")

    # /build — description varies by archetype
    build_descriptions = {
        "container":    "Build and push the Docker image for this project.",
        "databricks":   "Build the Python wheel and upload to DBFS.",
        "native":       "Tag this native build for release.",
        "data":         "Tag this data/ML project for release.",
        "iac":          "Run infrastructure plan/preview.",
        "swift_native": "Build the Swift/Apple platform project.",
    }
    build_desc = build_descriptions.get(build_type, "Build this project.")

    (commands_dir / "build.md").write_text(
        f"{build_desc}\n\n"
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
