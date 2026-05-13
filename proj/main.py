import typer
from rich.console import Console
from proj.commands import plan, new, dev, build, release, status, mcp, help as help_cmd, lazy, skills, agent

app = typer.Typer(
    name="proj",
    help="Project lifecycle manager — plan, scaffold, dev, build, release.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()

app.add_typer(plan.app,         name="plan",    help="LLM-assisted solutioning + story generation.")
app.add_typer(new.app,          name="new",     help="Scaffold a new project.")
app.add_typer(dev.app,          name="dev",     help="Start the dev loop.")
app.add_typer(build.app,        name="build",   help="Build and package.")
app.add_typer(release.app,      name="release", help="Version, deploy, and notify.")
app.add_typer(status.app,       name="status",  help="Show project + Jira status.")
app.add_typer(mcp.app,          name="mcp",     help="Start the MCP server for Claude Code.")
app.add_typer(help_cmd.app,     name="help",    help="Show all commands and flags.")
app.add_typer(lazy.app,         name="lazymode", help="TUI dashboard — run any command with a keypress.")
app.add_typer(skills.app,       name="skills",  help="Install/uninstall global Claude Code skills.")
app.add_typer(agent.app,        name="agent",   help="Autonomous agent — describe a goal, it runs the lifecycle.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print("\n[bold #a78bfa]proj[/] — project lifecycle manager\n")
        console.print("  [cyan]proj plan[/]     Brainstorm + architect with Claude")
        console.print("  [cyan]proj new[/]      Scaffold a new project")
        console.print("  [cyan]proj dev[/]      Start the dev loop")
        console.print("  [cyan]proj build[/]    Build and package")
        console.print("  [cyan]proj release[/]  Version, deploy, and notify")
        console.print("  [cyan]proj status[/]   Show project + Jira status")
        console.print("  [cyan]proj mcp[/]      Start MCP server for Claude Code")
        console.print("  [cyan]proj lazymode[/]  TUI dashboard — everything in one place")
        console.print("  [cyan]proj skills[/]   Install global Claude Code skills")
        console.print("  [cyan]proj agent[/]    Autonomous agent — describe a goal")
        console.print("\n  Run [bold]proj help[/] for full details and flags.\n")


if __name__ == "__main__":
    app()
