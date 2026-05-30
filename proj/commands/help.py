from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

app = typer.Typer()
console = Console()

COMMANDS = [
    # Core lifecycle — in execution order
    ("athena start",    "1 · plan",     "Set cloud target, link Confluence wiki, configure Jira, run a Claude planning session, then scaffold service directories and create Jira stories from the plan."),
    ("athena dev",      "2 · develop",  "Load secrets, show open Jira stories and set the chosen one → In Progress, then launch the stack-specific dev server (flask, uvicorn, npm run dev, air, cargo watch, etc.)."),
    ("athena build",    "3 · package",  "Build a Docker image (or Databricks wheel / Swift binary), push to the registry, and post a build summary on the active Jira ticket."),
    ("athena release",  "4 · ship",     "Bump semver (patch/minor/major), write a CHANGELOG entry, create a git tag, deploy to cloud, close Jira stories, and publish release notes to Confluence."),
    # Observe & utilities
    ("athena status",   "observe",      "Print name, version, stack, cloud, git branch, last tag, and the full Jira Epic with every open story and its current status."),
    ("athena lazymode", "tui",          "Full-screen TUI: live panes for all athena outputs, trigger any lifecycle command with a single keypress."),
    ("athena agent",    "automate",     "Describe a high-level goal; Claude runs the full lifecycle autonomously — plan → dev → build → release — using athena as its toolset."),
    ("athena mcp",      "integrate",    "Start an MCP server so Claude Code can call athena start / dev / build / release / status as tools directly from a conversation."),
    ("athena skills",   "extend",       "Install or uninstall global Claude Code skills (e.g. /review, /security-review) into ~/.claude/skills/."),
    ("athena settings", "configure",    "View and edit global defaults (~/.athena/settings.yml): Jira URL, Confluence token, secrets backend, preferred cloud."),
    # Deprecated
    ("athena plan",     "deprecated",   "Deprecated — use athena start instead."),
    ("athena new",      "deprecated",   "Deprecated — use athena start instead."),
]

LIFECYCLE = "1. athena start  →  2. athena dev  →  3. athena build  →  4. athena release"

FLAGS = [
    ("athena start --cloud azure",    "Skip the cloud picker — valid values: azure, aws, gcp, local"),
    ("athena dev --ticket PROJ-42",   "Jump straight to a specific Jira story (skips the interactive picker)"),
    ("athena dev --skip-jira",        "Start the dev server without touching Jira at all"),
    ("athena build --multi-arch",     "Build for linux/amd64 + linux/arm64 via Docker buildx"),
    ("athena build --no-push",        "Build the image locally but skip the registry push"),
    ("athena release --bump minor",   "Bump the minor version (default is patch)"),
    ("athena release --dry-run",      "Preview the full release — no files written, no tags, no deploys"),
    ("athena release --no-deploy",    "Tag and update CHANGELOG but skip the deploy step"),
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
