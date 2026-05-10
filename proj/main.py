import typer
from rich.console import Console
from proj.commands import new, dev, build, release, status, mcp

app = typer.Typer(
    name="proj",
    help="Project lifecycle manager — scaffold, dev, build, release.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()

app.add_typer(new.app,     name="new",     help="Scaffold a new project.")
app.add_typer(dev.app,     name="dev",     help="Start the dev loop.")
app.add_typer(build.app,   name="build",   help="Build and package.")
app.add_typer(release.app, name="release", help="Version, deploy, and notify.")
app.add_typer(status.app,  name="status",  help="Show project + Jira status.")
app.add_typer(mcp.app,     name="mcp",     help="Start the MCP server for Claude Code.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print("[bold #a78bfa]proj[/] — project lifecycle manager\n")
        console.print("  [cyan]proj new[/]      Scaffold a new project")
        console.print("  [cyan]proj dev[/]      Start the dev loop")
        console.print("  [cyan]proj build[/]    Build and package")
        console.print("  [cyan]proj release[/]  Version, deploy, and notify")
        console.print("  [cyan]proj status[/]   Show project + Jira status")
        console.print("  [cyan]proj mcp[/]      Start MCP server for Claude Code")


if __name__ == "__main__":
    app()
