from __future__ import annotations
import subprocess
from rich.console import Console

console = Console()


def extract_stories(plan_text: str, project_context: dict) -> list[str]:
    """Ask Claude Code CLI to extract actionable stories from a plan."""
    prompt = (
        "You are a Jira project manager. Given this project plan, extract a flat list of "
        "actionable user stories. Output ONLY a numbered list, one story per line, no extra text. "
        "Each summary must be under 80 chars and start with a verb.\n\n"
        f"Plan:\n\n{plan_text}"
    )
    try:
        result = subprocess.run(
            ["claude", "-p"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        raw = result.stdout.strip()
    except FileNotFoundError:
        console.print("[red]`claude` not found.[/] Install Claude Code: https://claude.ai/code")
        return []
    except subprocess.TimeoutExpired:
        console.print("[yellow]Story extraction timed out.[/]")
        return []

    return _parse_story_list(raw)


def _parse_story_list(raw: str) -> list[str]:
    stories = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        for prefix in ("- ", "* "):
            if line.startswith(prefix):
                line = line[len(prefix):]
        if line and line[0].isdigit() and ". " in line:
            line = line.split(". ", 1)[1]
        if line:
            stories.append(line)
    return stories
