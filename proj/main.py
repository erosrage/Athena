import typer
from rich.console import Console
from proj.config import CLI_NAME
from proj.commands import start, plan, new, dev, build, release, status, mcp, help as help_cmd, lazy, skills, agent, settings

app = typer.Typer(
    name=CLI_NAME,
    help="Project lifecycle manager — start, dev, build, release.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()

app.add_typer(start.app,        name="start",   help="Start a project — wiki, plan, and scaffold in one flow.")
app.add_typer(dev.app,          name="dev",     help="Start the dev loop.")
app.add_typer(build.app,        name="build",   help="Build and package.")
app.add_typer(release.app,      name="release", help="Version, deploy, and notify.")
app.add_typer(status.app,       name="status",  help="Show project + Jira status.")
app.add_typer(mcp.app,          name="mcp",     help="Start the MCP server for Claude Code.")
app.add_typer(help_cmd.app,     name="help",    help="Show all commands and flags.")
app.add_typer(lazy.app,         name="lazymode", help="TUI dashboard — run any command with a keypress.")
app.add_typer(skills.app,       name="skills",  help="Install/uninstall global Claude Code skills.")
app.add_typer(agent.app,        name="agent",   help="Autonomous agent — describe a goal, it runs the lifecycle.")
app.add_typer(settings.app,     name="settings", help="View and edit global user settings.")
app.add_typer(plan.app,         name="plan",    help="[dim](Deprecated — use start)[/] LLM-assisted solutioning.")
app.add_typer(new.app,          name="new",     help="[dim](Deprecated — use start)[/] Scaffold a new project.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        c = CLI_NAME
        console.print(f"\n[bold #a78bfa]{c}[/] — project lifecycle manager\n")
        console.print(f"  [dim]Lifecycle (run in order):[/]")
        console.print(f"  [bold cyan]1. {c} start[/]    Plan with Claude, configure Jira + Confluence, scaffold services")
        console.print(f"  [bold cyan]2. {c} dev[/]      Load secrets, pick a Jira story → In Progress, start dev server")
        console.print(f"  [bold cyan]3. {c} build[/]    Build image/wheel/binary, push to registry, update Jira")
        console.print(f"  [bold cyan]4. {c} release[/]  Bump version, tag, deploy to cloud, close stories")
        console.print()
        console.print(f"  [dim]Utilities:[/]")
        console.print(f"  [cyan]{c} status[/]   Show version, git state, and live Jira Epic summary")
        console.print(f"  [cyan]{c} agent[/]    Autonomous agent — describe a goal, it runs the lifecycle")
        console.print(f"  [cyan]{c} lazymode[/] TUI dashboard — run any command with a keypress")
        console.print(f"  [cyan]{c} mcp[/]      MCP server so Claude Code can call athena as tools")
        console.print(f"  [cyan]{c} skills[/]   Install global Claude Code skills")
        console.print(f"  [cyan]{c} settings[/] Edit global defaults (~/.athena/settings.yml)")
        console.print(f"\n  Run [bold]{c} help[/] for full details, flags, and examples.\n")


if __name__ == "__main__":
    app()
