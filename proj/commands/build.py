from __future__ import annotations
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm

from proj.config import load_config

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def build(
    multi_arch: bool = typer.Option(False, "--multi-arch", help="Build for linux/amd64 + linux/arm64"),
    push: bool       = typer.Option(True,  "--push/--no-push", help="Push image to registry after build"),
):
    """Build and package — Docker image for most stacks, Python wheel for Databricks."""

    config = _load_or_exit()
    name   = config["name"]
    stack  = config.get("stack", "")

    console.print(f"\n[bold #a78bfa]proj build[/] — [bold]{name}[/]\n")

    if stack == "databricks":
        _databricks_build(config)
        return

    version = config.get("version", "0.1.0")
    cloud   = config.get("cloud", "local")

    git_sha = _git_sha()
    tag     = f"{name}:{git_sha}"
    tag_ver = f"{name}:{version}"

    console.print(f"  Image tag: [cyan]{tag}[/]")
    console.print(f"  Version:   [cyan]{tag_ver}[/]")
    console.print(f"  Cloud:     [cyan]{cloud}[/]\n")

    # Build
    if multi_arch:
        _run(["docker", "buildx", "build",
              "--platform", "linux/amd64,linux/arm64",
              "-t", tag, "-t", tag_ver, "."])
    else:
        _run(["docker", "build", "-t", tag, "-t", tag_ver, "."])

    if not push or cloud == "local":
        console.print("\n[green]Build complete.[/] Image kept local.")
        return

    # Push
    registry = _registry_for(cloud, config)
    remote_tag     = f"{registry}/{tag}"
    remote_tag_ver = f"{registry}/{tag_ver}"

    _login(cloud, config)
    _run(["docker", "tag", tag, remote_tag])
    _run(["docker", "tag", tag_ver, remote_tag_ver])
    _run(["docker", "push", remote_tag])
    _run(["docker", "push", remote_tag_ver])

    console.print(f"\n[green]Pushed:[/] [bold]{remote_tag}[/]")
    console.print(f"[green]Pushed:[/] [bold]{remote_tag_ver}[/]")


def _registry_for(cloud: str, config: dict) -> str:
    registries = {
        "azure": config.get("acr_name", "myregistry") + ".azurecr.io",
        "aws":   config.get("aws_account_id", "123456789") + ".dkr.ecr." + config.get("aws_region", "us-east-1") + ".amazonaws.com",
        "gcp":   "gcr.io/" + config.get("gcp_project", "my-project"),
    }
    registry = registries.get(cloud)
    if not registry:
        console.print(f"[red]No registry configured for cloud: {cloud}[/]")
        raise typer.Exit(1)
    return registry


def _login(cloud: str, config: dict) -> None:
    console.print(f"Authenticating with [bold]{cloud}[/] registry...")
    if cloud == "azure":
        acr = config.get("acr_name", "myregistry")
        _run(["az", "acr", "login", "--name", acr])
    elif cloud == "aws":
        region  = config.get("aws_region", "us-east-1")
        account = config.get("aws_account_id", "")
        token_cmd = ["aws", "ecr", "get-login-password", "--region", region]
        result = subprocess.run(token_cmd, capture_output=True, text=True, check=True)
        registry = f"{account}.dkr.ecr.{region}.amazonaws.com"
        _run(["docker", "login", "--username", "AWS", "--password-stdin", registry],
             input=result.stdout)
    elif cloud == "gcp":
        _run(["gcloud", "auth", "configure-docker", "--quiet"])


def _databricks_build(config: dict) -> None:
    dbx     = config.get("databricks", {})
    name    = config["name"]
    version = config.get("version", "0.1.0")

    # Build Python wheel
    console.print("Building Python wheel...")
    _run(["python", "-m", "build", "--wheel", "--outdir", "dist/"])

    wheel = next(Path("dist").glob(f"*.whl"), None)
    if not wheel:
        console.print("[red]Wheel not found in dist/ after build.[/]")
        raise typer.Exit(1)
    console.print(f"  Wheel: [cyan]{wheel.name}[/]")

    # Upload to DBFS or Unity Catalog volume
    upload_path = dbx.get("wheel_path", f"dbfs:/FileStore/wheels/{name}")
    remote      = f"{upload_path}/{wheel.name}"
    console.print(f"\nUploading to [cyan]{remote}[/]...")
    _run(["databricks", "fs", "cp", "--overwrite", str(wheel), remote])

    # Deploy job definition
    deployment_file = Path("conf/deployment.yml")
    if deployment_file.exists():
        console.print("\nDeploying job definition...")
        _run(["dbx", "deploy", "--deployment-file", str(deployment_file)])

    console.print(f"\n[green]Databricks build complete.[/] v{version}")


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "latest"


def _run(cmd: list[str], input: str | None = None) -> None:
    console.print(f"  [dim]$ {' '.join(cmd)}[/]")
    subprocess.run(cmd, check=True, input=input, text=bool(input))


def _load_or_exit() -> dict:
    try:
        return load_config()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)
