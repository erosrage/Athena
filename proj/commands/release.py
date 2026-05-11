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

from proj.config import load_config, save_config, STACK_META
from proj.integrations import jira as jira_mod

app = typer.Typer()
console = Console()

BUMP_TYPES = ["patch", "minor", "major"]


@app.callback(invoke_without_command=True)
def release(
    bump:      str  = typer.Option("patch", "--bump", "-b", help="Version bump: patch | minor | major"),
    dry_run:   bool = typer.Option(False, "--dry-run",    help="Preview without making changes"),
    no_deploy: bool = typer.Option(False, "--no-deploy",  help="Skip the deploy step"),
    no_jira:   bool = typer.Option(False, "--no-jira",    help="Skip Jira comment and ticket transition"),
):
    """Bump version, update CHANGELOG, tag, deploy, and notify via Jira."""

    if bump not in BUMP_TYPES:
        console.print(f"[red]Invalid --bump '{bump}' — must be one of: {', '.join(BUMP_TYPES)}[/]")
        raise typer.Exit(1)

    config = _load_or_exit()
    name   = config["name"]
    stack  = config.get("stack", "")
    cloud  = config.get("cloud", "local")
    meta   = STACK_META.get(stack, {})
    build_type = meta.get("build", "container")

    console.print(f"\n[bold #a78bfa]proj release[/] — [bold]{name}[/]\n")

    old_version = config.get("version", "0.1.0")
    new_version = _bump_version(old_version, bump)
    console.print(f"  Version:   [dim]{old_version}[/] → [bold green]{new_version}[/]")
    if no_deploy:
        console.print(f"  Deploy:    [dim]skipped (--no-deploy)[/]")
    if no_jira:
        console.print(f"  Jira:      [dim]skipped (--no-jira)[/]")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/]")
        return

    # --- CHANGELOG ---
    log = _git_log_since_last_tag()
    _update_changelog(name, new_version, log)
    console.print("  CHANGELOG updated")

    # --- Version in manifest files ---
    _bump_manifest_files(new_version, meta)

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
    if not no_deploy:
        _deploy(build_type, cloud, name, new_version, config)
    else:
        console.print("\n[dim]Deploy skipped.[/]")

    # --- Jira comment + transition ---
    if no_jira:
        console.print("[dim]Jira skipped.[/]")
    else:
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


def _bump_manifest_files(version: str, meta: dict) -> None:
    manifest, pattern, replacement = meta.get("manifest", (None, None, None))
    if not manifest or not Path(manifest).exists():
        return
    text = Path(manifest).read_text()
    bumped = re.sub(pattern, replacement.replace("{version}", version), text, count=1)
    Path(manifest).write_text(bumped)
    console.print(f"  Bumped version in [cyan]{manifest}[/]")


def _deploy(build_type: str, cloud: str, name: str, version: str, config: dict) -> None:
    if build_type == "databricks":
        _deploy_databricks(name, version, config)
        return

    if build_type == "iac":
        console.print(f"\n[dim]IaC release tagged. Run [bold]terraform apply[/] or [bold]pulumi up[/] to deploy.[/]")
        return

    if build_type == "data":
        console.print(f"\n[dim]Data/ML release tagged v{version}. No automated deploy step.[/]")
        return

    if build_type == "native":
        console.print(f"\n[dim]Native release tagged v{version}. Deploy via platform toolchain.[/]")
        return

    if build_type == "swift_native":
        console.print(f"\n[dim]Swift release tagged v{version}. Deploy via App Store Connect / TestFlight.[/]")
        return

    # container
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

    job_name = dbx.get("job_name", name)
    if dbx.get("launch_on_release", False):
        console.print(f"\nLaunching smoke run: [cyan]{job_name}[/]...")
        _run(["dbx", "launch", "--job", job_name, "--as-run-submit", "--trace"])
    else:
        console.print(f"  [dim]Skipping launch (set databricks.launch_on_release: true to enable)[/]")


def _notify_jira(jira_cfg: dict, epic_key: str, name: str, version: str, log: str) -> None:
    console.print(f"\nPosting Jira release comment...")
    try:
        client = jira_mod.connect(jira_cfg["base_url"], jira_cfg["token"])
        stakeholders = jira_cfg.get("stakeholders", [])
        mentions = " ".join(f"[~{u}]" for u in stakeholders)
        active_key = jira_mod.load_active_ticket()
        body = (
            f"*Released: {name} v{version}*\n\n"
            f"{mentions}\n\n"
            f"{{noformat}}\n{log}\n{{noformat}}"
        )
        jira_mod.post_status_log(client, body, epic_key, active_key)
        targets = ", ".join(filter(None, [epic_key, active_key]))
        console.print(f"  Comment posted on [cyan]{targets}[/]")

        active_key = jira_mod.load_active_ticket()
        if active_key:
            ok = jira_mod.transition_ticket(client, active_key, "Done")
            if ok:
                jira_mod.clear_active_ticket()
                console.print(f"  [green]Jira:[/] [cyan]{active_key}[/] → Done")

        remaining = jira_mod.get_open_tickets(client, epic_key)
        if not remaining:
            jira_mod.transition_ticket(client, epic_key, "Done")
            console.print(f"  [green]Jira:[/] [cyan]{epic_key}[/] → Done (all stories complete)")
        else:
            console.print(f"  [dim]{len(remaining)} {'story' if len(remaining) == 1 else 'stories'} still open — Epic stays active[/]")
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
