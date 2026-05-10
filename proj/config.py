from pathlib import Path
from typing import TYPE_CHECKING
import yaml

if TYPE_CHECKING:
    from rich.console import Console

PROJ_FILE = "proj.yaml"

# Ordered dict — category → stacks. STACKS is derived from this.
STACK_CATEGORIES: dict[str, list[str]] = {
    "Python":           ["flask", "fastapi", "django", "python-cli", "streamlit"],
    "Node/TypeScript":  ["express", "nestjs", "ts-node"],
    "Frontend":         ["react", "nextjs", "vue", "svelte", "angular"],
    "Systems":          ["go", "rust", "dotnet"],
    "Desktop/Mobile":   ["electron", "tauri", "react-native", "flutter"],
    "Data/ML":          ["databricks", "jupyter", "mlflow", "dbt", "bi-report"],
    "Other Backend":    ["spring-boot", "rails", "laravel"],
    "IaC":              ["terraform", "pulumi"],
}

STACKS: list[str] = [s for stacks in STACK_CATEGORIES.values() for s in stacks]

CLOUDS           = ["azure", "aws", "gcp", "local"]
SECRETS_BACKENDS = ["dotenv", "sops", "azure-keyvault", "aws-ssm", "databricks-secrets"]


def print_stack_menu(console: "Console") -> None:
    """Print a categorized, numbered stack menu."""
    idx = 1
    for category, stacks in STACK_CATEGORIES.items():
        console.print(f"\n  [dim]{category}[/]")
        # Two columns
        pairs = []
        for stack in stacks:
            pairs.append(f"  [cyan]{idx:>2}[/]. {stack:<18}")
            idx += 1
        # Print in rows of 2
        for i in range(0, len(pairs), 2):
            console.print("".join(pairs[i:i+2]))


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
