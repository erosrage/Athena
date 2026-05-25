from __future__ import annotations
from pathlib import Path

import yaml
from atlassian import Jira
from rich.console import Console
from rich.table import Table

console = Console()

_ACTIVE_TICKET_FILE = ".athena_active_ticket"
_LEGACY_ACTIVE_TICKET_FILE = ".proj_active_ticket"


def _active_ticket_path() -> Path:
    primary = Path(_ACTIVE_TICKET_FILE)
    legacy = Path(_LEGACY_ACTIVE_TICKET_FILE)
    if primary.exists():
        return primary
    if legacy.exists():
        return legacy
    return primary


def connect(base_url: str, token: str) -> Jira:
    return Jira(url=base_url, token=token)


def validate_epic(jira: Jira, epic_key: str) -> dict | None:
    try:
        issue = jira.issue(epic_key)
        if issue.get("fields", {}).get("issuetype", {}).get("name") != "Epic":
            return None
        return issue
    except Exception:
        return None


def create_epic(jira: Jira, project_key: str, name: str, description: str) -> str:
    issue = jira.create_issue(fields={
        "project":     {"key": project_key},
        "summary":     name,
        "description": description,
        "issuetype":   {"name": "Epic"},
    })
    return issue["key"]


def create_story(jira: Jira, project_key: str, epic_key: str, summary: str, description: str = "") -> str:
    issue = jira.create_issue(fields={
        "project":          {"key": project_key},
        "summary":          summary,
        "description":      description,
        "issuetype":        {"name": "Story"},
        "customfield_10014": epic_key,  # Epic Link
    })
    return issue["key"]


def prompt_and_create_stories(jira: Jira, project_key: str, epic_key: str) -> list[str]:
    """Interactively prompt the user to create initial stories under the Epic."""
    from rich.prompt import Prompt, Confirm
    created = []
    console.print(f"\n  Break [bold]{epic_key}[/] into stories? Enter one per line, blank to finish.")
    while True:
        summary = Prompt.ask("  Story summary", default="").strip()
        if not summary:
            break
        try:
            key = create_story(jira, project_key, epic_key, summary)
            console.print(f"  [green]Created:[/] [cyan]{key}[/] — {summary}")
            created.append(key)
        except Exception as e:
            console.print(f"  [red]Failed to create story: {e}[/]")
    return created


def get_all_stories(jira: Jira, epic_key: str) -> list[dict]:
    """Return ALL stories under an Epic regardless of status."""
    issues = jira.get_epic_issues(epic_key).get("issues", [])
    return [i for i in issues if i["fields"]["issuetype"]["name"] == "Story"]


def get_open_tickets(jira: Jira, epic_key: str) -> list[dict]:
    """Return open (non-Done) tickets in an Epic."""
    issues = jira.get_epic_issues(epic_key).get("issues", [])
    return [
        i for i in issues
        if i["fields"]["status"]["name"].lower() not in ("done", "closed", "resolved")
    ]


def print_ticket_table(tickets: list[dict]) -> None:
    if not tickets:
        console.print("  [dim]No open tickets in Epic.[/]")
        return
    table = Table(show_header=True, header_style="bold #a78bfa", box=None, padding=(0, 2))
    table.add_column("#", style="dim", width=3)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Summary", max_width=52)
    table.add_column("Status", style="green")
    for i, issue in enumerate(tickets, 1):
        table.add_row(
            str(i),
            issue["key"],
            issue["fields"]["summary"],
            issue["fields"]["status"]["name"],
        )
    console.print(table)


def pick_active_ticket(tickets: list[dict]) -> dict | None:
    """Let the user pick one ticket to work on. Returns the chosen ticket or None."""
    from rich.prompt import Prompt
    if not tickets:
        return None
    print_ticket_table(tickets)
    choice = Prompt.ask(
        "\n  Pick a ticket to work on [dim](number, or Enter to skip)[/]",
        default="",
    ).strip()
    if not choice:
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(tickets):
            return tickets[idx]
    except ValueError:
        pass
    console.print("  [yellow]Invalid choice — no ticket selected.[/]")
    return None


def save_active_ticket(key: str) -> None:
    Path(_ACTIVE_TICKET_FILE).write_text(key)


def load_active_ticket() -> str | None:
    p = _active_ticket_path()
    return p.read_text().strip() if p.exists() else None


def clear_active_ticket() -> None:
    for name in (_ACTIVE_TICKET_FILE, _LEGACY_ACTIVE_TICKET_FILE):
        p = Path(name)
        if p.exists():
            p.unlink()


def transition_ticket(jira: Jira, issue_key: str, status_name: str) -> bool:
    """Transition a single ticket to the given status. Returns True on success."""
    try:
        transitions = jira.get_issue_transitions(issue_key)
        match = next((t for t in transitions if t["name"].lower() == status_name.lower()), None)
        if not match:
            console.print(f"  [yellow]No transition '{status_name}' found for {issue_key}[/]")
            return False
        jira.issue_transition(issue_key, match["id"])
        return True
    except Exception as e:
        console.print(f"  [yellow]Could not transition {issue_key}: {e}[/]")
        return False


def transition_issues(jira: Jira, epic_key: str, status_name: str) -> None:
    """Move all issues in an Epic to the given status name."""
    issues = jira.get_epic_issues(epic_key).get("issues", [])
    for issue in issues:
        transition_ticket(jira, issue["key"], status_name)


def add_watchers(jira: Jira, issue_key: str, usernames: list[str]) -> None:
    for username in usernames:
        try:
            jira.add_watcher(issue_key, username)
        except Exception:
            console.print(f"  [yellow]Warning:[/] could not add watcher [bold]{username}[/]")


def post_comment(jira: Jira, issue_key: str, body: str) -> None:
    jira.issue_add_comment(issue_key, body)


def post_status_log(jira: Jira, body: str, *keys: str | None) -> None:
    """Post the same status comment to every non-None key (Epic + ticket).
    Failures on individual keys are logged but do not abort the others."""
    for key in keys:
        if not key:
            continue
        try:
            jira.issue_add_comment(key, body)
        except Exception as e:
            console.print(f"  [yellow]Jira comment skipped on {key}: {e}[/]")
