from __future__ import annotations
import subprocess
from rich.console import Console

console = Console()


def stream_response(messages: list[dict], system: str) -> str:
    """Build conversation history into a single prompt, shell to `claude -p`, stream output."""
    prompt = _build_prompt(messages, system)
    return _run_claude_streaming(prompt)


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


def _run_claude_streaming(prompt: str) -> str:
    """Pipe prompt to `claude -p` via stdin, stream stdout to terminal, return full text."""
    try:
        proc = subprocess.Popen(
            ["claude", "-p"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        console.print("[red]`claude` not found.[/] Install Claude Code: https://claude.ai/code")
        raise SystemExit(1)

    proc.stdin.write(prompt)
    proc.stdin.close()

    chunks: list[str] = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        chunks.append(line)

    proc.wait()

    if proc.returncode != 0:
        err = proc.stderr.read().strip()
        console.print(f"\n[red]claude exited {proc.returncode}[/]{': ' + err if err else ''}")
        raise SystemExit(1)

    return "".join(chunks)


def _build_prompt(messages: list[dict], system: str) -> str:
    parts = [system, ""]
    for msg in messages:
        label = "User" if msg["role"] == "user" else "Assistant"
        parts.append(f"{label}: {msg['content']}")
    return "\n\n".join(parts)


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
