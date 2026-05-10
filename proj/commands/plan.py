from __future__ import annotations
import subprocess
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm

from proj.config import STACKS, CLOUDS, load_config
from proj.integrations import claude_ai
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()

PLAN_FILE = "PLAN.md"

_SYSTEM = """\
You are a senior software architect and tech lead helping a developer plan a project before writing any code.

Given the project context and the problem description, produce a structured plan with:
1. **Problem Summary** — restate the problem clearly in 2-3 sentences
2. **Proposed Solution** — high-level architecture and approach
3. **Key Components** — the main pieces that need to be built
4. **Tech Choices** — specific libraries, patterns, or services to use (grounded in the stack/cloud provided)
5. **Risks & Open Questions** — unknowns, tradeoffs, or things to validate early
6. **Suggested Stories** — a numbered list of actionable stories to break the work into

Be concrete and opinionated. Prefer simple solutions over complex ones. Ask clarifying questions if the problem is ambiguous.\
"""


@app.callback(invoke_without_command=True)
def plan(
    resume: bool = typer.Option(False, "--resume", help="Continue from an existing PLAN.md"),
):
    """LLM-assisted solutioning — brainstorm, architect, then scaffold."""

    # Detect mode: pre-scaffold (no proj.yaml) vs. existing project
    config = _try_load_config()
    existing_project = config is not None

    if existing_project:
        _plan_existing(config, resume)
    else:
        _plan_new(resume)


# ---------------------------------------------------------------------------
# Pre-scaffold mode — no proj.yaml yet
# ---------------------------------------------------------------------------

def _plan_new(resume: bool) -> None:
    console.print("\n[bold #a78bfa]proj plan[/] — new project\n")
    console.print("[dim]No proj.yaml found — let's figure out what you're building first.[/]\n")

    name = Prompt.ask("  Project name").strip()
    if not name:
        raise typer.Exit(0)

    console.print("\n  Pick a stack:")
    for i, s in enumerate(STACKS, 1):
        console.print(f"    [cyan]{i}[/]. {s}")
    stack = STACKS[int(Prompt.ask("  Choice", default="1")) - 1]

    console.print("\n  Pick a cloud target:")
    for i, c in enumerate(CLOUDS, 1):
        console.print(f"    [cyan]{i}[/]. {c}")
    cloud = CLOUDS[int(Prompt.ask("  Choice", default="4")) - 1]

    config = {"name": name, "stack": stack, "cloud": cloud}
    system = _build_system(config)
    messages: list[dict] = []

    if resume and Path(PLAN_FILE).exists():
        existing = Path(PLAN_FILE).read_text()
        messages.append({"role": "user", "content": f"Existing plan:\n\n{existing}\n\nLet's continue refining it."})
        console.print(f"\n[dim]Resuming from {PLAN_FILE}[/]")

    plan_text = _solutioning_loop(messages, system)

    _write_plan(name, stack, cloud, plan_text)
    console.print(f"\n[green]Plan saved to[/] [bold]{PLAN_FILE}[/]")

    # Summary + handoff to proj new
    console.print(f"\n[bold]Suggested settings[/]")
    console.print(f"  Name:  [cyan]{name}[/]")
    console.print(f"  Stack: [cyan]{stack}[/]")
    console.print(f"  Cloud: [cyan]{cloud}[/]")

    if Confirm.ask(f"\n  Scaffold [bold]{name}[/] now with these settings?", default=True):
        console.print()
        subprocess.run([sys.executable, "-m", "proj", "new", name], check=False)
    else:
        console.print(f"\n[dim]When ready:[/] [bold]proj new {name}[/]")


# ---------------------------------------------------------------------------
# Existing project mode — proj.yaml present
# ---------------------------------------------------------------------------

