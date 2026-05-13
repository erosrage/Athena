from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from proj.config import (
    GLOBAL_SETTINGS_FILE,
    SETTINGS_SCHEMA,
    get_nested,
    load_global_settings,
    save_global_settings,
    set_nested,
    unset_nested,
)

app = typer.Typer()
console = Console()

_MASK = "********"


def _validate_key(key: str) -> None:
    if key not in SETTINGS_SCHEMA:
        console.print(f"[red]Unknown key: {key}[/]")
        console.print("[dim]Valid keys:[/]")
        for k in SETTINGS_SCHEMA:
            console.print(f"  [dim]{k}[/]")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def settings(ctx: typer.Context) -> None:
    """View and edit global user settings (~/.proj/settings.yml)."""
    if ctx.invoked_subcommand is None:
        _cmd_list()


@app.command("list")
def _cmd_list() -> None:
    """Show all global settings."""
    data = load_global_settings()

    console.print(f"\n[bold #a78bfa]proj settings[/]  [dim]{GLOBAL_SETTINGS_FILE}[/]\n")

    if not data:
        console.print("[dim]No global settings configured.[/]")
        console.print("[dim]Run [bold]proj settings set <key> <value>[/] to get started.[/]\n")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2), show_edge=False)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value")
    table.add_column("Source", style="dim")

    current_section = None
    for dotkey, (section, _leaf, sensitive, _desc) in SETTINGS_SCHEMA.items():
        if section != current_section:
            if current_section is not None:
                table.add_row("", "", "")
            current_section = section

        value = get_nested(data, dotkey)
        if value is None:
            display = "[dim]—[/]"
            source = ""
        elif sensitive:
            display = _MASK
            source = f"(~/.proj/settings.yml)"
        else:
            display = str(value)
            source = f"(~/.proj/settings.yml)"

        table.add_row(dotkey, display, source)

    console.print(table)
    console.print()


@app.command("get")
def _cmd_get(
    key: str = typer.Argument(..., help="Dot-notation key, e.g. jira.token"),
) -> None:
    """Print the value of a setting."""
    _validate_key(key)
    data = load_global_settings()
    value = get_nested(data, key)
    if value is None:
        console.print(f"[dim]{key} is not set.[/]")
        return
    _sec, _leaf, sensitive, _desc = SETTINGS_SCHEMA[key]
    if sensitive:
        console.print(f"[yellow]Note: this is a sensitive value.[/]")
    console.print(f"{key}=[bold]{value}[/]")


@app.command("set")
def _cmd_set(
    key:   str = typer.Argument(..., help="Dot-notation key, e.g. jira.base_url"),
    value: str = typer.Argument(..., help="Value to store"),
) -> None:
    """Set a global setting."""
    _validate_key(key)
    _sec, _leaf, sensitive, _desc = SETTINGS_SCHEMA[key]
    if sensitive:
        console.print(f"[dim]Note: value will be stored plaintext in {GLOBAL_SETTINGS_FILE}[/]")
    data = load_global_settings()
    set_nested(data, key, value)
    try:
        save_global_settings(data)
    except PermissionError as e:
        console.print(f"[red]Could not write settings file: {e}[/]")
        raise typer.Exit(1)
    display = _MASK if sensitive else value
    console.print(f"[green]Set[/] {key}=[bold]{display}[/]")


@app.command("unset")
def _cmd_unset(
    key: str = typer.Argument(..., help="Dot-notation key to remove"),
) -> None:
    """Remove a setting."""
    _validate_key(key)
    data = load_global_settings()
    data, was_present = unset_nested(data, key)
    if not was_present:
        console.print(f"[dim]{key} was not set.[/]")
        return
    try:
        save_global_settings(data)
    except PermissionError as e:
        console.print(f"[red]Could not write settings file: {e}[/]")
        raise typer.Exit(1)
    console.print(f"[green]Unset[/] {key}")
