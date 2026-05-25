from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proj.config import STACK_META

# Default dev-server ports for browser preview panes in cmux layouts.
STACK_DEV_PORTS: dict[str, int | None] = {
    "flask": 5000,
    "fastapi": 8000,
    "django": 8000,
    "streamlit": 8501,
    "gradio": 7860,
    "litestar": 8000,
    "fasthtml": 8000,
    "express": 3000,
    "nestjs": 3000,
    "ts-node": 3000,
    "fastify": 3000,
    "bun": 3000,
    "hono": 3000,
    "react": 5173,
    "nextjs": 3000,
    "vue": 5173,
    "svelte": 5173,
    "angular": 4200,
    "astro": 4321,
    "remix": 3000,
    "solidjs": 5173,
    "electron": None,
    "tauri": None,
    "react-native": None,
    "flutter": None,
    "wails": None,
    "expo": None,
    "databricks": None,
    "jupyter": 8888,
    "mlflow": 5000,
    "dbt": None,
    "bi-report": None,
    "airflow": 8080,
    "terraform": None,
    "pulumi": None,
    "swiftui": None,
    "ios": None,
    "python-cli": None,
}


def dev_port_for_stack(stack: str) -> int | None:
    if stack in STACK_DEV_PORTS:
        return STACK_DEV_PORTS[stack]
    meta = STACK_META.get(stack, {})
    build_type = meta.get("build", "container")
    if build_type in ("container", "native") and stack not in ("go", "rust", "dotnet"):
        return 3000
    return None


def generate_cmux_config(config: dict) -> dict[str, Any]:
    name = config["name"]
    stack = config.get("stack", "")
    jira = config.get("jira", {})
    epic_key = jira.get("epic_key", "")
    version = config.get("version", "0.1.0")
    dev_port = dev_port_for_stack(stack)

    ws_suffix = f" — {epic_key}" if epic_key else ""
    ws_name = f"{name}{ws_suffix}"

    actions: dict[str, Any] = {
        "athena-plan": {
            "type": "command",
            "title": "Plan",
            "subtitle": "athena plan — solutioning session",
            "command": "athena plan --resume",
            "target": "currentTerminal",
            "keywords": ["plan", "design", "architecture"],
        },
        "athena-dev": {
            "type": "command",
            "title": "Dev",
            "subtitle": "athena dev — pick ticket, load secrets, start server",
            "command": "athena dev",
            "target": "currentTerminal",
            "keywords": ["dev", "develop", "server"],
        },
        "athena-build": {
            "type": "command",
            "title": "Build",
            "subtitle": "athena build — package and push",
            "command": "athena build",
            "target": "currentTerminal",
            "keywords": ["build", "docker", "package"],
        },
        "athena-release": {
            "type": "command",
            "title": "Release",
            "subtitle": "athena release — bump, deploy, notify Jira",
            "command": "athena release",
            "target": "currentTerminal",
            "keywords": ["release", "deploy", "version"],
        },
        "athena-status": {
            "type": "command",
            "title": "Status",
            "subtitle": "athena status — version, git, Jira epic",
            "command": "athena status",
            "target": "currentTerminal",
            "keywords": ["status", "jira", "health"],
        },
        "athena-claude": {
            "type": "agent",
            "title": "Claude (athena)",
            "subtitle": "Claude Code with athena MCP context",
            "agent": "claude",
            "args": [],
            "target": "newTabInCurrentPane",
            "keywords": ["claude", "agent", "ai"],
        },
        "athena-dev-loop": {
            "type": "workspaceCommand",
            "title": "Dev Loop",
            "subtitle": "Claude + dev server + preview",
            "commandName": "Dev Loop",
            "keywords": ["dev", "loop", "fullstack"],
        },
        "athena-plan-workspace": {
            "type": "workspaceCommand",
            "title": "Plan Workspace",
            "subtitle": "Planning session + plan reader",
            "commandName": "Plan Workspace",
            "keywords": ["plan", "design"],
        },
        "athena-story": {
            "type": "workspaceCommand",
            "title": "Story Workspace",
            "subtitle": "Work on a Jira story (set PROJ_TICKET env)",
            "commandName": "Story Workspace",
            "keywords": ["story", "ticket", "jira"],
        },
    }

    commands: list[dict[str, Any]] = [
        _plan_workspace_command(ws_name),
        _story_workspace_command(ws_name, dev_port),
        _dev_loop_workspace_command(ws_name, dev_port),
        {
            "name": "Build / Release",
            "description": "Claude for /build and /release plus status shell",
            "keywords": ["build", "release", "ship"],
            "workspace": {
                "name": f"Build — {name}",
                "cwd": ".",
                "layout": {
                    "direction": "horizontal",
                    "split": 0.5,
                    "children": [
                        {
                            "pane": {
                                "surfaces": [
                                    {
                                        "type": "terminal",
                                        "name": "Claude",
                                        "command": "claude",
                                        "focus": True,
                                    }
                                ]
                            }
                        },
                        {
                            "pane": {
                                "surfaces": [
                                    {
                                        "type": "terminal",
                                        "name": "Status",
                                        "command": "athena status; exec ${SHELL:-/bin/zsh} -l",
                                    }
                                ]
                            }
                        },
                    ],
                },
            },
        },
    ]

    return {
        "actions": actions,
        "ui": {
            "surfaceTabBar": {
                "buttons": [
                    "athena-claude",
                    "athena-dev",
                    "athena-build",
                    "athena-plan",
                    "athena-status",
                ]
            }
        },
        "commands": commands,
        "_proj_meta": {
            "name": name,
            "stack": stack,
            "version": version,
            "epic_key": epic_key or None,
            "dev_port": dev_port,
        },
    }


