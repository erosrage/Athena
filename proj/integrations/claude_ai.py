from __future__ import annotations
import os

from rich.console import Console
from rich.markdown import Markdown

console = Console()


def _client():
    try:
        import anthropic
    except ImportError:
        console.print("[red]anthropic package not installed.[/] Run: pip install anthropic")
        raise SystemExit(1)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY not set.[/] Add it to your .env or environment.")
        raise SystemExit(1)
    return anthropic.Anthropic(api_key=api_key)


def stream_response(messages: list[dict], system: str) -> str:
    """Stream a Claude response to the terminal, return the full text."""
    import anthropic
    client = _client()
    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text
    print()
    return full_text


def extract_stories(plan_text: str, project_context: dict) -> list[str]:
    """Ask Claude to pull actionable stories out of a plan. Returns a list of summaries."""
    system = (
        "You are a Jira project manager. Given a project plan, extract a flat list of "
        "actionable user stories. Output ONLY a numbered list of story summaries, one per line, "
        "no extra commentary. Each summary should be concise (under 80 chars) and start with a verb."
    )
    messages = [{"role": "user", "content": f"Extract stories from this plan:\n\n{plan_text}"}]
    client = _client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    raw = response.content[0].text.strip()
    stories = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading "1. ", "- ", etc.
        for prefix in ("- ", "* "):
            if line.startswith(prefix):
                line = line[len(prefix):]
        if line and line[0].isdigit() and ". " in line:
            line = line.split(". ", 1)[1]
        if line:
            stories.append(line)
    return stories
