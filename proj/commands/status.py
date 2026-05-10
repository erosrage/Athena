from __future__ import annotations
import subprocess

import typer
from rich.console import Console
from rich.table import Table

from proj.config import load_config
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def status(ctx: typer.Context):
    """Show project status: version, git, Jira Epic, and open tickets."""

    config = _load_or_exit()
    name    = config["name"]
    stack   = config["stack"]
    cloud   = config["cloud"]
    version = config.get("version", "0.1.0")

    console.print(f"\n[bold #a78bfa]proj status[/] — [bold]{name}[/]\n")

    # Project summary table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Name",    name)
    table.add_row("Version", version)
    table.add_row("Stack",   stack)
    table.add_row("Cloud",   cloud)
    table.add_row("Secrets", config.get("secrets_backend", "—"))
    table.add_row("Git tag", _last_git_tag())
    table.add_row("Branch",  _git_branch())
    console.print(table)

    # Jira
    jira_cfg = config.get("jira", {})
    epic_key = jira_cfg.get("epic_key")
    if not epic_key:
        console.print("\n[dim]No Jira Epic linked.[/]")
        return

    console.print(f"\n[bold]Jira Epic:[/] [cyan]{epic_key}[/]")
    base_url = jira_cfg.get("base_url", "")
    console.print(f"[dim]{base_url}/browse/{epic_key}[/]\n")

    token = jira_cfg.get("token") or _prompt_token()
    if not token:
        console.print("[yellow]No Jira token — skipping ticket fetch.[/]")
        return

    try:
        client = jira_mod.connect(base_url, token)
        epic   = client.issue(epic_key)
        console.print(f"  Summary: {epic['fields']['summary']}")
        console.print(f"  Status:  {epic['fields']['status']['name']}")

        issues = jira_mod.connect(base_url, token)
        raw    = client.get_epic_issues(epic_key).get("issues", [])

        if not raw:
            console.print("\n  [dim]No tickets in Epic.[/]")
            return

        ticket_table = Table(show_header=True, header_style="bold #a78bfa")
        ticket_table.add_column("Key",      style="cyan", no_wrap=True)
        ticket_table.add_column("Summary",  max_width=50)
        ticket_table.add_column("Status",   style="green")
        ticket_table.add_column("Assignee", style="dim")

        for issue in raw:
            f        = issue["fields"]
            assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")
            ticket_table.add_row(
                issue["key"],
                f["summary"],
                f["status"]["name"],
                assignee,
            )

        console.print()
        console.print(ticket_table)
        console.print(f"\n  [dim]{len(raw)} ticket(s) in Epic[/]")

    except Exception as e:
        console.print(f"[red]Could not fetch Jira data: {e}[/]")


def _last_git_tag() -> str:
    r = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else "no tags"


def _git_branch() -> str:
    r = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def _prompt_token() -> str | None:
    from rich.prompt import Prompt
    return Prompt.ask("  Jira personal access token", password=True, default="")


def _load_or_exit() -> dict:
    try:
        return load_config()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
