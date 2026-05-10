from __future__ import annotations
import subprocess
import sys

import typer
from rich.console import Console

from proj.config import load_config
from proj.integrations import secrets as secrets_mod
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()

STACK_COMMANDS: dict[str, list[str] | None] = {
    # Python
    "flask":        [sys.executable, "-m", "flask", "run", "--reload"],
    "fastapi":      ["uvicorn", "main:app", "--reload"],
    "django":       [sys.executable, "manage.py", "runserver"],
    "python-cli":   [sys.executable, "-m", "pytest", "-v", "--tb=short"],
    "streamlit":    ["streamlit", "run", "app.py"],
    # Node / TypeScript
    "express":      ["npx", "nodemon", "src/index.js"],
    "nestjs":       ["npm", "run", "start:dev"],
    "ts-node":      ["npx", "tsx", "watch", "src/index.ts"],
    # Frontend
    "react":        ["npm", "run", "dev"],
    "nextjs":       ["npm", "run", "dev"],
    "vue":          ["npm", "run", "dev"],
    "svelte":       ["npm", "run", "dev"],
    "angular":      ["npm", "start"],
    # Systems
    "go":           ["air"],
    "rust":         ["cargo", "watch", "-x", "run"],
    "dotnet":       ["dotnet", "watch", "run"],
    # Desktop / Mobile
    "electron":     ["npm", "run", "dev"],
    "tauri":        ["npm", "run", "tauri", "dev"],
    "react-native": ["npx", "react-native", "start"],
    "flutter":      ["flutter", "run"],
    # Data / ML
    "databricks":   None,   # handled separately
    "jupyter":      ["jupyter", "lab"],
    "mlflow":       [sys.executable, "-m", "mlflow", "ui"],
    "dbt":          ["dbt", "docs", "serve"],
    "bi-report":    [sys.executable, "scripts/refresh.py"],
    # Other Backend
    "spring-boot":  ["./mvnw", "spring-boot:run"],
    "rails":        ["bin/rails", "server"],
    "laravel":      ["php", "artisan", "serve"],
    # IaC
    "terraform":    ["terraform", "plan"],
    "pulumi":       ["pulumi", "preview"],
}


@app.callback(invoke_without_command=True)
def dev(ctx: typer.Context):
    """Load secrets, pick a Jira ticket, and start the dev server."""

    config  = _load_or_exit()
    name    = config["name"]
    stack   = config["stack"]
    backend = config.get("secrets_backend", "dotenv")

    console.print(f"\n[bold #a78bfa]proj dev[/] — [bold]{name}[/] ([cyan]{stack}[/])\n")

    # --- Jira: show open tickets + pick active ---
    active_ticket = _jira_start(config)

    # --- Load secrets ---
    console.print(f"\nLoading secrets via [bold]{backend}[/]...")
    secrets_mod.load(backend, config)

    # --- Databricks: sync to Repos instead of running locally ---
    if stack == "databricks":
        _databricks_dev(config)
        return

    # --- Resolve and run dev command ---
    cmd = STACK_COMMANDS.get(stack)
    if not cmd:
        console.print(f"[red]No dev command configured for stack: {stack}[/]")
        raise typer.Exit(1)

    console.print(f"\nStarting: [bold]{' '.join(cmd)}[/]\n")
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        console.print(f"[red]Command not found: {cmd[0]}[/]")
        console.print(f"Make sure [bold]{cmd[0]}[/] is installed and on your PATH.")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Dev server stopped.[/]")


def _jira_start(config: dict) -> str | None:
    """Show open tickets, let user pick one, transition it to In Progress."""
    jira_cfg = config.get("jira", {})
    epic_key = jira_cfg.get("epic_key")
    base_url = jira_cfg.get("base_url")
    token    = jira_cfg.get("token")

    if not all([epic_key, base_url, token]):
        return None

    console.print(f"[bold]Jira:[/] open tickets in [cyan]{epic_key}[/]")
    try:
        client  = jira_mod.connect(base_url, token)
        tickets = jira_mod.get_open_tickets(client, epic_key)

        if not tickets:
            console.print("  [dim]No open tickets.[/]")
            return None

        ticket = jira_mod.pick_active_ticket(tickets)
        if not ticket:
            return None

        key = ticket["key"]
        jira_mod.save_active_ticket(key)
        ok = jira_mod.transition_ticket(client, key, "In Progress")
        if ok:
            console.print(f"  [green]{key}[/] → In Progress")
        return key

    except Exception as e:
        console.print(f"  [yellow]Jira unavailable: {e}[/]")
        return None


def _databricks_dev(config: dict) -> None:
    dbx = config.get("databricks", {})
    repo_path = dbx.get("repo_path")
    if not repo_path:
        console.print("[red]databricks.repo_path not set in proj.yaml[/]")
        console.print("Example: [dim]repo_path: /Repos/you@adobe.com/my-project[/]")
        raise typer.Exit(1)

    console.print(f"\nSyncing to Databricks Repos: [cyan]{repo_path}[/]")
    subprocess.run(
        ["databricks", "repos", "update", "--path", repo_path, "--branch", _git_branch()],
        check=True,
    )
    console.print("[green]Repo synced.[/]")

    if config.get("databricks", {}).get("run_tests_on_dev", False):
        console.print("\nRunning tests against cluster...")
        subprocess.run(["pytest", "tests/", "-v"], check=False)


def _git_branch() -> str:
    r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "main"


def _load_or_exit() -> dict:
    try:
        return load_config()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
