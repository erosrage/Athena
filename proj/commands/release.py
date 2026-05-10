from __future__ import annotations
import re
import subprocess
from datetime import date
from pathlib import Path

import requests
import typer
import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm

from proj.config import load_config, save_config
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()

BUMP_TYPES = ["patch", "minor", "major"]


@app.callback(invoke_without_command=True)
def release(
    bump: str = typer.Option("patch", "--bump", "-b", help="Version bump: patch | minor | major"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
):
    """Bump version, update CHANGELOG, tag, deploy, and notify via Jira."""

    config = _load_or_exit()
    name   = config["name"]
    cloud  = config.get("cloud", "local")

    console.print(f"\n[bold #a78bfa]proj release[/] — [bold]{name}[/]\n")

    # --- Version bump ---
    old_version = config.get("version", "0.1.0")
    new_version = _bump_version(old_version, bump)
    console.print(f"  Version: [dim]{old_version}[/] → [bold green]{new_version}[/]")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/]")
        return

    # --- CHANGELOG ---
    log = _git_log_since_last_tag()
    _update_changelog(name, new_version, log)
    console.print("  CHANGELOG updated")

    # --- Version in manifest files ---
    _bump_manifest_files(new_version, config["stack"])

    # --- proj.yaml version ---
    config["version"] = new_version
    save_config(config)

    # --- Git commit + tag ---
    _run(["git", "add", "."])
    _run(["git", "commit", "-m", f"chore: release {new_version}"])
    _run(["git", "tag", f"v{new_version}"])
    _run(["git", "push"])
    _run(["git", "push", "--tags"])
    console.print(f"  Tagged: [cyan]v{new_version}[/]")

    # --- Deploy ---
    _deploy(cloud, name, new_version, config)

    # --- Jira comment + transition ---
    jira_cfg = config.get("jira", {})
    epic_key  = jira_cfg.get("epic_key")
    if epic_key and jira_cfg.get("base_url") and jira_cfg.get("token"):
        _notify_jira(jira_cfg, epic_key, name, new_version, log)
    else:
        console.print("  [dim]Jira not configured — skipping comment.[/]")

    # --- Webhook ---
    webhook_url = config.get("webhook_url")
    if webhook_url:
        _post_webhook(webhook_url, name, new_version, cloud)

    console.print(f"\n[bold green]Released {name} v{new_version}[/]")


def _bump_version(version: str, bump: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _git_log_since_last_tag() -> str:
    result = subprocess.run(
        ["git", "log", "--oneline", "$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || git rev-list --max-parents=0 HEAD)..HEAD"],
        shell=True, capture_output=True, text=True,
    )
    return result.stdout.strip() or "Initial release"


def _update_changelog(name: str, version: str, log: str) -> None:
    changelog = Path("CHANGELOG.md")
    today = date.today().isoformat()
    entry = f"## [{version}] — {today}\n\n{log}\n\n"
    existing = changelog.read_text() if changelog.exists() else f"# Changelog — {name}\n\n"
    header, _, rest = existing.partition("\n\n")
    changelog.write_text(f"{header}\n\n{entry}{rest}")


def _bump_manifest_files(version: str, stack: str) -> None:
    bumpers = {
        "flask":       ("pyproject.toml", r'(version\s*=\s*")[^"]+(")', rf'\g<1>{version}\2'),
        "ts-node":     ("package.json",   r'("version"\s*:\s*")[^"]+(")', rf'\g<1>{version}\2'),
        "electron":    ("package.json",   r'("version"\s*:\s*")[^"]+(")', rf'\g<1>{version}\2'),
        "rust":        ("Cargo.toml",     r'(version\s*=\s*")[^"]+(")', rf'\g<1>{version}\2'),
        "databricks":  ("pyproject.toml", r'(version\s*=\s*")[^"]+(")', rf'\g<1>{version}\2'),
        "go":          (None, None, None),
    }
    manifest, pattern, replacement = bumpers.get(stack, (None, None, None))
    if manifest and Path(manifest).exists():
        text = Path(manifest).read_text()
        Path(manifest).write_text(re.sub(pattern, replacement, text, count=1))


def _deploy(cloud: str, name: str, version: str, config: dict) -> None:
    if config.get("stack") == "databricks":
        _deploy_databricks(name, version, config)
        return

    console.print(f"\nDeploying to [bold]{cloud}[/]...")
    if cloud == "local":
        console.print("  [dim]Local target — skipping deploy.[/]")
        return
    cmds = {
        "azure": ["az", "webapp", "deploy", "--name", name, "--src-path", "."],
        "aws":   ["aws", "ecs", "update-service", "--cluster", config.get("ecs_cluster", "default"),
                  "--service", name, "--force-new-deployment"],
        "gcp":   ["gcloud", "run", "deploy", name, "--image",
                  f"gcr.io/{config.get('gcp_project', 'my-project')}/{name}:{version}"],
    }
    cmd = cmds.get(cloud)
    if cmd:
        _run(cmd)
    if cloud == "azure":
        _run(["kubectl", "rollout", "status", f"deployment/{name}"])


def _deploy_databricks(name: str, version: str, config: dict) -> None:
    dbx = config.get("databricks", {})
    deployment_file = dbx.get("deployment_file", "conf/deployment.yml")

    console.print(f"\nDeploying Databricks job [bold]{name}[/] v{version}...")
    _run(["dbx", "deploy", "--deployment-file", deployment_file])

    # Smoke-run validation
    job_name = dbx.get("job_name", name)
    if dbx.get("launch_on_release", False):
        console.print(f"\nLaunching smoke run: [cyan]{job_name}[/]...")
        _run(["dbx", "launch", "--job", job_name, "--as-run-submit", "--trace"])
    else:
        console.print(f"  [dim]Skipping launch (set databricks.launch_on_release: true to enable)[/]")


def _notify_jira(jira_cfg: dict, epic_key: str, name: str, version: str, log: str) -> None:
    console.print(f"\nPosting Jira comment on [bold]{epic_key}[/]...")
    try:
        client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
        stakeholders = jira_cfg.get("stakeholders", [])
        mentions = " ".join(f"[~{u}]" for u in stakeholders)
        body = (
            f"*Released: {name} v{version}*\n\n"
            f"{mentions}\n\n"
            f"{{noformat}}\n{log}\n{{noformat}}"
        )
        jira_mod.post_comment(client, epic_key, body)
        jira_mod.transition_issues(client, epic_key, "Done")
        console.print("  Comment posted, tickets transitioned to Done.")
    except Exception as e:
        console.print(f"  [yellow]Jira notify failed: {e}[/]")


def _post_webhook(url: str, name: str, version: str, cloud: str) -> None:
    try:
        requests.post(url, json={"project": name, "version": version, "cloud": cloud}, timeout=5)
        console.print(f"  Webhook posted to [dim]{url}[/]")
    except Exception as e:
        console.print(f"  [yellow]Webhook failed: {e}[/]")


def _run(cmd: list[str]) -> None:
    console.print(f"  [dim]$ {' '.join(cmd)}[/]")
    subprocess.run(cmd, check=True)


def _load_or_exit() -> dict:
    try:
        return load_config()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
