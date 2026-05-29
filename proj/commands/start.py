from __future__ import annotations
import re
import shutil
import subprocess
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm

from proj.config import (
    STACKS, CLOUDS, SECRETS_BACKENDS,
    print_stack_menu, load_global_settings, get_nested, save_config, load_config,
)
from proj.integrations import jira as jira_mod
from proj.integrations import claude_code
from proj.integrations import confluence as conf_mod
from proj.integrations import claude_ai
from proj.integrations import cmux as cmux_mod

app = typer.Typer()
console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
PLAN_DIR      = "plans"
PLAN_FILE     = "plans/PLAN.md"

_PLANNING_SYSTEM_PROMPT = """\
You are in PLANNING MODE. Your role is strictly to help the developer think through what they want to build — ask questions, explore the problem, and design the architecture together.

Rules for this session:
- Do NOT write any code
- Do NOT run any commands
- Do NOT scaffold files or directories (other than plans/PLAN.md when explicitly asked)
- Do NOT attempt to implement anything
- Do NOT spawn agents or sub-tasks to implement on your behalf
- ONLY ask questions, discuss trade-offs, and recommend approaches

When the developer is happy with the plan, write it to plans/PLAN.md using your Write tool. The plan should cover:
1. **Problem Summary** — 2-3 sentences restating the problem clearly
2. **Proposed Solution** — high-level architecture and approach
3. **Key Components** — the main pieces that need to be built
4. **Tech Choices** — specific stacks, libraries, services (note each component's stack)
5. **Risks & Open Questions** — unknowns, tradeoffs, things to validate early
6. **Suggested Stories** — numbered list of actionable stories to break the work into

If the developer asks to start building, implement a story, write code, or begin development:
- Do NOT start implementing
- Tell them the plan is ready and they should type /exit to return to the athena CLI
- Remind them the next step is: athena dev\
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def start(
    name:  str = typer.Argument(None, help="Project name"),
    cloud: str = typer.Option(None, "--cloud", "-c", help="Cloud target: azure|aws|gcp|local"),
):
    """Start a project — wiki, plan, and scaffold in one flow. Replaces `athena plan` + `athena new`."""
    config = _try_load_config()
    if config is not None:
        _start_existing(config)
    else:
        _start_new(name, cloud)


# ---------------------------------------------------------------------------
# New project
# ---------------------------------------------------------------------------

def _start_new(name: str | None, cloud: str | None) -> None:
    console.print("\n[bold #a78bfa]athena start[/] — new project\n")
    _gs = load_global_settings()

    # Name
    if name:
        console.print(f"  Project name: [bold]{name}[/]")
    else:
        name = Prompt.ask("  Project name", default=Path.cwd().name).strip()
    if not name:
        raise typer.Exit(0)

    # Cloud
    if cloud:
        if cloud not in CLOUDS:
            console.print(f"[red]Invalid cloud '{cloud}' — must be one of: {', '.join(CLOUDS)}[/]")
            raise typer.Exit(1)
        console.print(f"  Cloud: [cyan]{cloud}[/] [dim](from --cloud flag)[/]")
    else:
        console.print("\n[bold]Step 1/4[/] Cloud target:")
        for i, c in enumerate(CLOUDS, 1):
            console.print(f"  [cyan]{i}[/]. {c}")
        cloud = _pick(CLOUDS, Prompt.ask("  Choice", default="4"), "cloud")

    # Wiki (frontloaded)
    console.print("\n[bold]Step 2/4[/] Wiki documentation")
    conf_cfg, wiki_context = _wiki_setup(_gs)

    # Jira (frontloaded)
    console.print("\n[bold]Step 3/4[/] Jira")
    jira_cfg = _jira_setup(_gs)

    # Project directory + initial athena.yaml
    project_dir = Path(".") if name == Path.cwd().name else Path(name)
    project_dir.mkdir(exist_ok=True)
    (project_dir / PLAN_DIR).mkdir(exist_ok=True)

    init_config: dict = {"name": name, "cloud": cloud, "version": "0.1.0"}
    if jira_cfg:
        init_config["jira"] = jira_cfg
    if conf_cfg:
        init_config["confluence"] = conf_cfg

    proj_yaml = project_dir / "athena.yaml"
    if not proj_yaml.exists():
        with open(proj_yaml, "w") as f:
            yaml.dump(init_config, f, default_flow_style=False, sort_keys=False)
        console.print(f"  [dim]Created {proj_yaml}[/]")

    # git init on project root so athena.yaml and PLAN.md are always tracked
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", f"chore: athena init {name}"],
        cwd=project_dir, capture_output=True,
    )
    if result.returncode != 0 and b"nothing to commit" not in result.stdout + result.stderr:
        console.print(f"  [yellow]git: {result.stderr.decode().strip()}[/]")
    console.print(f"  [dim]git init {project_dir}[/]\n")

    # Plan?
    console.print("\n[bold]Step 4/4[/] Planning")
    plan_text = ""
    if Confirm.ask("  Open a Claude planning session?", default=True):
        existing = _read_plan_if_resume(base=project_dir)
        _open_claude_session(init_config, existing, wiki_context, cwd=project_dir)
        plan_text = _read_plan_or_warn(base=project_dir)
        if not plan_text:
            raise typer.Exit(0)
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "docs: add PLAN.md"],
            cwd=project_dir, capture_output=True,
        )

    # Stack picker
    services = _pick_stacks_post_session(name)

    # Scaffold
    default_secrets = get_nested(_gs, "defaults.secrets_backend") or "dotenv"
    for svc_name, stack in services:
        if Confirm.ask(f"\n  Scaffold [bold]{svc_name}[/] ([cyan]{stack}[/] / [cyan]{cloud}[/])?", default=True):
            _scaffold_service(svc_name, stack, cloud, default_secrets, jira_cfg, conf_cfg)

    # Reload config in case scaffold wrote to it
    try:
        with open(project_dir / "athena.yaml") as f:
            config = yaml.safe_load(f) or {}
    except Exception:
        config = init_config

    if plan_text:
        _jira_post_plan(config, plan_text, root=project_dir)
        _publish_plan_to_confluence(config, plan_text, root=project_dir)
    elif conf_cfg.get("base_url") and conf_cfg.get("token") and conf_cfg.get("space_key"):
        _create_project_wiki_page(config, conf_cfg, root=project_dir)

    console.print(f"\n[bold green]Done![/] Project at [bold]{project_dir.resolve()}[/]")
    console.print(f"  Cloud: [cyan]{cloud}[/]")
    if jira_cfg.get("epic_key"):
        console.print(f"  Jira:  [cyan]{jira_cfg['epic_key']}[/]")
    console.print(f"\nNext: [bold]athena dev[/]")


# ---------------------------------------------------------------------------
# Existing project
# ---------------------------------------------------------------------------

def _start_existing(config: dict) -> None:
    name  = config["name"]
    stack = config.get("stack", "—")
    cloud = config.get("cloud", "local")

    console.print(f"\n[bold #a78bfa]athena start[/] — [bold]{name}[/] ([cyan]{stack}[/] / [cyan]{cloud}[/])\n")

    wiki_context: str | None = None
    if not config.get("confluence"):
        _gs = load_global_settings()
        if get_nested(_gs, "confluence.base_url"):
            console.print("[bold]Wiki documentation[/]")
            conf_cfg, wiki_context = _wiki_setup(_gs)
            if conf_cfg:
                config["confluence"] = conf_cfg
                try:
                    save_config(config)
                except Exception:
                    pass

    if stack == "—":
        want_plan = True
        console.print("[dim]No stack set — opening planning session.[/]\n")
    else:
        want_plan = Confirm.ask("  Open a re-planning session with Claude?", default=False)

    if want_plan:
        existing_plan: str | None = None
        if Path(PLAN_FILE).exists():
            existing_plan = Path(PLAN_FILE).read_text(encoding="utf-8")
            console.print(f"[dim]Loaded {PLAN_FILE}[/]\n")
        _open_claude_session(config, existing_plan, wiki_context)
        plan_text = _read_plan_or_warn()
        if plan_text:
            _jira_post_plan(config, plan_text)
            _publish_plan_to_confluence(config, plan_text)
    else:
        console.print(f"\n[dim]Next:[/] [bold]athena dev[/]")


# ---------------------------------------------------------------------------
# Wiki setup (frontloaded)
# ---------------------------------------------------------------------------

def _wiki_setup(gs: dict) -> tuple[dict, str | None]:
    """Returns (conf_cfg, wiki_context_text). wiki_context is set when an existing page is linked."""
    base_url  = get_nested(gs, "confluence.base_url") or ""
    token     = get_nested(gs, "confluence.token") or ""
    space_key = get_nested(gs, "confluence.space_key") or ""

    console.print("  [cyan]1[/]. Link an existing wiki page [dim](loads content as planning context)[/]")
    console.print("  [cyan]2[/]. Create a new project wiki page")
    console.print("  [cyan]3[/]. Skip [dim](default)[/]")
    choice = Prompt.ask("  Choice", default="3").strip()

    if choice not in ("1", "2"):
        return {}, None

    if base_url:
        console.print(f"  Base URL: [cyan]{base_url}[/] [dim](from settings)[/]")
    else:
        base_url = Prompt.ask("  Confluence base URL", default="https://wiki.corp.adobe.com").strip()
    if not base_url:
        return {}, None

    if token:
        console.print(f"  Token: [dim](from settings)[/]")
    else:
        token = Prompt.ask("  Personal access token", password=True)
    if not token:
        return {}, None

    if space_key:
        console.print(f"  Space: [cyan]{space_key}[/] [dim](from settings)[/]")
    else:
        space_key = Prompt.ask("  Space key (e.g. ENG)", default="").strip() or None

    conf_cfg: dict = {
        "base_url": base_url, "token": token, "space_key": space_key,
        "project_page_id": None, "plan_page_id": None, "release_page_id": None,
    }

    if choice == "1":
        raw = Prompt.ask("  Page ID or URL").strip()
        page_id = _parse_page_id(raw)
        if not page_id:
            console.print("  [yellow]Could not parse page ID — skipping wiki.[/]")
            return {}, None
        console.print(f"  Fetching page {page_id}...", end=" ")
        try:
            client = conf_mod.connect(base_url, token)
            title, content = conf_mod.get_page_content(client, page_id)
            console.print(f"[green]OK[/] — [dim]{title}[/]")
            conf_cfg["project_page_id"] = page_id
            return conf_cfg, f"**Wiki spec: {title}**\n\n{content[:4000]}"
        except Exception as e:
            console.print(f"[red]failed — {e}[/]")
            return conf_cfg, None

    # choice == "2": page created after planning
    return conf_cfg, None


# ---------------------------------------------------------------------------
# Jira setup (frontloaded)
# ---------------------------------------------------------------------------

def _jira_setup(gs: dict) -> dict:
    base_url    = get_nested(gs, "jira.base_url") or ""
    token       = get_nested(gs, "jira.token") or ""
    project_key = get_nested(gs, "jira.project_key") or ""

    if not (base_url and token):
        console.print("  [dim]Jira not in global settings — skipping. Run [bold]athena settings[/] to configure.[/]")
        return {}

    console.print(f"  Base URL: [cyan]{base_url}[/] [dim](from settings)[/]")
    if project_key:
        console.print(f"  Project key: [cyan]{project_key}[/] [dim](from settings)[/]")
    else:
        project_key = Prompt.ask("  Project key (e.g. BPOE)", default="").strip() or None

    raw_epic = Prompt.ask(
        "  Epic key (e.g. " + (project_key or "BPOE") + "-1), or Enter to skip",
        default="",
    ).strip()
    epic_key = _normalize_jira_key(raw_epic, project_key) if raw_epic else None

    return {
        "base_url": base_url, "token": token,
        "project_key": project_key, "epic_key": epic_key,
        "stakeholders": [],
    }


# ---------------------------------------------------------------------------
# Claude planning session
# ---------------------------------------------------------------------------

def _open_claude_session(
    config: dict,
    existing_plan: str | None,
    wiki_context: str | None,
    cwd: Path | None = None,
) -> None:
    name     = config["name"]
    cloud    = config.get("cloud", "local")
    stack    = config.get("stack")
    jira_cfg = config.get("jira", {})
    epic_key = jira_cfg.get("epic_key", "none")
    secrets  = config.get("secrets_backend", "dotenv")
    version  = config.get("version", "0.1.0")

    stack_line   = f"- Stack: {stack}\n" if stack else "- Stack: TBD — help the developer decide\n"
    wiki_block   = f"\n\n**Wiki specification (use as source of truth):**\n\n{wiki_context}" if wiki_context else ""
    resume_block = (
        f"\n\nExisting plan to continue refining:\n\n```markdown\n{existing_plan}\n```\n\nPick up from where we left off."
        if existing_plan else ""
    )

    initial_message = (
        f"**Project context**\n"
        f"- Name: {name}\n"
        f"- Cloud: {cloud}\n"
        f"{stack_line}"
        f"- Secrets: {secrets}\n"
        f"- Jira epic: {epic_key}\n"
        f"- Version: {version}"
        f"{wiki_block}"
        f"{resume_block}\n\n"
        f"Start by asking what the developer wants to build or solve."
    )

    if cwd is None:
        Path(PLAN_DIR).mkdir(exist_ok=True)

    console.print("\n[bold]Opening Claude Code[/] — planning mode.")
    console.print("[dim]Chat naturally. Claude cannot run commands or write code in this session.[/]")
    console.print("[dim]When ready, say 'write the plan' — Claude will create plans/PLAN.md.[/]")
    console.print("[dim]Type /exit or Ctrl+C when done.\n[/]")

    try:
        subprocess.run(
            ["claude", "--allowedTools", "Write", "--append-system-prompt", _PLANNING_SYSTEM_PROMPT, initial_message],
            cwd=cwd,
        )
    except FileNotFoundError:
        console.print("[red]`claude` not found.[/] Install Claude Code: https://claude.ai/code")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Stack picker
# ---------------------------------------------------------------------------

def _pick_stacks_post_session(project_name: str) -> list[tuple[str, str]]:
    console.print("\n[bold]Stacks to scaffold[/] [dim](leave blank to skip)[/]\n")
    print_stack_menu(console)

    raw = Prompt.ask("\n  Stack numbers (e.g. 2,9)", default="").strip()
    if not raw:
        return []

    chosen: list[str] = []
    for part in raw.split(","):
        try:
            idx = int(part.strip()) - 1
            if 0 <= idx < len(STACKS):
                chosen.append(STACKS[idx])
        except ValueError:
            pass

    if not chosen:
        return []

    console.print(f"\n  {len(chosen)} stack(s) selected. Name each service:\n")
    services: list[tuple[str, str]] = []
    for stack in chosen:
        suffix  = stack.split("-")[0]
        default = project_name if len(chosen) == 1 else f"{project_name}-{suffix}"
        svc     = Prompt.ask(f"  Service name for [cyan]{stack}[/]", default=default).strip()
        if svc:
            services.append((svc, stack))
    return services


# ---------------------------------------------------------------------------
# Scaffolding
# ---------------------------------------------------------------------------

def _scaffold_service(
    svc_name: str,
    stack: str,
    cloud: str,
    secrets_backend: str,
    jira_cfg: dict,
    conf_cfg: dict,
) -> None:
    console.print(f"\n  Scaffolding [bold]{svc_name}[/] ([cyan]{stack}[/])...")

    project_dir = Path(".") if svc_name == Path.cwd().name else Path(svc_name)

    if project_dir.exists() and (project_dir / "athena.yaml").exists():
        console.print(f"  [yellow]{project_dir} already has an athena.yaml — skipping.[/]")
        return

    template_src = TEMPLATES_DIR / stack
    if not project_dir.exists():
        if template_src.exists():
            shutil.copytree(template_src, project_dir)
        else:
            project_dir.mkdir(parents=True)

    config: dict = {
        "name":            svc_name,
        "stack":           stack,
        "cloud":           cloud,
        "secrets_backend": secrets_backend,
        "version":         "0.1.0",
    }
    if jira_cfg:
        config["jira"] = jira_cfg
    if conf_cfg:
        config["confluence"] = conf_cfg

    with open(project_dir / "athena.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    env_ex = project_dir / ".env.example"
    if not env_ex.exists():
        env_ex.write_text("# Copy to .env and fill in values\n# DATABASE_URL=\n# SECRET_KEY=\n")

    gi = project_dir / ".gitignore"
    if not gi.exists():
        gi.write_text(".env\n.venv\n__pycache__\n*.pyc\ndist/\n.DS_Store\n")

    console.print("  Generating CLAUDE.md...", end=" ")
    claude_code.scaffold(project_dir, config)
    console.print("[green]OK[/]")

    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", f"chore: athena init {svc_name}"],
        cwd=project_dir, capture_output=True,
    )
    if result.returncode != 0 and b"nothing to commit" not in result.stdout + result.stderr:
        console.print(f"  [yellow]git: {result.stderr.decode().strip()}[/]")

    if jira_cfg.get("base_url") and jira_cfg.get("token") and jira_cfg.get("epic_key"):
        try:
            client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
            body = (
                f"*Project scaffolded via athena CLI*\n\n"
                f"- *Name:* {svc_name}\n- *Stack:* {stack}\n"
                f"- *Cloud:* {cloud}\n- *Version:* 0.1.0"
            )
            jira_mod.post_comment(client, jira_cfg["epic_key"], body)
        except Exception:
            pass

    console.print(f"  [green]Done[/] — {project_dir.resolve()}")


# ---------------------------------------------------------------------------
# Confluence project page (when no plan exists)
# ---------------------------------------------------------------------------

def _create_project_wiki_page(config: dict, conf_cfg: dict, root: Path = Path(".")) -> None:
    base_url  = conf_cfg.get("base_url")
    token     = conf_cfg.get("token")
    space_key = conf_cfg.get("space_key")
    if not all([base_url, token, space_key]):
        return
    if conf_cfg.get("project_page_id"):
        return  # already linked to an existing page

    name  = config["name"]
    stack = config.get("stack", "TBD")
    cloud = config.get("cloud", "local")
    epic  = config.get("jira", {}).get("epic_key", "—")

    console.print("  Creating Confluence project page...", end=" ")
    try:
        client  = conf_mod.connect(base_url, token)
        body    = (
            f"# {name}\n\n"
            f"| Key | Value |\n|---|---|\n"
            f"| Stack | `{stack}` |\n| Cloud | `{cloud}` |\n"
            f"| Jira Epic | {epic} |\n| Version | 0.1.0 |\n\n"
            f"## Pages\n\n- **Project Plan** — created by `athena start`\n"
            f"- **Release Notes** — updated by `athena release`\n"
        )
        page_id = conf_mod.create_page(client, space_key, name, body)
        conf_cfg["project_page_id"] = page_id
        config["confluence"] = conf_cfg
        save_config(config, root=root)
        console.print(f"[green]OK[/]  [dim]{conf_mod.get_page_url(base_url, page_id)}[/]")
    except Exception as e:
        console.print(f"[red]failed — {e}[/]")


# ---------------------------------------------------------------------------
# Confluence plan publish
# ---------------------------------------------------------------------------

def _publish_plan_to_confluence(config: dict, plan_text: str, root: Path = Path(".")) -> None:
    conf_cfg  = config.get("confluence", {})
    base_url  = conf_cfg.get("base_url")
    token     = conf_cfg.get("token")
    space_key = conf_cfg.get("space_key")
    if not all([base_url, token, space_key]):
        return
    if not Confirm.ask("\n  Publish plan to Confluence?", default=True):
        return

    name  = config["name"]
    title = f"{name} — Project Plan"
    try:
        client       = conf_mod.connect(base_url, token)
        plan_page_id = conf_cfg.get("plan_page_id")
        parent_id    = conf_cfg.get("project_page_id")

        if plan_page_id:
            conf_mod.update_page(client, plan_page_id, title, plan_text)
            console.print("  [green]Confluence plan page updated[/]")
        else:
            plan_page_id = conf_mod.create_page(client, space_key, title, plan_text, parent_id=parent_id)
            conf_cfg["plan_page_id"] = plan_page_id
            config["confluence"] = conf_cfg
            save_config(config, root=root)
            console.print("  [green]Confluence plan page created[/]")

        console.print(f"  [dim]{conf_mod.get_page_url(base_url, plan_page_id)}[/]")
    except Exception as e:
        console.print(f"  [yellow]Confluence publish failed: {e}[/]")


# ---------------------------------------------------------------------------
# Jira post-plan
# ---------------------------------------------------------------------------

def _jira_post_plan(config: dict, plan_text: str, root: Path = Path(".")) -> None:
    _gs         = load_global_settings()
    jira_cfg    = config.get("jira", {})
    base_url    = jira_cfg.get("base_url")    or get_nested(_gs, "jira.base_url")
    token       = jira_cfg.get("token")       or get_nested(_gs, "jira.token")
    project_key = jira_cfg.get("project_key") or get_nested(_gs, "jira.project_key")
    epic_key    = jira_cfg.get("epic_key")

    if not all([base_url, token]):
        console.print("\n  [dim]Jira not configured — skipping story creation.[/]")
        return

    if not epic_key:
        raw = Prompt.ask(
            "\n  Epic key (e.g. " + (project_key or "BPOE") + "-1), or Enter to skip",
            default="",
        ).strip()
        epic_key = _normalize_jira_key(raw, project_key) if raw else None

    config.setdefault("jira", {})
    config["jira"].update({k: v for k, v in {
        "base_url": base_url, "token": token,
        "project_key": project_key, "epic_key": epic_key,
    }.items() if v})
    try:
        save_config(config, root=root)
    except Exception:
        pass

    jira_cfg = config["jira"]
    epic_label = f" under [cyan]{epic_key}[/]" if epic_key else " [dim](no Epic linked)[/]"
    console.print(f"\n[bold]Jira stories[/]{epic_label}")
    console.print("  [cyan]1[/]. Extract stories from plan via Claude")
    console.print("  [cyan]2[/]. Enter stories manually")
    console.print("  [cyan]3[/]. Skip")
    choice = Prompt.ask("  Choice", default="1").strip()

    if choice == "1":
        _create_stories_from_plan(config, jira_cfg, plan_text)
    elif choice == "2":
        _create_stories_manual(jira_cfg)
    else:
        if epic_key:
            try:
                client = jira_mod.connect(base_url, token)
                story  = _pick_plan_story(client, epic_key)
                if story:
                    jira_mod.save_active_ticket(story)
                    console.print(f"  [dim]Active story: {story}[/]")
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Jira story helpers
# ---------------------------------------------------------------------------

def _create_stories_from_plan(config: dict, jira_cfg: dict, plan_text: str) -> None:
    console.print("\n  Extracting stories...")
    stories = claude_ai.extract_stories(plan_text, config)
    if not stories:
        console.print("  [yellow]No stories extracted.[/]")
        return

    epic_key = jira_cfg.get("epic_key", "")
    existing: list = []
    try:
        client   = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
        existing = jira_mod.get_all_stories(client, epic_key)
        if existing:
            console.print(f"\n  [bold]Existing stories[/] in [cyan]{epic_key}[/]:\n")
            for s in existing:
                status = s["fields"]["status"]["name"]
                style  = "dim" if status.lower() in ("done", "closed") else "white"
                console.print(f"    [{style}][cyan]{s['key']}[/] [{status}] {s['fields']['summary']}[/]")
    except Exception:
        pass

    console.print(f"\n  [bold]Stories from plan[/] ({len(stories)}):\n")
    for i, s in enumerate(stories, 1):
        console.print(f"    [cyan]{i}[/]. {s}")

    if not Confirm.ask("\n  Create all in Jira?", default=True):
        raw = Prompt.ask("  Numbers to create (e.g. 1,3) or blank to skip", default="").strip()
        if not raw:
            return
        selected = []
        for part in raw.split(","):
            try:
                idx = int(part.strip()) - 1
                if 0 <= idx < len(stories):
                    selected.append(stories[idx])
            except ValueError:
                pass
        _post_stories(jira_cfg, selected)
    else:
        _post_stories(jira_cfg, stories)


def _create_stories_manual(jira_cfg: dict) -> None:
    epic_key = jira_cfg.get("epic_key", "")
    try:
        client   = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
        existing = jira_mod.get_all_stories(client, epic_key)
        if existing:
            console.print(f"\n  [bold]Existing stories[/] in [cyan]{epic_key}[/]:\n")
            for s in existing:
                style = "dim" if s["fields"]["status"]["name"].lower() in ("done", "closed") else "white"
                console.print(f"    [{style}][cyan]{s['key']}[/] {s['fields']['summary']}[/]")
    except Exception:
        pass
    console.print("\n  Enter one story per line, blank to finish.")
    stories = []
    while True:
        summary = Prompt.ask("  Story", default="").strip()
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
        created: list[str] = []
        for summary in stories:
            key = jira_mod.create_story(client, project_key, epic_key, summary)
            console.print(f"  [green]Created:[/] [cyan]{key}[/] — {summary}")
            created.append(key)
        console.print(f"\n  [bold]{len(created)}[/] {'story' if len(created) == 1 else 'stories'} created under [cyan]{epic_key}[/]")

        plan_story = _pick_plan_story(client, epic_key, newly_created=created)
        if plan_story:
            jira_mod.save_active_ticket(plan_story)
            console.print(f"  [dim]Active story: {plan_story}[/]")

        if created:
            body = (
                f"*Planning complete — {len(created)} {'story' if len(created) == 1 else 'stories'} added*\n\n"
                + "\n".join(f"- [{k}]" for k in created)
                + "\n\n_Review stories before starting development._"
            )
            jira_mod.post_status_log(client, body, epic_key, plan_story)
    except Exception as e:
        console.print(f"  [red]Jira story creation failed: {e}[/]")


def _pick_plan_story(client, epic_key: str, newly_created: list[str] | None = None) -> str | None:
    try:
        open_stories = jira_mod.get_open_tickets(client, epic_key)
    except Exception:
        return None
    if not open_stories:
        return None

    new_set = set(newly_created or [])
    console.print(f"\n  [bold]Link plan to a story[/] under [cyan]{epic_key}[/]:\n")
    console.print("  [cyan]0[/]. Skip")
    for i, s in enumerate(open_stories, 1):
        tag = " [dim](new)[/]" if s["key"] in new_set else ""
        console.print(f"  [cyan]{i}[/]. [cyan]{s['key']}[/] — {s['fields']['summary']}{tag}")

    raw = Prompt.ask("\n  Choice", default="0").strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(open_stories):
            return open_stories[idx]["key"]
    except ValueError:
        pass
    return None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _try_load_config() -> dict | None:
    try:
        return load_config()
    except FileNotFoundError:
        return None


def _read_plan_if_resume(base: Path = Path(".")) -> str | None:
    p = base / PLAN_FILE
    return p.read_text(encoding="utf-8") if p.exists() else None


def _read_plan_or_warn(base: Path = Path(".")) -> str:
    p = base / PLAN_FILE
    if p.exists():
        console.print(f"\n[green]Plan saved:[/] [bold]{p}[/]")
        cmux_mod.notify("Plan saved", str(p))
        cmux_mod.log(f"Plan written to {p}", level="success", source="athena start")
        return p.read_text(encoding="utf-8")
    console.print(f"\n[yellow]No {p} found.[/] Ask Claude to write it, or run [bold]athena start[/] again.")
    return ""


def _pick(options: list[str], raw: str, label: str) -> str:
    try:
        idx = int(raw) - 1
    except ValueError:
        idx = -1
    if not (0 <= idx < len(options)):
        console.print(f"[red]Invalid {label} — must be 1–{len(options)}.[/]")
        raise typer.Exit(1)
    return options[idx]


def _normalize_jira_key(raw: str, project_key: str | None) -> str:
    raw = raw.strip().upper()
    if project_key and raw.isdigit():
        return f"{project_key.upper()}-{raw}"
    return raw


def _parse_page_id(raw: str) -> str | None:
    raw = raw.strip()
    if raw.isdigit():
        return raw
    m = re.search(r"pageId=(\d+)", raw)
    return m.group(1) if m else None
