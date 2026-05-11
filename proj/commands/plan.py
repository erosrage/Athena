from __future__ import annotations
import subprocess
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm

from proj.config import STACKS, CLOUDS, load_config, print_stack_menu
from proj.integrations import claude_ai
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()

PLAN_FILE = "PLAN.md"

_PLANNING_SYSTEM_PROMPT = """\
You are in PLANNING MODE. Your role is strictly to help the developer think through what they want to build — ask questions, explore the problem, and design the architecture together.

Rules for this session:
- Do NOT write any code
- Do NOT run any commands
- Do NOT scaffold files or directories (other than PLAN.md when explicitly asked)
- Do NOT attempt to implement anything
- Do NOT spawn agents or sub-tasks to implement on your behalf
- ONLY ask questions, discuss trade-offs, and recommend approaches

When the developer is happy with the plan, write it to PLAN.md using your Write tool. The plan should cover:
1. **Problem Summary** — 2-3 sentences restating the problem clearly
2. **Proposed Solution** — high-level architecture and approach
3. **Key Components** — the main pieces that need to be built
4. **Tech Choices** — specific stacks, libraries, services (note each component's stack)
5. **Risks & Open Questions** — unknowns, tradeoffs, things to validate early
6. **Suggested Stories** — numbered list of actionable stories to break the work into

If the developer asks to start building, implement a story, write code, or begin development:
- Do NOT start implementing
- Tell them the plan is ready and they should type /exit to return to the proj CLI
- Remind them the next step is: proj new <name> to scaffold, then proj dev to start coding\
"""


@app.callback(invoke_without_command=True)
def plan(
    name:   str  = typer.Argument(None, help="Project name (skips the name prompt)"),
    resume: bool = typer.Option(False, "--resume", help="Continue from an existing PLAN.md"),
    cloud:  str  = typer.Option(None, "--cloud", "-c", help="Cloud target: azure|aws|gcp|local (skips cloud picker)"),
):
    """LLM-assisted solutioning — opens a Claude Code session to brainstorm and architect."""

    if cloud and cloud not in CLOUDS:
        console.print(f"[red]Invalid cloud '{cloud}' — must be one of: {', '.join(CLOUDS)}[/]")
        raise typer.Exit(1)

    config = _try_load_config()
    if config is not None:
        _plan_existing(config, resume)
    else:
        _plan_new(resume, name, cloud)


# ---------------------------------------------------------------------------
# Pre-scaffold mode — no proj.yaml yet
# ---------------------------------------------------------------------------

def _plan_new(resume: bool, name: str | None = None, cloud: str | None = None) -> None:
    console.print("\n[bold #a78bfa]proj plan[/] — new project\n")
    console.print("[dim]No proj.yaml found — let's figure out what you're building first.[/]\n")

    if name:
        console.print(f"  Project name: [bold]{name}[/]")
    else:
        name = Prompt.ask("  Project name").strip()
    if not name:
        raise typer.Exit(0)

    if cloud:
        console.print(f"  Cloud target: [cyan]{cloud}[/] [dim](from --cloud flag)[/]")
    else:
        console.print("\n  Pick a cloud target: [dim](infrastructure constraint — shapes the conversation)[/]")
        for i, c in enumerate(CLOUDS, 1):
            console.print(f"    [cyan]{i}[/]. {c}")
        cloud = _pick(CLOUDS, Prompt.ask("  Choice", default="4"), "cloud")

    existing_plan = _read_plan_if_resume(resume)
    _open_claude_session({"name": name, "cloud": cloud}, existing_plan)

    plan_text = _read_plan_or_warn()
    if not plan_text:
        raise typer.Exit(0)

    # Post-session: ask which stacks were decided
    services = _pick_stacks_post_session(name)

    if not services:
        console.print(f"\n[dim]When ready:[/] [bold]proj new {name}[/]")
        return

    scaffolded: list[str] = []
    console.print()
    for svc_name, stack in services:
        if Confirm.ask(f"  Scaffold [bold]{svc_name}[/] ([cyan]{stack}[/] / [cyan]{cloud}[/])?", default=True):
            console.print()
            subprocess.run(
                [sys.executable, "-m", "proj", "new", svc_name,
                 "--stack", stack, "--cloud", cloud],
                check=False,
            )
            scaffolded.append(svc_name)

    # Offer Jira story creation from plan using the first scaffolded service's config
    if scaffolded and plan_text:
        _maybe_create_stories_new_project(scaffolded[0], plan_text)


# ---------------------------------------------------------------------------
# Existing project mode — proj.yaml present
# ---------------------------------------------------------------------------

