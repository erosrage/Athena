from __future__ import annotations
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

_SKILLS_DIR = Path.home() / ".claude" / "commands" / "proj"

# ---------------------------------------------------------------------------
# Skill definitions — (filename, description, body)
# ---------------------------------------------------------------------------

_SKILLS: list[tuple[str, str, str]] = [
    (
        "proj-status.md",
        "Show current project status",
        """\
Show the current proj project status.

Use the Bash tool to run: `proj status`

Display the full output. If the command fails with "No proj.yaml found", tell the
user they need to `cd` into a proj project directory or run `proj new <name>` first.
""",
    ),
    (
        "proj-plan.md",
        "Start a planning session",
        """\
Start a proj planning session for the current project.

Use the Bash tool to run: `proj plan`

This opens an interactive Claude Code planning session in a subprocess. Let it run.
When it exits, summarise any PLAN.md content that was written.

If the user provides a project name (e.g. `/proj-plan MyApp`), run: `proj plan <name>`
If they also specify a cloud (e.g. `/proj-plan MyApp --cloud azure`), include that flag.
""",
    ),
    (
        "proj-dev.md",
        "Start the dev loop",
        """\
Start the proj dev loop for the current project.

Use the Bash tool to run: `proj dev`

This will show open Jira tickets, let the user pick one, load secrets, and start
the dev server. If the user wants to skip Jira, run: `proj dev --skip-jira`
If they specify a ticket (e.g. `/proj-dev PROJ-42`), run: `proj dev --ticket PROJ-42`
""",
    ),
    (
        "proj-build.md",
        "Build and package the project",
        """\
Build the current proj project.

Use the Bash tool to run: `proj build`

Common variants:
- Multi-arch build: `proj build --multi-arch`
- Local only (no push): `proj build --no-push`
- Skip Jira updates: `proj build --no-jira`

Show the full output and report success or failure clearly.
""",
    ),
    (
        "proj-release.md",
        "Release a new version",
        """\
Release the current proj project.

Default: `proj release` (patch bump)

Common variants:
- Minor bump: `proj release --bump minor`
- Major bump: `proj release --bump major`
- Dry run (preview only): `proj release --dry-run`
- Skip deploy: `proj release --no-deploy`
- Skip Jira: `proj release --no-jira`

Use the Bash tool to run the appropriate command based on the user's intent.
Show the full output including the version bump, changelog update, and Jira comment.
""",
    ),
    (
        "proj-tickets.md",
        "List open Jira tickets",
        """\
List the open Jira tickets for the current proj project.

Use the Bash tool to run: `proj status`

Parse the Jira ticket table from the output and present it cleanly.
If no tickets are shown, tell the user the Epic has no open stories.
If Jira is not configured, explain how to add it: edit `proj.yaml` and add a `jira:` section.
""",
    ),
    (
        "proj-new.md",
        "Scaffold a new project",
        """\
Scaffold a new proj project.

Ask the user for the project name if not provided, then use the Bash tool to run:
`proj new <name>`

If the user specifies a stack and cloud upfront, use:
`proj new <name> --stack <stack> --cloud <cloud>`

Available stacks: flask, fastapi, django, python-cli, streamlit, gradio, litestar,
fasthtml, celery, express, nestjs, ts-node, fastify, bun, hono, react, nextjs, vue,
svelte, angular, astro, remix, solidjs, go, rust, dotnet, zig, kotlin, java,
electron, tauri, react-native, flutter, wails, expo, databricks, jupyter, mlflow,
dbt, bi-report, airflow, huggingface, pytorch, spark, langchain, llamaindex, crewai,
anthropic-sdk, spring-boot, rails, laravel, fiber, phoenix, graphql, grpc,
terraform, pulumi, ansible, helm, cdk, bicep, swift, vapor, swiftui, ios

Available clouds: azure, aws, gcp, local
""",
    ),
    (
        "proj-lazy.md",
        "Open the retro TUI dashboard",
        """\
Open the proj lazy-mode retro TUI dashboard.

Use the Bash tool to run: `proj lazy`

This opens a full-screen terminal UI with buttons for all proj commands.
Keyboard shortcuts: P=Plan, N=New, D=Dev, B=Build, L=reLease, S=Status, Q=Quit.
""",
    ),
    (
        "proj-agent.md",
        "Run the autonomous proj agent",
        """\
Run the proj autonomous agent with a natural language goal.

Use the Bash tool to run: `proj agent "<goal>"`

Examples:
- `proj agent "build the project and post the image tag to Jira"`
- `proj agent "create 3 stories from PLAN.md and transition the first one to In Progress"`
- `proj agent "do a patch release and notify the team"`

The agent will use the proj CLI tools autonomously to accomplish the goal.
Use `--max-turns N` to limit turns (default 15).
""",
    ),
]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def skills(ctx: typer.Context):
    """Manage global Claude Code skills for the proj CLI."""
    if ctx.invoked_subcommand is None:
        _cmd_list()


@app.command("install")
def install():
    """Install proj skills into ~/.claude/commands/proj/ for use in any Claude Code session."""
    _SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    console.print(f"\n[bold #a78bfa]proj skills install[/] → [dim]{_SKILLS_DIR}[/]\n")

    for filename, description, body in _SKILLS:
        path = _SKILLS_DIR / filename
        path.write_text(body, encoding="utf-8")
        console.print(f"  [green]✓[/] [bold]/{filename.removesuffix('.md')}[/]  [dim]{description}[/]")

    console.print(f"\n[bold]{len(_SKILLS)}[/] skills installed.")
    console.print("[dim]Reload Claude Code for changes to take effect.[/]")
    console.print(f"\nInvoke with: [bold]/proj-status[/], [bold]/proj-plan[/], [bold]/proj-build[/], etc.\n")


@app.command("uninstall")
def uninstall():
    """Remove all proj skills from ~/.claude/commands/proj/."""
    if not _SKILLS_DIR.exists():
        console.print("[dim]No proj skills installed.[/]")
        return

    removed = 0
    for filename, _, _ in _SKILLS:
        path = _SKILLS_DIR / filename
        if path.exists():
            path.unlink()
            removed += 1

    # Remove dir if empty
    try:
        _SKILLS_DIR.rmdir()
    except OSError:
        pass

    console.print(f"[green]Removed {removed} skill(s).[/]")


@app.command("list")
def _cmd_list():
    """List installed proj skills."""
    console.print(f"\n[bold #a78bfa]proj skills[/] — [dim]{_SKILLS_DIR}[/]\n")
    table = Table(show_header=True, header_style="bold #a78bfa", box=None, padding=(0, 2))
    table.add_column("Skill", style="cyan")
    table.add_column("Description")
    table.add_column("Installed", style="green")

    for filename, description, _ in _SKILLS:
        name = "/" + filename.removesuffix(".md")
        installed = "✓" if (_SKILLS_DIR / filename).exists() else "—"
        table.add_row(name, description, installed)

    console.print(table)
    if not _SKILLS_DIR.exists():
        console.print("\n[dim]Run [bold]proj skills install[/] to install.[/]")
    console.print()
