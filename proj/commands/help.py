from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

app = typer.Typer()
console = Console()

COMMANDS = [
    ("athena start",   "start",      "Wiki, plan, and scaffold a project in one flow. Replaces athena plan + athena new."),
    ("athena dev",     "develop",    "Load secrets, pick active Jira ticket → In Progress, start dev server."),
    ("athena build",   "build",      "Build Docker image (or Databricks wheel), push to registry, update Jira ticket."),
    ("athena release", "release",    "Bump version, update CHANGELOG, tag, deploy to cloud, close Jira stories."),
    ("athena status",  "observe",    "Show git state, current version, and live Jira Epic + ticket summary."),
    ("athena mcp",     "integration","Start MCP server so Claude Code can call athena commands as tools."),
    ("athena help",    "meta",       "Show this help screen."),
    ("athena plan",    "deprecated", "Deprecated — use athena start instead."),
    ("athena new",     "deprecated", "Deprecated — use athena start instead."),
]

LIFECYCLE = "athena start → athena dev → athena build → athena release"

FLAGS = [
    ("athena start --cloud azure",   "Set cloud target (skips the cloud picker)"),
    ("athena build --multi-arch",    "Build for linux/amd64 + linux/arm64"),
    ("athena build --no-push",       "Build image but keep it local"),
    ("athena release --bump minor",  "Bump minor version instead of patch"),
    ("athena release --dry-run",     "Preview release without making changes"),
]


@app.callback(invoke_without_command=True)
def help_cmd():
    """Show all commands, lifecycle order, and useful flags."""

    console.print()
    console.print(Panel(
        Text(LIFECYCLE, style="bold cyan", justify="center"),
        title="[bold #a78bfa]athena[/] — lifecycle",
        border_style="#334155",
        padding=(0, 2),
    ))
    console.print()

    # Commands table
    table = Table(
        show_header=True,
        header_style="bold #a78bfa",
        box=None,
        padding=(0, 2),
        show_edge=False,
    )
    table.add_column("Command",  style="bold cyan",   no_wrap=True)
    table.add_column("Phase",    style="dim",         no_wrap=True)
    table.add_column("Description")

    for cmd, phase, desc in COMMANDS:
        table.add_row(cmd, phase, desc)

    console.print(table)
    console.print()

    # Flags table
    flags_table = Table(
        show_header=True,
        header_style="bold #a78bfa",
        box=None,
        padding=(0, 2),
        show_edge=False,
        title="[dim]Common flags[/]",
        title_justify="left",
    )
    flags_table.add_column("Flag",        style="cyan", no_wrap=True)
    flags_table.add_column("Description")

    for flag, desc in FLAGS:
        flags_table.add_row(flag, desc)

    console.print(flags_table)
    console.print()
    console.print("  [dim]Full docs:[/] [bold]athena <command> --help[/]")
    console.print()
