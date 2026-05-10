from __future__ import annotations
import subprocess
import sys

import typer
from rich.console import Console

from proj.config import load_config
from proj.integrations import secrets as secrets_mod

app = typer.Typer()
console = Console()

STACK_COMMANDS: dict[str, list[str]] = {
    "flask":       [sys.executable, "-m", "flask", "run", "--reload"],
    "electron":    ["npm", "run", "dev"],
    "go":          ["air"],
    "rust":        ["cargo", "watch", "-x", "run"],
    "ts-node":     ["npx", "tsx", "watch", "src/index.ts"],
    "bi-report":   [sys.executable, "scripts/refresh.py"],
    "databricks":  None,  # handled separately below
}


@app.callback(invoke_without_command=True)
def dev(ctx: typer.Context):
    """Load secrets and start the dev server for the current project."""

    config = _load_or_exit()
    name    = config["name"]
    stack   = config["stack"]
    backend = config.get("secrets_backend", "dotenv")

    console.print(f"\n[bold #a78bfa]proj dev[/] — [bold]{name}[/] ([cyan]{stack}[/])\n")

    # Load secrets
    console.print(f"Loading secrets via [bold]{backend}[/]...")
    secrets_mod.load(backend, config)

    # Databricks: sync to Repos instead of running locally
    if stack == "databricks":
        _databricks_dev(config)
        return

    # Resolve command
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

    run_tests = dbx.get("run_tests_on_dev", False)
    if run_tests:
        console.print("\nRunning tests against cluster...")
        subprocess.run(["pytest", "tests/", "-v"], check=False)


def _git_branch() -> str:
    import subprocess as sp
    r = sp.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "main"


def _load_or_exit() -> dict:
    try:
        return load_config()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