def write_cmux_scaffold(project_dir: Path, config: dict) -> None:
    cmux_dir = project_dir / ".cmux"
    cmux_dir.mkdir(exist_ok=True)

    cmux_config = generate_cmux_config(config)
    # Strip internal metadata before writing — cmux may reject unknown keys.
    cmux_config.pop("_proj_meta", None)
    (cmux_dir / "cmux.json").write_text(json.dumps(cmux_config, indent=2) + "\n")

    setup_script = """#!/usr/bin/env bash
# cmux worktree setup — runs after worktree creation (craigsc/cmux compatible)
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [ ! -f athena.yaml ]; then
  echo "[athena] No athena.yaml — skipping setup"
  exit 0
fi
if [ -n "${PROJ_TICKET:-}" ]; then
  echo "[athena] Starting dev for ticket ${PROJ_TICKET}"
  athena dev --ticket "$PROJ_TICKET"
else
  echo "[athena] Run 'athena dev' or set PROJ_TICKET for story workspaces"
fi
"""
    setup_path = cmux_dir / "setup"
    setup_path.write_text(setup_script)
    setup_path.chmod(0o755)


def _plan_workspace_command(ws_name: str) -> dict[str, Any]:
    return {
        "name": "Plan Workspace",
        "description": "Interactive planning session with plan reader pane",
        "keywords": ["plan", "design", "architecture"],
        "workspace": {
            "name": f"Plan — {ws_name}",
            "cwd": ".",
            "layout": {
                "direction": "horizontal",
                "split": 0.55,
                "children": [
                    {
                        "pane": {
                            "surfaces": [
                                {
                                    "type": "terminal",
                                    "name": "Plan",
                                    "command": "athena plan --resume",
                                    "focus": True,
                                }
                            ]
                        }
                    },
                    {
                        "pane": {
                            "surfaces": [
                                {
                                    "type": "terminal",
                                    "name": "PLAN.md",
                                    "command": "while [ ! -f plans/PLAN.md ]; do echo 'Waiting for plans/PLAN.md...'; sleep 2; done; less +G plans/PLAN.md",
                                }
                            ]
                        }
                    },
                ],
            },
        },
    }