def _plan_existing(config: dict, resume: bool) -> None:
    name  = config["name"]
    stack = config.get("stack", "unknown")
    cloud = config.get("cloud", "local")

    console.print(f"\n[bold #a78bfa]proj plan[/] — [bold]{name}[/] ([cyan]{stack}[/] / [cyan]{cloud}[/])\n")

    system   = _build_system(config)
    messages: list[dict] = []

    if resume and Path(PLAN_FILE).exists():
        existing = Path(PLAN_FILE).read_text()
        messages.append({"role": "user", "content": f"Existing plan:\n\n{existing}\n\nLet's continue refining it."})
        console.print(f"[dim]Resuming from {PLAN_FILE}[/]\n")

    plan_text = _solutioning_loop(messages, system)

    _write_plan(name, stack, cloud, plan_text)
    console.print(f"\n[green]Plan saved to[/] [bold]{PLAN_FILE}[/]")

    # Jira stories
    jira_cfg    = config.get("jira", {})
    base_url    = jira_cfg.get("base_url")
    token       = jira_cfg.get("token")
    project_key = jira_cfg.get("project_key")
    epic_key    = jira_cfg.get("epic_key")

    if all([base_url, token, project_key, epic_key]):
        console.print(f"\n[bold]Jira stories[/] under [cyan]{epic_key}[/]")
        console.print("  [cyan]1[/]. Extract stories from plan via Claude")
        console.print("  [cyan]2[/]. Enter stories manually")
        console.print("  [cyan]3[/]. Skip")
        choice = Prompt.ask("  Choice", default="1").strip()
        if choice == "1":
            _create_stories_from_plan(config, jira_cfg, plan_text)
        elif choice == "2":
            _create_stories_manual(jira_cfg)
        else:
            console.print("  [dim]Skipped.[/]")
    else:
        console.print("\n  [dim]Jira not configured — skipping story creation.[/]")

    console.print(f"\n[dim]Next:[/] [bold]proj dev[/]")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _solutioning_loop(messages: list[dict], system: str) -> str:
    console.print("[bold]Describe what you're trying to build or solve.[/]")
    console.print("[dim]Be as vague or specific as you like — Claude will ask clarifying questions.[/]\n")
    problem = Prompt.ask("  Problem").strip()
    if not problem:
        console.print("[yellow]No input — exiting.[/]")
        raise typer.Exit(0)

    messages.append({"role": "user", "content": problem})
    plan_text = ""

    while True:
        console.print()
        console.rule("[dim]Claude[/]", style="dim #475569")
        console.print()

        response = claude_ai.stream_response(messages, system)
        plan_text = response
        messages.append({"role": "assistant", "content": response})

        console.print()
        console.rule(style="dim #475569")
        console.print()

        action = Prompt.ask(
            "  [bold]What next?[/] [dim](refine / question, or Enter to accept)[/]",
            default="",
        ).strip()

        if not action:
            break

        messages.append({"role": "user", "content": action})

    return plan_text


def _build_system(config: dict) -> str:
    jira_cfg = config.get("jira", {})
    epic_key = jira_cfg.get("epic_key", "none")
    return (
        f"{_SYSTEM}\n\n"
        f"Project context:\n"
        f"  name: {config['name']}\n"
        f"  stack: {config.get('stack', 'unknown')}\n"
        f"  cloud: {config.get('cloud', 'local')}\n"
        f"  secrets backend: {config.get('secrets_backend', 'dotenv')}\n"
        f"  jira epic: {epic_key}\n"
        f"  version: {config.get('version', '0.1.0')}"
    )


def _write_plan(name: str, stack: str, cloud: str, plan_text: str) -> None:
    today = date.today().isoformat()
    content = (
        f"# Plan — {name}\n\n"
        f"**Date:** {today}  \n"
        f"**Stack:** {stack}  \n"
        f"**Cloud:** {cloud}  \n\n"
        f"---\n\n"
        f"{plan_text}\n"
    )
    Path(PLAN_FILE).write_text(content, encoding="utf-8")


def _create_stories_from_plan(config: dict, jira_cfg: dict, plan_text: str) -> None:
    console.print("\n  Extracting stories from plan...")
    stories = claude_ai.extract_stories(plan_text, config)

    if not stories:
        console.print("  [yellow]No stories extracted.[/]")
        return

    console.print(f"\n  Found [bold]{len(stories)}[/] suggested stories:\n")
    for i, s in enumerate(stories, 1):
        console.print(f"    [cyan]{i}[/]. {s}")

    console.print()
    if not Confirm.ask("  Create all of these in Jira?", default=True):
        console.print("  [dim]Skipped.[/]")
        return

    _post_stories(jira_cfg, stories)


def _create_stories_manual(jira_cfg: dict) -> None:
    console.print("\n  Enter one story per line, blank to finish.")
    stories = []
    while True:
        summary = Prompt.ask("  Story summary", default="").strip()
        if not summary:
            break
        stories.append(summary)
    if stories:
        _post_stories(jira_cfg, stories)


def _post_stories(jira_cfg: dict, stories: list[str]) -> None:
    try:
        client      = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
        project_key = jira_cfg["project_key"]
        epic_key    = jira_cfg["epic_key"]
        created = []
        for summary in stories:
            key = jira_mod.create_story(client, project_key, epic_key, summary)
            console.print(f"  [green]Created:[/] [cyan]{key}[/] — {summary}")
            created.append(key)
        console.print(f"\n  [bold]{len(created)}[/] stories created under [cyan]{epic_key}[/]")
    except Exception as e:
        console.print(f"  [red]Jira story creation failed: {e}[/]")


def _try_load_config() -> dict | None:
    try:
        return load_config()
    except FileNotFoundError:
        return None
