from __future__ import annotations
from atlassian import Jira
from rich.console import Console

console = Console()


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


def add_watchers(jira: Jira, issue_key: str, usernames: list[str]) -> None:
    for username in usernames:
        try:
            jira.add_watcher(issue_key, username)
        except Exception:
            console.print(f"  [yellow]Warning:[/] could not add watcher [bold]{username}[/]")


def post_comment(jira: Jira, issue_key: str, body: str) -> None:
    jira.issue_add_comment(issue_key, body)


def transition_issues(jira: Jira, epic_key: str, status_name: str) -> None:
    """Move all issues in an Epic to the given status name."""
    issues = jira.get_epic_issues(epic_key).get("issues", [])
    for issue in issues:
        transitions = jira.get_issue_transitions(issue["key"])
        match = next((t for t in transitions if t["name"].lower() == status_name.lower()), None)
        if match:
            jira.issue_transition(issue["key"], match["id"])
