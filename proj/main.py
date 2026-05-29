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
        console.print(f"  [cyan]{c} start[/]    Wiki, plan, and scaffold a project")
        console.print(f"  [cyan]{c} dev[/]      Start the dev loop")
        console.print(f"  [cyan]{c} build[/]    Build and package")
        console.print(f"  [cyan]{c} release[/]  Version, deploy, and notify")
        console.print(f"  [cyan]{c} status[/]   Show project + Jira status")
        console.print(f"  [cyan]{c} mcp[/]      Start MCP server for Claude Code")
        console.print(f"  [cyan]{c} lazymode[/] TUI dashboard — everything in one place")
        console.print(f"  [cyan]{c} skills[/]   Install global Claude Code skills")
        console.print(f"  [cyan]{c} agent[/]    Autonomous agent — describe a goal")
        console.print(f"  [cyan]{c} settings[/] Manage global settings (~/.athena/settings.yml)")
        console.print(f"\n  Run [bold]{c} help[/] for full details and flags.\n")


if __name__ == "__main__":
    app()
