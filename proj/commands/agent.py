from __future__ import annotations
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from proj.config import load_config, STACKS, cli_argv
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()

# ---------------------------------------------------------------------------
# Tool definitions — the athena surface exposed to the agent
# ---------------------------------------------------------------------------

_TOOLS = [
    {
        "name": "athena_status",
        "description": (
            "Get the current project status: name, stack, cloud, version, "
            "secrets backend, git branch, last tag, and Jira Epic with open tickets."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "athena_build",
        "description": "Build the project (docker build + registry push, wheel upload, swift build, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "multi_arch": {"type": "boolean", "description": "Build for linux/amd64 + linux/arm64"},
                "no_push":    {"type": "boolean", "description": "Skip pushing image to registry"},
                "no_jira":    {"type": "boolean", "description": "Skip Jira ticket transition and comment"},
            },
            "required": [],
        },
    },
    {
        "name": "athena_release",
        "description": "Release: bump version, update CHANGELOG, git tag, deploy, notify Jira.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bump":      {"type": "string", "enum": ["patch", "minor", "major"], "description": "Version bump type (default: patch)"},
                "dry_run":   {"type": "boolean", "description": "Preview changes without writing anything"},
                "no_deploy": {"type": "boolean", "description": "Skip the deploy step"},
                "no_jira":   {"type": "boolean", "description": "Skip Jira comment and ticket transition"},
            },
            "required": [],
        },
    },
    {
        "name": "jira_list_tickets",
        "description": "List all open Jira tickets in the project's Epic.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "jira_create_ticket",
        "description": "Create a new Jira story in the project's Epic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary":     {"type": "string", "description": "One-line ticket title"},
                "description": {"type": "string", "description": "Ticket body (optional)"},
            },
            "required": ["summary"],
        },
    },
    {
        "name": "jira_transition_ticket",
        "description": "Transition a Jira ticket to a new status (e.g. In Progress, In Review, Done).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string", "description": "Jira ticket key, e.g. PROJ-42"},
                "status":     {"type": "string", "description": "Target status name"},
            },
            "required": ["ticket_key", "status"],
        },
    },
    {
        "name": "jira_comment",
        "description": "Post a status comment on a Jira ticket or Epic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key":  {"type": "string", "description": "Jira issue key (ticket or Epic)"},
                "body": {"type": "string", "description": "Comment body (Jira wiki markup supported)"},
            },
            "required": ["key", "body"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from the project directory (e.g. PLAN.md, CHANGELOG.md, athena.yaml).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to current directory"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "shell",
        "description": (
            "Run a shell command and return stdout + stderr. "
            "Use for git, docker inspection, or diagnostic commands. "
            "Do NOT use to run athena commands — use the dedicated athena_* tools instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
            },
            "required": ["command"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def _run_proj(*args: str) -> str:
    result = subprocess.run(
        cli_argv(*args),
        capture_output=True, text=True,
    )
    return (result.stdout + result.stderr).strip()


def _execute_tool(name: str, args: dict, config: dict | None) -> str:
    try:
        if name == "athena_status":
            return _run_proj("status")

        if name == "athena_build":
            cmd = ["build"]
            if args.get("multi_arch"): cmd.append("--multi-arch")
            if args.get("no_push"):    cmd.append("--no-push")
            if args.get("no_jira"):    cmd.append("--no-jira")
            return _run_proj(*cmd)

        if name == "athena_release":
            cmd = ["release", "--bump", args.get("bump", "patch")]
            if args.get("dry_run"):   cmd.append("--dry-run")
            if args.get("no_deploy"): cmd.append("--no-deploy")
            if args.get("no_jira"):   cmd.append("--no-jira")
            return _run_proj(*cmd)

        if name == "jira_list_tickets":
            if not config:
                return "No athena.yaml found."
            jira_cfg = config.get("jira", {})
            base_url = jira_cfg.get("base_url")
            token    = jira_cfg.get("token")
            epic_key = jira_cfg.get("epic_key")
            if not all([base_url, token, epic_key]):
                return "Jira not configured in athena.yaml."
            client  = jira_mod.connect(base_url, token)
            tickets = jira_mod.get_open_tickets(client, epic_key)
            if not tickets:
                return f"No open tickets in {epic_key}."
            lines = [f"{t['key']}: [{t['fields']['status']['name']}] {t['fields']['summary']}" for t in tickets]
            return "\n".join(lines)

        if name == "jira_create_ticket":
            if not config:
                return "No athena.yaml found."
            jira_cfg    = config.get("jira", {})
            project_key = jira_cfg.get("project_key")
            epic_key    = jira_cfg.get("epic_key")
            client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
            key = jira_mod.create_story(
                client, project_key, epic_key,
                args["summary"], args.get("description", ""),
            )
            return f"Created: {key} — {args['summary']}"

        if name == "jira_transition_ticket":
            if not config:
                return "No athena.yaml found."
            jira_cfg = config.get("jira", {})
            client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
            ok = jira_mod.transition_ticket(client, args["ticket_key"], args["status"])
            return f"{args['ticket_key']} → {args['status']}" if ok else f"Transition failed — status '{args['status']}' not available."

        if name == "jira_comment":
            if not config:
                return "No athena.yaml found."
            jira_cfg = config.get("jira", {})
            client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
            jira_mod.post_comment(client, args["key"], args["body"])
            return f"Comment posted on {args['key']}."

        if name == "read_file":
            p = Path(args["path"])
            if not p.exists():
                return f"File not found: {args['path']}"
            return p.read_text(encoding="utf-8")

        if name == "shell":
            result = subprocess.run(
                args["command"], shell=True, capture_output=True, text=True,
            )
            out = (result.stdout + result.stderr).strip()
            return out or "(no output)"

        return f"Unknown tool: {name}"

    except Exception as e:
        return f"Error in {name}: {e}"


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def _system_prompt(config: dict | None) -> str:
    if config:
        jira_cfg = config.get("jira", {})
        ctx = (
            f"Current project context:\n"
            f"- Name: {config['name']}\n"
            f"- Stack: {config.get('stack', '—')}\n"
            f"- Cloud: {config.get('cloud', '—')}\n"
            f"- Version: {config.get('version', '—')}\n"
            f"- Secrets: {config.get('secrets_backend', '—')}\n"
            f"- Jira Epic: {jira_cfg.get('epic_key', '—')}\n"
            f"- Today: {date.today().isoformat()}"
        )
    else:
        ctx = "No athena.yaml found in current directory — project context unavailable."

    return (
        "You are the athena agent — an autonomous project lifecycle assistant. "
        "You help developers accomplish multi-step goals using the athena CLI toolkit.\n\n"
        "Rules:\n"
        "- Use the provided tools to accomplish the goal. Do not ask clarifying questions unless truly blocked.\n"
        "- Prefer athena_* tools over raw shell commands.\n"
        "- After each tool call, briefly state what you did and what you plan next.\n"
        "- When the goal is complete, summarise what was accomplished.\n"
        "- If a tool fails, diagnose and try an alternative before giving up.\n\n"
        f"{ctx}"
    )


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def _run_agent(goal: str, config: dict | None, max_turns: int, model: str) -> None:
    try:
        import anthropic as anthropic_sdk
    except ImportError:
        console.print("[red]anthropic SDK not installed.[/] Run: [bold]pip install anthropic[/]")
        raise typer.Exit(1)

    client_ai = anthropic_sdk.Anthropic()
    messages = [{"role": "user", "content": goal}]

    console.print(Rule("[bold #a78bfa]athena agent[/]"))
    console.print(f"[dim]Goal:[/] {goal}\n")

    for turn in range(1, max_turns + 1):
        response = client_ai.messages.create(
            model=model,
            max_tokens=8096,
            system=[{
                "type": "text",
                "text": _system_prompt(config),
                "cache_control": {"type": "ephemeral"},
            }],
            tools=_TOOLS,
            messages=messages,
        )

        # Print any text the agent produces
        for block in response.content:
            if hasattr(block, "text") and block.text.strip():
                console.print(block.text)

        if response.stop_reason == "end_turn":
            console.print(Rule("[green]Agent complete[/]"))
            break

        if response.stop_reason != "tool_use":
            console.print(f"[yellow]Unexpected stop reason: {response.stop_reason}[/]")
            break

        # Execute tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            console.print(f"\n[dim]▶ {block.name}[/] [dim]{json.dumps(block.input, ensure_ascii=False)}[/]")
            result = _execute_tool(block.name, block.input, config)
            if result:
                console.print(Panel(result, border_style="dim", padding=(0, 1)))
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user",      "content": tool_results})

        if turn == max_turns:
            console.print(f"[yellow]Reached max turns ({max_turns}). Stopping.[/]")


# ---------------------------------------------------------------------------
# Typer entry point
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def agent(
    goal:      str = typer.Argument(...,                      help="What you want to accomplish"),
    max_turns: int = typer.Option(15,  "--max-turns", "-n",   help="Maximum agent turns before stopping"),
    model:     str = typer.Option(
        "claude-opus-4-5", "--model", "-m",
        help="Claude model (claude-opus-4-5 | claude-sonnet-4-5)",
    ),
):
    """Autonomous agent — describe a goal, the agent runs the full lifecycle."""
    config: dict | None = None
    try:
        config = load_config()
    except FileNotFoundError:
        pass
    _run_agent(goal, config, max_turns, model)
