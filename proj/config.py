from pathlib import Path
import yaml

PROJ_FILE = "proj.yaml"

STACKS = ["flask", "electron", "go", "rust", "ts-node", "bi-report", "databricks"]
CLOUDS  = ["azure", "aws", "gcp", "local"]
SECRETS_BACKENDS = ["dotenv", "sops", "azure-keyvault", "aws-ssm", "databricks-secrets"]


def find_proj_root() -> Path:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / PROJ_FILE).exists():
            return parent
    raise FileNotFoundError(
        f"No {PROJ_FILE} found. Run [bold]proj new[/] to initialise a project."
    )


def load_config() -> dict:
    root = find_proj_root()
    with open(root / PROJ_FILE) as f:
        return yaml.safe_load(f)


def save_config(data: dict, root: Path | None = None) -> None:
    if root is None:
        root = find_proj_root()
    with open(root / PROJ_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