def _plan_existing(config: dict, resume: bool) -> None:
    name  = config["name"]
    stack = config.get("stack", "unknown")
    cloud = config.get("cloud", "local")

    console.print(f"\n[bold #a78bfa]proj plan[/] — [bold]{name}[/] ([cyan]{stack}[/] / [cyan]{cloud}[/])\n")

    # Always load existing plan when inside a project — no flag needed
    existing_plan = None
    if Path(PLAN_FILE).exists():
        existing_plan = Path(PLAN_FILE).read_text(encoding="utf-8")
        console.print(f"[dim]Loaded existing {PLAN_FILE}[/]\n")

    _open_claude_session(config, existing_plan)

    plan_text = _read_plan_or_warn()
    if not plan_text:
        raise typer.Exit(0)

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
# Native Claude Code session
# ---------------------------------------------------------------------------

def _open_claude_session(config: dict, existing_plan: str | None) -> None:
    """Hand off to a full interactive Claude Code session with project context pre-loaded."""
    name    = config["name"]
    cloud   = config.get("cloud", "local")
    stack   = config.get("stack")          # None for new projects — Claude will recommend
    jira_cfg  = config.get("jira", {})
    epic_key  = jira_cfg.get("epic_key", "none")
    secrets   = config.get("secrets_backend", "dotenv")
    version   = config.get("version", "0.1.0")

    stack_line = f"- Stack: {stack}\n" if stack else "- Stack: TBD — help the developer decide\n"

    if existing_plan:
        resume_block = (
            f"\n\nThere is an existing plan to continue refining:\n\n"
            f"```markdown\n{existing_plan}\n```\n\n"
            f"Pick up from where we left off."
        )
    else:
        resume_block = ""

    initial_message = (
        f"**Project context**\n"
        f"- Name: {name}\n"
        f"- Cloud target: {cloud}\n"
        f"{stack_line}"
        f"- Secrets backend: {secrets}\n"
        f"- Jira epic: {epic_key}\n"
        f"- Version: {version}\n"
        f"{resume_block}\n\n"
        f"Start by asking what the developer wants to build or solve."
    )

    console.print("\n[bold]Opening Claude Code[/] — planning mode.")
    console.print("[dim]Chat naturally. Claude cannot run commands or write code in this session.[/]")
    console.print("[dim]When you have a plan, say 'write the plan' — Claude will create PLAN.md.[/]")
    console.print("[dim]Type /exit or Ctrl+C when done.\n[/]")

    try:
        subprocess.run([
            "claude",
            "--allowedTools", "Write",
            "--append-system-prompt", _PLANNING_SYSTEM_PROMPT,
            initial_message,
        ])
    except FileNotFoundError:
        console.print("[red]`claude` not found.[/] Install Claude Code: https://claude.ai/code")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Post-session multi-stack picker
# ---------------------------------------------------------------------------

def _pick_stacks_post_session(project_name: str) -> list[tuple[str, str]]:
    """Ask which stacks were decided in the Claude session. Returns [(service_name, stack)]."""
    console.print("\n[bold]What stacks did you land on?[/]")
    console.print("[dim]Enter the numbers from the menu, comma-separated. Leave blank to skip scaffolding.[/]\n")
    print_stack_menu(console)

    raw = Prompt.ask("\n  Stack numbers (e.g. 2,9 or just 2)", default="").strip()
    if not raw:
        return []

    chosen_stacks: list[str] = []
    skipped: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        try:
            idx = int(part) - 1
            if 0 <= idx < len(STACKS):
                chosen_stacks.append(STACKS[idx])
            else:
                skipped.append(part)
        except ValueError:
            skipped.append(part)

    if skipped:
        console.print(f"  [yellow]Skipped invalid entries: {', '.join(skipped)}[/]")

    if not chosen_stacks:
        return []

    console.print(f"\n  [bold]{len(chosen_stacks)}[/] stack(s) selected. Name each service:\n")
    services: list[tuple[str, str]] = []
    for stack in chosen_stacks:
        if len(chosen_stacks) == 1:
            default_name = project_name
        else:
            # e.g. my-app-api, my-app-web
            suffix = stack.split("-")[0]   # fastapi → fastapi, react → react
            default_name = f"{project_name}-{suffix}"
        svc_name = Prompt.ask(f"  Service name for [cyan]{stack}[/]", default=default_name).strip()
        if svc_name:
            services.append((svc_name, stack))

    return services


# ---------------------------------------------------------------------------
# Jira story helpers
# ---------------------------------------------------------------------------

