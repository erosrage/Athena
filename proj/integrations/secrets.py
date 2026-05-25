from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

console = Console()


def load(backend: str, config: dict) -> dict[str, str]:
    """Load secrets into os.environ and return a dict of loaded keys."""
    handlers = {
        "dotenv":               _load_dotenv,
        "sops":                 _load_sops,
        "azure-keyvault":       _load_azure_keyvault,
        "aws-ssm":              _load_aws_ssm,
        "databricks-secrets":   _load_databricks_secrets,
    }
    handler = handlers.get(backend)
    if not handler:
        console.print(f"[yellow]Unknown secrets backend: {backend}. Skipping.[/]")
        return {}
    return handler(config)


def _load_dotenv(config: dict) -> dict[str, str]:
    env_file = Path(config.get("env_file", ".env"))
    if not env_file.exists():
        console.print(f"  [yellow].env not found at {env_file}. Copy .env.example to get started.[/]")
        return {}
    load_dotenv(env_file, override=True)
    console.print(f"  [dim]Loaded secrets from {env_file}[/]")
    with open(env_file) as f:
        keys = [
            line.split("=")[0].strip()
            for line in f
            if line.strip() and not line.startswith("#") and "=" in line
        ]
    return {k: os.environ.get(k, "") for k in keys}


def _load_sops(config: dict) -> dict[str, str]:
    enc_file = Path(config.get("sops_file", ".env.enc"))
    if not enc_file.exists():
        console.print(f"  [yellow]SOPS file not found: {enc_file}[/]")
        return {}
    result = subprocess.run(
        ["sops", "--decrypt", "--output-type", "dotenv", str(enc_file)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        console.print(f"  [red]SOPS decrypt failed: {result.stderr.strip()}[/]")
        return {}
    loaded = {}
    for line in result.stdout.splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()
            loaded[k.strip()] = v.strip()
    console.print(f"  [dim]Loaded {len(loaded)} secrets via SOPS[/]")
    return loaded


def _load_azure_keyvault(config: dict) -> dict[str, str]:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    vault_url = config.get("keyvault_url")
    if not vault_url:
        console.print("  [red]keyvault_url not set in athena.yaml[/]")
        return {}

    client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
    loaded = {}
    for prop in client.list_properties_of_secrets():
        secret = client.get_secret(prop.name)
        env_key = prop.name.upper().replace("-", "_")
        os.environ[env_key] = secret.value
        loaded[env_key] = secret.value
    console.print(f"  [dim]Loaded {len(loaded)} secrets from Azure Key Vault[/]")
    return loaded


def _load_aws_ssm(config: dict) -> dict[str, str]:
    import boto3

    prefix = config.get("ssm_prefix", f"/{config.get('name', 'project')}/")
    client = boto3.client("ssm", region_name=config.get("aws_region", "us-east-1"))

    paginator = client.get_paginator("get_parameters_by_path")
    loaded = {}
    for page in paginator.paginate(Path=prefix, WithDecryption=True):
        for param in page["Parameters"]:
            key = param["Name"].replace(prefix, "").upper().replace("-", "_").replace("/", "_")
            os.environ[key] = param["Value"]
            loaded[key] = param["Value"]
    console.print(f"  [dim]Loaded {len(loaded)} secrets from AWS SSM ({prefix})[/]")
    return loaded


def _load_databricks_secrets(config: dict) -> dict[str, str]:
    dbx = config.get("databricks", {})
    scope = dbx.get("secret_scope", config.get("name", "project"))
    keys  = dbx.get("secret_keys", [])

    if not keys:
        console.print(f"  [yellow]No secret_keys listed under databricks.secret_keys in athena.yaml — skipping.[/]")
        return {}

    loaded = {}
    for key in keys:
        result = subprocess.run(
            ["databricks", "secrets", "get-secret", "--scope", scope, "--key", key],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            console.print(f"  [yellow]Could not fetch secret {scope}/{key}: {result.stderr.strip()}[/]")
            continue
        # databricks CLI returns value as base64-encoded JSON: {"value": "..."}
        import base64, json as _json
        try:
            value = _json.loads(result.stdout).get("value", "")
            value = base64.b64decode(value).decode()
        except Exception:
            value = result.stdout.strip()
        env_key = key.upper().replace("-", "_")
        os.environ[env_key] = value
        loaded[env_key] = value

    console.print(f"  [dim]Loaded {len(loaded)} secrets from Databricks secret scope [{scope}][/]")
    return loaded
