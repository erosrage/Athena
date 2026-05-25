from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

from proj.config import load_config, STACKS, cli_argv
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def mcp():
    """Start the athena MCP server for Claude Code integration (runs over stdio)."""
    try:
        import mcp.server.stdio
        from mcp.server import Server
        from mcp.types import Tool, TextContent
    except ImportError:
        console.print("[red]MCP SDK not installed.[/]")
        console.print("Run: [bold]pip install mcp[/]")
        raise typer.Exit(1)

    server = Server("athena-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            # ── Project context ────────────────────────────────────────────
            Tool(
                name="get_project_context",
                description=(
                    "Returns the current project's name, stack, cloud, version, "
                    "secrets backend, and linked Jira Epic from athena.yaml."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="list_stacks",
                description="Returns the full list of supported athena stacks grouped by category.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            # ── Plan & CHANGELOG ───────────────────────────────────────────
            Tool(
                name="get_plan",
                description="Reads plans/PLAN.md from the current project directory and returns its content.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="get_changelog",
                description="Reads CHANGELOG.md from the current project directory and returns its content.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="run_status",
                description="Runs `athena status` and returns the full output including Jira ticket table.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            # ── Git ────────────────────────────────────────────────────────
            Tool(
                name="get_git_status",
                description="Returns current git branch, last tag, and uncommitted file count.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            # ── Jira ───────────────────────────────────────────────────────
            Tool(
                name="get_jira_epic",
                description="Fetches the Jira Epic details and all open tickets for this project.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="list_open_tickets",
                description=(
                    "Returns a simplified list of open Jira tickets in the project Epic "
                    "(key, summary, status, assignee)."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="get_active_ticket",
                description=(
                    "Returns the currently active Jira ticket key saved by `athena dev`, "
                    "or null if none is set."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="set_active_ticket",
                description=(
                    "Sets the active Jira ticket for the current project (used by build/release "
                    "to know which story to transition)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_key": {"type": "string", "description": "Jira ticket key, e.g. PROJ-42"},
                    },
                    "required": ["ticket_key"],
                },
            ),
            Tool(
                name="create_jira_ticket",
                description="Creates a new Jira story in this project's Epic.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary":     {"type": "string",  "description": "One-line ticket title"},
                        "description": {"type": "string",  "description": "Ticket body (optional)"},
                        "assignee":    {"type": "string",  "description": "Jira username to assign (optional)"},
                        "issue_type":  {"type": "string",  "description": "Story | Bug | Task (default: Story)"},
                    },
                    "required": ["summary"],
                },
            ),
            Tool(
                name="start_ticket",
                description=(
                    "Transitions a Jira ticket to 'In Progress' and saves it as the active ticket. "
                    "Equivalent to picking a ticket in `athena dev`."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_key": {"type": "string", "description": "Jira ticket key, e.g. PROJ-42"},
                    },
                    "required": ["ticket_key"],
                },
            ),
            Tool(
                name="complete_ticket",
                description=(
                    "Transitions a Jira ticket to 'Done' and clears the active ticket. "
                    "Optionally closes the Epic if all stories are done."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_key": {"type": "string", "description": "Jira ticket key (defaults to active ticket)"},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="add_jira_comment",
                description="Posts a comment on any Jira issue (ticket or Epic).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key":  {"type": "string", "description": "Jira issue key"},
                        "body": {"type": "string", "description": "Comment body (Jira wiki markup supported)"},
                    },
                    "required": ["key", "body"],
                },
            ),
            # ── Build / Release ────────────────────────────────────────────
            Tool(
                name="run_build",
                description="Runs `athena build` and returns the output.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "multi_arch": {"type": "boolean", "description": "Build for linux/amd64 + linux/arm64"},
                        "no_push":    {"type": "boolean", "description": "Skip pushing image to registry"},
                        "no_jira":    {"type": "boolean", "description": "Skip Jira status update"},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="run_release",
                description="Runs `athena release` — bumps version, tags, deploys, notifies Jira.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bump":      {"type": "string", "enum": ["patch", "minor", "major"], "description": "Version bump type (default: patch)"},
                        "dry_run":   {"type": "boolean", "description": "Preview changes without writing anything"},
                        "no_deploy": {"type": "boolean", "description": "Skip the deploy step"},
                        "no_jira":   {"type": "boolean", "description": "Skip Jira comment and ticket transition"},
                    },
                    "required": [],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        from mcp.types import TextContent as TC

        def ok(text: str) -> list[TC]:
            return [TC(type="text", text=text)]

        try:
            cfg = load_config()
        except FileNotFoundError:
            cfg = None

        # ── Project context ────────────────────────────────────────────────
        if name == "get_project_context":
            if not cfg:
                return ok("No athena.yaml found in current directory.")
            jira = cfg.get("jira", {})
            result = {
                "name":            cfg["name"],
                "stack":           cfg.get("stack", "—"),
                "cloud":           cfg.get("cloud", "—"),
                "version":         cfg.get("version", "0.1.0"),
                "secrets_backend": cfg.get("secrets_backend", "dotenv"),
                "jira_epic":       jira.get("epic_key"),
                "jira_base_url":   jira.get("base_url"),
                "stakeholders":    jira.get("stakeholders", []),
            }
            return ok(json.dumps(result, indent=2))

        if name == "list_stacks":
            from proj.config import STACK_CATEGORIES
            return ok(json.dumps(STACK_CATEGORIES, indent=2))

        # ── Plan & CHANGELOG ───────────────────────────────────────────────
        if name == "get_plan":
            p = Path("plans/PLAN.md")
            if not p.exists():
                return ok("No plans/PLAN.md found in current directory.")
            return ok(p.read_text(encoding="utf-8"))

        if name == "get_changelog":
            p = Path("CHANGELOG.md")
            if not p.exists():
                return ok("No CHANGELOG.md found in current directory.")
            return ok(p.read_text(encoding="utf-8"))

        if name == "run_status":
            return ok(_run_capture(cli_argv("status")))

        # ── Git ────────────────────────────────────────────────────────────
        if name == "get_git_status":
            branch = _shell(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            tag    = _shell(["git", "describe", "--tags", "--abbrev=0"])
            dirty  = _shell(["git", "status", "--porcelain"])
            result = {
                "branch":            branch or "unknown",
                "last_tag":          tag or "no tags",
                "uncommitted_files": len([l for l in dirty.splitlines() if l.strip()]),
            }
            return ok(json.dumps(result, indent=2))

        # ── Jira ───────────────────────────────────────────────────────────
        if name == "get_jira_epic":
            if not cfg:
                return ok("No athena.yaml found.")
            jira_cfg = cfg.get("jira", {})
            epic_key = jira_cfg.get("epic_key")
            if not epic_key:
                return ok("No Jira Epic linked in athena.yaml")
            try:
                client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
                epic   = client.issue(epic_key)
                issues = client.get_epic_issues(epic_key).get("issues", [])
                result = {
                    "epic_key": epic_key,
                    "summary":  epic["fields"]["summary"],
                    "status":   epic["fields"]["status"]["name"],
                    "tickets": [
                        {
                            "key":      i["key"],
                            "summary":  i["fields"]["summary"],
                            "status":   i["fields"]["status"]["name"],
                            "assignee": (i["fields"].get("assignee") or {}).get("displayName", "Unassigned"),
                        }
                        for i in issues
                    ],
                }
                return ok(json.dumps(result, indent=2))
            except Exception as e:
                return ok(f"Jira error: {e}")

        if name == "list_open_tickets":
            if not cfg:
                return ok("No athena.yaml found.")
            jira_cfg = cfg.get("jira", {})
            epic_key = jira_cfg.get("epic_key")
            base_url = jira_cfg.get("base_url")
            token    = jira_cfg.get("token")
            if not all([epic_key, base_url, token]):
                return ok("Jira not fully configured in athena.yaml.")
            try:
                client  = jira_mod.connect(base_url, token)
                tickets = jira_mod.get_open_tickets(client, epic_key)
                if not tickets:
                    return ok(f"No open tickets in {epic_key}.")
                rows = [
                    {
                        "key":      t["key"],
                        "summary":  t["fields"]["summary"],
                        "status":   t["fields"]["status"]["name"],
                        "assignee": (t["fields"].get("assignee") or {}).get("displayName", "Unassigned"),
                    }
                    for t in tickets
                ]
                return ok(json.dumps(rows, indent=2))
            except Exception as e:
                return ok(f"Jira error: {e}")

        if name == "get_active_ticket":
            key = jira_mod.load_active_ticket()
            return ok(json.dumps({"active_ticket": key}))

        if name == "set_active_ticket":
            key = arguments["ticket_key"]
            jira_mod.save_active_ticket(key)
            return ok(f"Active ticket set to {key}.")

        if name == "create_jira_ticket":
            if not cfg:
                return ok("No athena.yaml found.")
            jira_cfg   = cfg.get("jira", {})
            epic_key   = jira_cfg.get("epic_key")
            issue_type = arguments.get("issue_type", "Story")
            try:
                client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
                fields = {
                    "project":     {"key": jira_cfg["project_key"]},
                    "summary":     arguments["summary"],
                    "description": arguments.get("description", ""),
                    "issuetype":   {"name": issue_type},
                }
                if epic_key:
                    fields["customfield_10014"] = epic_key
                if arguments.get("assignee"):
                    fields["assignee"] = {"name": arguments["assignee"]}
                issue = client.create_issue(fields=fields)
                url   = f"{jira_cfg['base_url']}/browse/{issue['key']}"
                return ok(f"Created: {issue['key']}\n{url}")
            except Exception as e:
                return ok(f"Failed to create ticket: {e}")

        if name == "start_ticket":
            if not cfg:
                return ok("No athena.yaml found.")
            jira_cfg = cfg.get("jira", {})
            key      = arguments["ticket_key"]
            try:
                client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
                jira_mod.save_active_ticket(key)
                ok_t = jira_mod.transition_ticket(client, key, "In Progress")
                if ok_t:
                    return ok(f"{key} → In Progress (saved as active ticket).")
                return ok(f"Could not transition {key} to In Progress — check available statuses.")
            except Exception as e:
                return ok(f"Jira error: {e}")

        if name == "complete_ticket":
            if not cfg:
                return ok("No athena.yaml found.")
            jira_cfg = cfg.get("jira", {})
            epic_key = jira_cfg.get("epic_key")
            key      = arguments.get("ticket_key") or jira_mod.load_active_ticket()
            if not key:
                return ok("No ticket_key provided and no active ticket set.")
            try:
                client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
                ok_t = jira_mod.transition_ticket(client, key, "Done")
                jira_mod.clear_active_ticket()
                lines = [f"{key} → Done"]
                if epic_key:
                    remaining = jira_mod.get_open_tickets(client, epic_key)
                    if not remaining:
                        jira_mod.transition_ticket(client, epic_key, "Done")
                        lines.append(f"{epic_key} → Done (all stories complete)")
                    else:
                        lines.append(f"{len(remaining)} stories still open — Epic stays active")
                return ok("\n".join(lines))
            except Exception as e:
                return ok(f"Jira error: {e}")

        if name == "add_jira_comment":
            if not cfg:
                return ok("No athena.yaml found.")
            jira_cfg = cfg.get("jira", {})
            try:
                client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
                jira_mod.post_comment(client, arguments["key"], arguments["body"])
                return ok(f"Comment posted on {arguments['key']}.")
            except Exception as e:
                return ok(f"Jira error: {e}")

        # ── Build / Release ────────────────────────────────────────────────
        if name == "run_build":
            cmd = cli_argv("build")
            if arguments.get("multi_arch"): cmd.append("--multi-arch")
            if arguments.get("no_push"):    cmd.append("--no-push")
            if arguments.get("no_jira"):    cmd.append("--no-jira")
            return ok(_run_capture(cmd))

        if name == "run_release":
            cmd = cli_argv("release", "--bump", arguments.get("bump", "patch"))
            if arguments.get("dry_run"):   cmd.append("--dry-run")
            if arguments.get("no_deploy"): cmd.append("--no-deploy")
            if arguments.get("no_jira"):   cmd.append("--no-jira")
            return ok(_run_capture(cmd))

        return ok(f"Unknown tool: {name}")

    console.print("[bold #a78bfa]athena mcp[/] — starting on stdio")
    console.print("Add to Claude Code settings:")
    console.print('  [dim]{"mcpServers": {"athena": {"command": "athena", "args": ["mcp"]}}}[/]\n')

    import asyncio
    asyncio.run(mcp.server.stdio.stdio_server(server))


def _run_capture(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return (result.stdout + result.stderr).strip()


def _shell(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""