def _maybe_create_stories_new_project(svc_name: str, plan_text: str) -> None:
    """After proj new scaffolds a service, offer Jira story creation if Jira is configured."""
    import yaml
    proj_yaml = Path(svc_name) / "proj.yaml"
    if not proj_yaml.exists():
        return
    with open(proj_yaml) as f:
        config = yaml.safe_load(f)
    jira_cfg    = config.get("jira", {})
    base_url    = jira_cfg.get("base_url")
    token       = jira_cfg.get("token")
    project_key = jira_cfg.get("project_key")
    epic_key    = jira_cfg.get("epic_key")
    if not all([base_url, token, project_key, epic_key]):
        return
    console.print(f"\n[bold]Jira stories[/] — create stories from your plan under [cyan]{epic_key}[/]?")
    console.print("  [cyan]1[/]. Extract stories from plan via Claude")
    console.print("  [cyan]2[/]. Enter stories manually")
    console.print("  [cyan]3[/]. Skip")
    choice = Prompt.ask("  Choice", default="1").strip()
    if choice == "1":
        _create_stories_from_plan(config, jira_cfg, plan_text)
    elif choice == "2":
        _create_stories_manual(jira_cfg)
    else:
        console.print("  [dim]Skipped — run proj plan inside the project later to add stories.[/]")


def _create_stories_from_plan(config: dict, jira_cfg: dict, plan_text: str) -> None:
    console.print("\n  Extracting stories from plan...")
    new_stories = claude_ai.extract_stories(plan_text, config)

    if not new_stories:
        console.print("  [yellow]No stories extracted.[/]")
        return

    # Show existing Jira stories so the user can judge what's actually new
    epic_key = jira_cfg.get("epic_key", "")
    try:
        client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
        existing = jira_mod.get_all_stories(client, epic_key)
        if existing:
            console.print(f"\n  [bold]Existing stories[/] in [cyan]{epic_key}[/]:\n")
            for s in existing:
                status = s["fields"]["status"]["name"]
                summary = s["fields"]["summary"]
                key = s["key"]
                style = "dim" if status.lower() in ("done", "closed") else "white"
                console.print(f"    [{style}][cyan]{key}[/] [{status}] {summary}[/]")
    except Exception:
        existing = []

    console.print(f"\n  [bold]Stories from revised plan[/] ({len(new_stories)}):\n")
    for i, s in enumerate(new_stories, 1):
        console.print(f"    [cyan]{i}[/]. {s}")

    console.print()
    if existing:
        console.print("  [dim]Review the lists above — skip any that already exist.[/]")

    if not Confirm.ask("  Create all of these in Jira?", default=True):
        # Let user pick which ones to create
        raw = Prompt.ask(
            "  Enter numbers to create (e.g. 1,3,5) or blank to skip all",
            default="",
        ).strip()
        if not raw:
            console.print("  [dim]Skipped.[/]")
            return
        selected = []
        for part in raw.split(","):
            try:
                idx = int(part.strip()) - 1
                if 0 <= idx < len(new_stories):
                    selected.append(new_stories[idx])
            except ValueError:
                pass
        _post_stories(jira_cfg, selected)
    else:
        _post_stories(jira_cfg, new_stories)


def _create_stories_manual(jira_cfg: dict) -> None:
    epic_key = jira_cfg.get("epic_key", "")
    try:
        client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
        existing = jira_mod.get_all_stories(client, epic_key)
        if existing:
            console.print(f"\n  [bold]Existing stories[/] in [cyan]{epic_key}[/]:\n")
            for s in existing:
                status = s["fields"]["status"]["name"]
                key = s["key"]
                style = "dim" if status.lower() in ("done", "closed") else "white"
                console.print(f"    [{style}][cyan]{key}[/] [{status}] {s['fields']['summary']}[/]")
    except Exception:
        pass
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


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _read_plan_if_resume(resume: bool) -> str | None:
    if resume and Path(PLAN_FILE).exists():
        console.print(f"[dim]Resuming from {PLAN_FILE}[/]\n")
        return Path(PLAN_FILE).read_text(encoding="utf-8")
    return None


def _read_plan_or_warn() -> str:
    if Path(PLAN_FILE).exists():
        console.print(f"\n[green]Plan saved to[/] [bold]{PLAN_FILE}[/]")
        return Path(PLAN_FILE).read_text(encoding="utf-8")
    console.print(
        f"\n[yellow]No {PLAN_FILE} found.[/] "
        "Ask Claude to write it next time, or run [bold]proj plan[/] again."
    )
    return ""


def _pick(options: list[str], raw: str, label: str) -> str:
    try:
        idx = int(raw) - 1
    except ValueError:
        idx = -1
    if not (0 <= idx < len(options)):
        console.print(f"[red]Invalid {label} choice — must be 1–{len(options)}.[/]")
        raise typer.Exit(1)
    return options[idx]


def _try_load_config() -> dict | None:
    try:
        return load_config()
    except FileNotFoundError:
        return None