def _story_workspace_command(ws_name: str, dev_port: int | None) -> dict[str, Any]:
    dev_cmd = (
        'if [ -n "${PROJ_TICKET:-}" ]; then athena dev --ticket "$PROJ_TICKET"; '
        "else echo 'Set PROJ_TICKET (e.g. export PROJ_TICKET=PROJ-42) then re-run'; exec ${SHELL:-/bin/zsh} -l; fi"
    )
    right_children: list[dict[str, Any]] = [
        {
            "pane": {
                "surfaces": [
                    {
                        "type": "terminal",
                        "name": "Dev",
                        "command": dev_cmd,
                        "focus": True,
                    }
                ]
            }
        }
    ]
    if dev_port:
        right_children.append(
            {
                "pane": {
                    "surfaces": [
                        {
                            "type": "browser",
                            "name": "Preview",
                            "url": f"http://localhost:{dev_port}",
                        }
                    ]
                }
            }
        )
        right_layout: dict[str, Any] = {
            "direction": "vertical",
            "split": 0.6,
            "children": right_children,
        }
    else:
        right_layout = right_children[0]

    return {
        "name": "Story Workspace",
        "description": "Jira story dev loop — export PROJ_TICKET before opening",
        "keywords": ["story", "ticket", "jira"],
        "workspace": {
            "name": f"Story — {ws_name}",
            "cwd": ".",
            "layout": {
                "direction": "horizontal",
                "split": 0.4,
                "children": [
                    {
                        "pane": {
                            "surfaces": [
                                {
                                    "type": "terminal",
                                    "name": "Claude",
                                    "command": "claude",
                                }
                            ]
                        }
                    },
                    right_layout,
                ],
            },
        },
    }


def _dev_loop_workspace_command(ws_name: str, dev_port: int | None) -> dict[str, Any]:
    dev_cmd = "athena dev"

    if not dev_port:
        return {
            "name": "Dev Loop",
            "description": "Claude + athena dev (no browser preview for this stack)",
            "keywords": ["dev", "loop"],
            "workspace": {
                "name": f"Dev — {ws_name}",
                "cwd": ".",
                "layout": {
                    "direction": "horizontal",
                    "split": 0.4,
                    "children": [
                        {
                            "pane": {
                                "surfaces": [
                                    {
                                        "type": "terminal",
                                        "name": "Claude",
                                        "command": "claude",
                                        "focus": True,
                                    }
                                ]
                            }
                        },
                        {
                            "pane": {
                                "surfaces": [
                                    {
                                        "type": "terminal",
                                        "name": "Dev",
                                        "command": dev_cmd,
                                    }
                                ]
                            }
                        },
                    ],
                },
            },
        }

    return {
        "name": "Dev Loop",
        "description": "Claude + dev server + browser preview",
        "keywords": ["dev", "loop", "fullstack"],
        "workspace": {
            "name": f"Dev — {ws_name}",
            "cwd": ".",
            "layout": {
                "direction": "horizontal",
                "split": 0.4,
                "children": [
                    {
                        "pane": {
                            "surfaces": [
                                {
                                    "type": "terminal",
                                    "name": "Claude",
                                    "command": "claude",
                                    "focus": True,
                                }
                            ]
                        }
                    },
                    {
                        "direction": "vertical",
                        "split": 0.55,
                        "children": [
                            {
                                "pane": {
                                    "surfaces": [
                                        {
                                            "type": "terminal",
                                            "name": "Dev",
                                            "command": dev_cmd,
                                        }
                                    ]
                                }
                            },
                            {
                                "pane": {
                                    "surfaces": [
                                        {
                                            "type": "browser",
                                            "name": "Preview",
                                            "url": f"http://localhost:{dev_port}",
                                        }
                                    ]
                                }
                            },
                        ],
                    },
                ],
            },
        },
    }
