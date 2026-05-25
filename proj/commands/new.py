from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm

from proj.config import STACKS, CLOUDS, SECRETS_BACKENDS, print_stack_menu, load_global_settings, get_nested
from proj.integrations import jira as jira_mod
from proj.integrations import claude_code
from proj.integrations import confluence as conf_mod

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
    stack_flag: str = typer.Option(None, "--stack", "-s", help="Skip stack picker (set by athena plan)"),
    cloud_flag: str  = typer.Option(None, "--cloud", "-c", help="Skip cloud picker (set by athena plan)"),
):
    """Scaffold a new project with stack, cloud, and Jira Epic."""

    console.print(f"\n[bold #a78bfa]athena new[/] — scaffolding [bold]{name}[/]\n")

    # --- Stack ---
    if stack_flag:
        if stack_flag not in STACKS:
            console.print(f"[red]Unknown stack: {stack_flag}[/]")
            raise typer.Exit(1)
        stack = stack_flag
        console.print(f"[bold]Step 1/4[/] Stack: [cyan]{stack}[/] [dim](from athena plan)[/]")
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
        console.print(f"\n[bold]Step 2/4[/] Cloud: [cyan]{cloud}[/] [dim](from athena plan)[/]")
    else:
        console.print("\n[bold]Step 2/4[/] Pick a cloud target:")
        for i, c in enumerate(CLOUDS, 1):
            console.print(f"  [cyan]{i}[/]. {c}")
        cloud = _pick(CLOUDS, Prompt.ask("  Choice", default="4"), "cloud")

    # --- Secrets backend ---
    console.print("\n[bold]Step 3/5[/] Pick a secrets backend:")
    for i, s in enumerate(SECRETS_BACKENDS, 1):
        console.print(f"  [cyan]{i}[/]. {s}")
    secrets_backend = _pick(SECRETS_BACKENDS, Prompt.ask("  Choice", default="1"), "secrets backend")

    # --- Jira ---
    console.print("\n[bold]Step 4/5[/] Jira Epic\n")
    _gs = load_global_settings()

    jira_base_url = os.environ.get("JIRA_BASE_URL") or get_nested(_gs, "jira.base_url") or ""
    jira_token    = os.environ.get("JIRA_TOKEN")    or get_nested(_gs, "jira.token")    or ""
    jira_project  = os.environ.get("JIRA_PROJECT")  or get_nested(_gs, "jira.project_key") or ""

    if os.environ.get("JIRA_BASE_URL"):
        console.print(f"  Jira base URL: [cyan]{jira_base_url}[/] [dim](from $JIRA_BASE_URL)[/]")
    elif jira_base_url:
        console.print(f"  Jira base URL: [cyan]{jira_base_url}[/] [dim](from global settings)[/]")
    else:
        jira_base_url = Prompt.ask("  Jira base URL", default="https://jira.corp.adobe.com")

    if os.environ.get("JIRA_TOKEN"):
        console.print(f"  Jira token: [dim](from $JIRA_TOKEN)[/]")
    elif jira_token:
        console.print(f"  Jira token: [dim](from global settings)[/]")
    else:
        jira_token = Prompt.ask("  Jira personal access token", password=True)

    if os.environ.get("JIRA_PROJECT"):
        console.print(f"  Jira project key: [cyan]{jira_project}[/] [dim](from $JIRA_PROJECT)[/]")
    elif jira_project:
        console.print(f"  Jira project key: [cyan]{jira_project}[/] [dim](from global settings)[/]")
    else:
        jira_project = Prompt.ask("  Jira project key (e.g. BPOE)")

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

    # --- Confluence ---
    console.print("\n[bold]Step 5/5[/] Confluence [dim](Enter to skip)[/]\n")
    conf_token: str | None      = None
    conf_space: str | None      = None
    conf_project_page_id: str | None = None

    _conf_url_gs  = get_nested(_gs, "confluence.base_url") or ""
    _conf_tok_gs  = get_nested(_gs, "confluence.token") or ""
    _conf_spc_gs  = get_nested(_gs, "confluence.space_key") or ""

    if _conf_url_gs:
        console.print(f"  Confluence base URL: [cyan]{_conf_url_gs}[/] [dim](from global settings)[/]")
        conf_base_url = _conf_url_gs
    else:
        conf_base_url = Prompt.ask("  Confluence base URL", default="").strip()

    if conf_base_url:
        if _conf_tok_gs:
            console.print(f"  Confluence token: [dim](from global settings)[/]")
            conf_token = _conf_tok_gs
        else:
            conf_token = Prompt.ask("  Confluence personal access token", password=True)

        if _conf_spc_gs:
            console.print(f"  Space key: [cyan]{_conf_spc_gs}[/] [dim](from global settings)[/]")
            conf_space = _conf_spc_gs
        else:
            conf_space = Prompt.ask("  Space key (e.g. ENG)").strip() or None

    # --- Scaffold ---
    project_dir = output_dir / name
    in_place = False
    if project_dir.exists():
        if (project_dir / "athena.yaml").exists():
            console.print(f"\n[red]Directory {project_dir} already exists with an athena.yaml.[/]")
            raise typer.Exit(1)
        console.print(f"\n[yellow]Directory {project_dir} exists but has no athena.yaml.[/]")
        if not Confirm.ask("  Initialize athena in-place (writes athena.yaml and config files, skips template copy)?", default=True):
            raise typer.Exit(0)
        in_place = True

    if not in_place:
        template_src = TEMPLATES_DIR / stack
        if template_src.exists():
            shutil.copytree(template_src, project_dir)
        else:
            project_dir.mkdir(parents=True)

    # Write athena.yaml
    config = {
        "name":            name,
        "stack":           stack,
        "cloud":           cloud,
        "secrets_backend": secrets_backend,
        "version":         "0.1.0",
        "jira": {
            "base_url":     jira_base_url,
            "token":        jira_token,
            "project_key":  jira_project,
            "epic_key":     epic_key,
            "stakeholders": stakeholders,
        },
    }
    if conf_base_url and conf_token and conf_space:
        config["confluence"] = {
            "base_url":        conf_base_url,
            "token":           conf_token,
            "space_key":       conf_space,
            "project_page_id": None,
            "plan_page_id":    None,
            "release_page_id": None,
        }
    with open(project_dir / "athena.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # .env.example
    env_example = project_dir / ".env.example"
    if not env_example.exists():
        env_example.write_text(
            "# Copy to .env and fill in values\n"
            "# DATABASE_URL=\n"
            "# SECRET_KEY=\n"
        )

    # .gitignore
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            ".env\n.venv\n__pycache__\n*.pyc\ndist/\n.DS_Store\n"
        )

    # CLAUDE.md + .claude/ hooks + slash commands
    console.print("  Generating CLAUDE.md and .claude/ config...", end=" ")
    claude_code.scaffold(project_dir, config)
    console.print("[green]OK[/]")

    # git init (safe to re-run if repo already exists)
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    commit_msg = f"chore: athena init {name}" if in_place else f"chore: init {name}"
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
                f"*Project {verb} via athena CLI*\n\n"
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

    # Confluence: create project home page
    if conf_base_url and conf_token and conf_space:
        console.print("  Creating Confluence project page...", end=" ")
        try:
            conf_client = conf_mod.connect(conf_base_url, conf_token)
            page_body = (
                f"# {name}\n\n"
                f"Project home page auto-generated by athena CLI.\n\n"
                f"| Key | Value |\n"
                f"|---|---|\n"
                f"| Stack | `{stack}` |\n"
                f"| Cloud | `{cloud}` |\n"
                f"| Jira Epic | {epic_key or '—'} |\n"
                f"| Version | 0.1.0 |\n\n"
                f"## Pages\n\n"
                f"- **Project Plan** — created by `athena plan`\n"
                f"- **Release Notes** — updated by `athena release`\n"
            )
            conf_project_page_id = conf_mod.create_page(
                conf_client, conf_space, name, page_body
            )
            # Persist the page ID
            config["confluence"]["project_page_id"] = conf_project_page_id
            with open(project_dir / "athena.yaml", "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            page_url = conf_mod.get_page_url(conf_base_url, conf_project_page_id)
            console.print(f"[green]OK[/]")
            console.print(f"  [dim]{page_url}[/]")
        except Exception as e:
            console.print(f"[red]failed — {e}[/]")
            console.print("  [yellow]Confluence page skipped — check your token and space key.[/]")

    action = "initialized in" if in_place else "created at"
    console.print(f"\n[bold green]Done![/] Project {action} [bold]{project_dir}[/]")
    console.print(f"  Stack:   [cyan]{stack}[/]")
    console.print(f"  Cloud:   [cyan]{cloud}[/]")
    console.print(f"  Secrets: [cyan]{secrets_backend}[/]")
    if epic_key:
        console.print(f"  Jira:    [cyan]{epic_key}[/]")
    if conf_project_page_id:
        console.print(f"  Wiki:    [cyan]{conf_mod.get_page_url(conf_base_url, conf_project_page_id)}[/]")
    console.print(f"\nNext: [bold]cd {name} && athena plan[/]  [dim](or athena dev if you already know the plan)[/]")
