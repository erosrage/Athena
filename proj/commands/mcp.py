from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

from proj.config import load_config
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def mcp():
    """Start the proj MCP server for Claude Code integration (runs over stdio)."""
    try:
        import mcp.server.stdio
        from mcp.server import Server
        from mcp.types import Tool, TextContent
    except ImportError:
        console.print("[red]MCP SDK not installed.[/]")
        console.print("Run: [bold]pip install mcp[/]")
        raise typer.Exit(1)

    config = _load_or_exit()
    server = Server("proj-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="get_project_context",
                description="Returns the current project's stack, cloud, version, and Jira Epic from proj.yaml.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="get_jira_epic",
                description="Fetches the Jira Epic details and all open tickets for this project.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="create_jira_ticket",
                description="Creates a new Jira ticket inside this project's Epic.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary":     {"type": "string", "description": "One-line ticket title"},
                        "description": {"type": "string", "description": "Ticket body (optional)"},
                        "assignee":    {"type": "string", "description": "Jira username to assign (optional)"},
                        "issue_type":  {"type": "string", "description": "Story, Bug, Task (default: Task)"},
                    },
                    "required": ["summary"],
                },
            ),
            Tool(
                name="run_build",
                description="Runs proj build and returns the output.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "multi_arch": {"type": "boolean", "description": "Build for amd64 + arm64"},
                        "push":       {"type": "boolean", "description": "Push to registry (default true)"},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="run_release",
                description="Runs proj release — bumps version, deploys, notifies Jira.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bump": {
                            "type": "string",
                            "enum": ["patch", "minor", "major"],
                            "description": "Version bump type (default: patch)",
                        },
                        "dry_run": {"type": "boolean", "description": "Preview without making changes"},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_git_status",
                description="Returns current git branch, last tag, and uncommitted file count.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        cfg = load_config()

        if name == "get_project_context":
            jira = cfg.get("jira", {})
            result = {
                "name":            cfg["name"],
                "stack":           cfg["stack"],
                "cloud":           cfg["cloud"],
                "version":         cfg.get("version", "0.1.0"),
                "secrets_backend": cfg.get("secrets_backend", "dotenv"),
                "jira_epic":       jira.get("epic_key"),
                "jira_base_url":   jira.get("base_url"),
                "stakeholders":    jira.get("stakeholders", []),
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "get_jira_epic":
            jira_cfg = cfg.get("jira", {})
            epic_key = jira_cfg.get("epic_key")
            if not epic_key:
                return [TextContent(type="text", text="No Jira Epic linked in proj.yaml")]
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
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=f"Jira error: {e}")]

        if name == "create_jira_ticket":
            jira_cfg   = cfg.get("jira", {})
            epic_key   = jira_cfg.get("epic_key")
            issue_type = arguments.get("issue_type", "Task")
            try:
                client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
                fields = {
                    "project":     {"key": jira_cfg["project_key"]},
                    "summary":     arguments["summary"],
                    "description": arguments.get("description", ""),
                    "issuetype":   {"name": issue_type},
                }
                if epic_key:
                    fields["customfield_10014"] = epic_key  # Epic Link field
                if arguments.get("assignee"):
                    fields["assignee"] = {"name": arguments["assignee"]}
                issue = client.create_issue(fields=fields)
                url   = f"{jira_cfg['base_url']}/browse/{issue['key']}"
                return [TextContent(type="text", text=f"Created: {issue['key']}\n{url}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Failed to create ticket: {e}")]

        if name == "run_build":
            cmd = ["proj", "build"]
            if arguments.get("multi_arch"):
                cmd.append("--multi-arch")
            if arguments.get("push") is False:
                cmd.append("--no-push")
            return [TextContent(type="text", text=_run_capture(cmd))]

        if name == "run_release":
            cmd = ["proj", "release", "--bump", arguments.get("bump", "patch")]
            if arguments.get("dry_run"):
                cmd.append("--dry-run")
            return [TextContent(type="text", text=_run_capture(cmd))]

        if name == "get_git_status":
            branch = _shell(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            tag    = _shell(["git", "describe", "--tags", "--abbrev=0"])
            dirty  = _shell(["git", "status", "--porcelain"])
            result = {
                "branch":            branch,
                "last_tag":          tag or "no tags",
                "uncommitted_files": len([l for l in dirty.splitlines() if l.strip()]),
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    console.print("[bold #a78bfa]proj mcp[/] — starting on stdio")
    console.print("Add to Claude Code settings:")
    console.print(f'  [dim]{{"mcpServers": {{"proj": {{"command": "proj", "args": ["mcp"]}}}}}}[/]\n')

    import asyncio
    asyncio.run(mcp.server.stdio.stdio_server(server))


def _run_capture(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return (result.stdout + result.stderr).strip()


def _shell(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _load_or_exit() -> dict:
    try:
        return load_config()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
