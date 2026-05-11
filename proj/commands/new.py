from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm

from proj.config import STACKS, CLOUDS, SECRETS_BACKENDS, print_stack_menu
from proj.integrations import jira as jira_mod
from proj.integrations import claude_code

app = typer.Typer()
console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _pick(options: list[str], raw: str, label: str) -> str:
    try:
        idx = int(raw) - 1
    except ValueError:
        idx = -1
    if not (0 <= idx < len(options)):
        console.print(f"[red]Invalid {label} choice — must be 1–{len(options)}.[/]")
        raise typer.Exit(1)
    return options[idx]


@app.callback(invoke_without_command=True)
def new(
    name: str = typer.Argument(..., help="Project name"),
    output_dir: Path = typer.Option(Path.cwd(), "--dir", "-d", help="Where to create the project"),
    stack_flag: str = typer.Option(None, "--stack", "-s", help="Skip stack picker (set by proj plan)"),
    cloud_flag: str  = typer.Option(None, "--cloud", "-c", help="Skip cloud picker (set by proj plan)"),
):
    """Scaffold a new project with stack, cloud, and Jira Epic."""

    console.print(f"\n[bold #a78bfa]proj new[/] — scaffolding [bold]{name}[/]\n")

    # --- Stack ---
    if stack_flag:
        if stack_flag not in STACKS:
            console.print(f"[red]Unknown stack: {stack_flag}[/]")
            raise typer.Exit(1)
        stack = stack_flag
        console.print(f"[bold]Step 1/4[/] Stack: [cyan]{stack}[/] [dim](from proj plan)[/]")
    else:
        console.print("[bold]Step 1/4[/] Pick a stack:")
        print_stack_menu(console)
        stack = _pick(STACKS, Prompt.ask("\n  Choice", default="1"), "stack")

    # --- Cloud ---
    if cloud_flag:
        if cloud_flag not in CLOUDS:
            console.print(f"[red]Unknown cloud: {cloud_flag}[/]")
            raise typer.Exit(1)
        cloud = cloud_flag
        console.print(f"\n[bold]Step 2/4[/] Cloud: [cyan]{cloud}[/] [dim](from proj plan)[/]")
    else:
        console.print("\n[bold]Step 2/4[/] Pick a cloud target:")
        for i, c in enumerate(CLOUDS, 1):
            console.print(f"  [cyan]{i}[/]. {c}")
        cloud = _pick(CLOUDS, Prompt.ask("  Choice", default="4"), "cloud")

    # --- Secrets backend ---
    console.print("\n[bold]Step 3/4[/] Pick a secrets backend:")
    for i, s in enumerate(SECRETS_BACKENDS, 1):
        console.print(f"  [cyan]{i}[/]. {s}")
    secrets_backend = _pick(SECRETS_BACKENDS, Prompt.ask("  Choice", default="1"), "secrets backend")

    # --- Jira ---
    console.print("\n[bold]Step 4/4[/] Jira Epic\n")
    jira_base_url = Prompt.ask("  Jira base URL", default="https://jira.corp.adobe.com")
    jira_token    = Prompt.ask("  Jira personal access token", password=True)
    jira_project  = Prompt.ask("  Jira project key (e.g. BPOE)")

    epic_key: str | None = None
    stakeholders: list[str] = []
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

    # --- Scaffold ---
    project_dir = output_dir / name
    in_place = False
    if project_dir.exists():
        if (project_dir / "proj.yaml").exists():
            console.print(f"\n[red]Directory {project_dir} already exists with a proj.yaml.[/]")
            raise typer.Exit(1)
        console.print(f"\n[yellow]Directory {project_dir} exists but has no proj.yaml.[/]")
        if not Confirm.ask("  Initialize proj in-place (writes proj.yaml and config files, skips template copy)?", default=True):
            raise typer.Exit(0)
        in_place = True

    if not in_place:
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

    # git init (safe to re-run if repo already exists)
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    commit_msg = f"chore: proj init {name}" if in_place else f"chore: init {name}"
    result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=project_dir, capture_output=True,
    )
    if result.returncode != 0 and b"nothing to commit" not in result.stdout + result.stderr:
        console.print(f"  [yellow]git commit warning: {result.stderr.decode().strip()}[/]")

    # Jira: comment on Epic that the project is scaffolded
    if epic_key and client:
        try:
            verb = "initialised in-place" if in_place else "scaffolded"
            body = (
                f"*Project {verb} via proj CLI*\n\n"
                f"- *Name:* {name}\n"
                f"- *Stack:* {stack}\n"
                f"- *Cloud:* {cloud}\n"
                f"- *Secrets:* {secrets_backend}\n"
                f"- *Version:* 0.1.0\n"
                f"- *Directory:* {project_dir}"
            )
            jira_mod.post_comment(client, epic_key, body)
            console.print(f"  [dim]Jira: comment posted on {epic_key}[/]")
        except Exception as e:
            console.print(f"  [yellow]Jira comment skipped: {e}[/]")

    action = "initialized in" if in_place else "created at"
    console.print(f"\n[bold green]Done![/] Project {action} [bold]{project_dir}[/]")
    console.print(f"  Stack:   [cyan]{stack}[/]")
    console.print(f"  Cloud:   [cyan]{cloud}[/]")
    console.print(f"  Secrets: [cyan]{secrets_backend}[/]")
    if epic_key:
        console.print(f"  Jira:    [cyan]{epic_key}[/]")
    console.print(f"\nNext: [bold]cd {name} && proj plan[/]  [dim](or proj dev if you already know the plan)[/]")
