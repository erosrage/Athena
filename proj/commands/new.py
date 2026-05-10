from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm

from proj.config import STACKS, CLOUDS, SECRETS_BACKENDS
from proj.integrations import jira as jira_mod
from proj.integrations import claude_code

app = typer.Typer()
console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


@app.callback(invoke_without_command=True)
def new(
    name: str = typer.Argument(..., help="Project name"),
    output_dir: Path = typer.Option(Path.cwd(), "--dir", "-d", help="Where to create the project"),
):
    """Scaffold a new project with stack, cloud, and Jira Epic."""

    console.print(f"\n[bold #a78bfa]proj new[/] — scaffolding [bold]{name}[/]\n")

    # --- Stack ---
    console.print("[bold]Step 1/4[/] Pick a stack:")
    for i, s in enumerate(STACKS, 1):
        console.print(f"  [cyan]{i}[/]. {s}")
    stack_idx = int(Prompt.ask("  Choice", default="1")) - 1
    stack = STACKS[stack_idx]

    # --- Cloud ---
    console.print("\n[bold]Step 2/4[/] Pick a cloud target:")
    for i, c in enumerate(CLOUDS, 1):
        console.print(f"  [cyan]{i}[/]. {c}")
    cloud_idx = int(Prompt.ask("  Choice", default="4")) - 1
    cloud = CLOUDS[cloud_idx]

    # --- Secrets backend ---
    console.print("\n[bold]Step 3/4[/] Pick a secrets backend:")
    for i, s in enumerate(SECRETS_BACKENDS, 1):
        console.print(f"  [cyan]{i}[/]. {s}")
    secrets_idx = int(Prompt.ask("  Choice", default="1")) - 1
    secrets_backend = SECRETS_BACKENDS[secrets_idx]

    # --- Jira ---
    console.print("\n[bold]Step 4/4[/] Jira Epic\n")
    jira_base_url = Prompt.ask("  Jira base URL", default="https://jira.corp.adobe.com")
    jira_token    = Prompt.ask("  Jira personal access token", password=True)
    jira_project  = Prompt.ask("  Jira project key (e.g. BPOE)")

    epic_key: str | None = None
    client = None

    if Confirm.ask("  Link to an existing Epic?"):
        while True:
            epic_key = Prompt.ask("  Epic key (e.g. BPOE-84)")
            console.print(f"  Validating [bold]{epic_key}[/]...", end=" ")
            try:
                client = jira_mod.connect(jira_base_url, jira_token)
                epic = jira_mod.validate_epic(client, epic_key)
                if epic:
                    console.print("[green]OK[/]")
                    console.print(f"  [dim]{epic['fields']['summary']}[/]")
                    break
                else:
                    console.print("[red]not found or not an Epic[/]")
            except Exception as e:
                console.print(f"[red]error — {e}[/]")
    else:
        description = Prompt.ask("  Epic description", default=f"Project: {name}")
        stakeholders_raw = Prompt.ask("  Stakeholder Jira usernames (comma-separated)", default="")
        stakeholders = [s.strip() for s in stakeholders_raw.split(",") if s.strip()]
        console.print("  Creating Epic...", end=" ")
        try:
            client = jira_mod.connect(jira_base_url, jira_token)
            epic_key = jira_mod.create_epic(client, jira_project, name, description)
            console.print(f"[green]{epic_key}[/]")
            if stakeholders:
                jira_mod.add_watchers(client, epic_key, stakeholders)
                console.print(f"  Watchers added: [dim]{', '.join(stakeholders)}[/]")
        except Exception as e:
            console.print(f"[red]failed — {e}[/]")
            console.print("  [yellow]Continuing without Jira link.[/]")
            epic_key = None

    # --- Create initial stories ---
    if epic_key and client:
        if Confirm.ask(f"\n  Create initial stories under [cyan]{epic_key}[/]?", default=True):
            jira_mod.prompt_and_create_stories(client, jira_project, epic_key)

    # --- Scaffold ---
    project_dir = output_dir / name
    if project_dir.exists():
        console.print(f"\n[red]Directory {project_dir} already exists.[/]")
        raise typer.Exit(1)

    template_src = TEMPLATES_DIR / stack
    if template_src.exists():
        shutil.copytree(template_src, project_dir)
    else:
        project_dir.mkdir(parents=True)

    # Write proj.yaml
    config = {
        "name":            name,
        "stack":           stack,
        "cloud":           cloud,
        "secrets_backend": secrets_backend,
        "version":         "0.1.0",
        "jira": {
            "base_url":     jira_base_url,
            "project_key":  jira_project,
            "epic_key":     epic_key,
            "stakeholders": stakeholders,
        },
    }
    with open(project_dir / "proj.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # .env.example
    (project_dir / ".env.example").write_text(
        "# Copy to .env and fill in values\n"
        "# DATABASE_URL=\n"
        "# SECRET_KEY=\n"
    )

    # .gitignore
    (project_dir / ".gitignore").write_text(
        ".env\n.venv\n__pycache__\n*.pyc\ndist/\n.DS_Store\n"
    )

    # CLAUDE.md + .claude/ hooks + slash commands
    console.print("  Generating CLAUDE.md and .claude/ config...", end=" ")
    claude_code.scaffold(project_dir, config)
    console.print("[green]OK[/]")

    # git init
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"chore: init {name}"],
        cwd=project_dir, check=True, capture_output=True,
    )

    console.print(f"\n[bold green]Done![/] Project created at [bold]{project_dir}[/]")
    console.print(f"  Stack:   [cyan]{stack}[/]")
    console.print(f"  Cloud:   [cyan]{cloud}[/]")
    console.print(f"  Secrets: [cyan]{secrets_backend}[/]")
    if epic_key:
        console.print(f"  Jira:    [cyan]{epic_key}[/]")
    console.print(f"\nNext: [bold]cd {name} && proj dev[/]")
