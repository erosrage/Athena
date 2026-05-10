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
    "Swift / Apple":    ["swift", "vapor", "swiftui", "ios"],
}

STACKS: list[str] = [s for stacks in STACK_CATEGORIES.values() for s in stacks]

CLOUDS           = ["azure", "aws", "gcp", "local"]
SECRETS_BACKENDS = ["dotenv", "sops", "azure-keyvault", "aws-ssm", "databricks-secrets"]

# ---------------------------------------------------------------------------
# Manifest pattern constants — (filename, regex, replacement)
# ---------------------------------------------------------------------------
_PYPROJECT = ("pyproject.toml", r'(version\s*=\s*")[^"]+(")',        r'\g<1>{version}\2')
_PKG_JSON  = ("package.json",   r'("version"\s*:\s*")[^"]+(")',       r'\g<1>{version}\2')
_CARGO     = ("Cargo.toml",     r'(version\s*=\s*")[^"]+(")',         r'\g<1>{version}\2')
_PUBSPEC   = ("pubspec.yaml",   r'(^version:\s*)\S+',                 r'\g<1>{version}')
_POM       = ("pom.xml",        r'(<version>)[^<]+(</version>)',       r'\g<1>{version}\2')
_COMPOSER  = ("composer.json",  r'("version"\s*:\s*")[^"]+(")',        r'\g<1>{version}\2')
_NONE      = (None, None, None)

# ---------------------------------------------------------------------------
# Per-stack metadata
# build: container | databricks | native | data | iac | swift_native
# manifest: tuple for version-bumping
# entry: primary entry-point hint for CLAUDE.md
# notes: CLAUDE.md stack-notes section
# ---------------------------------------------------------------------------
STACK_META: dict[str, dict] = {
    # Python
    "flask": {
        "build": "container", "manifest": _PYPROJECT, "entry": "app.py",
        "notes": "- Entry point: `app.py`\n- Run: `flask run --reload`\n- Deps: `pyproject.toml` / `requirements.txt`",
    },
    "fastapi": {
        "build": "container", "manifest": _PYPROJECT, "entry": "main.py",
        "notes": "- Entry point: `main.py`\n- Run: `uvicorn main:app --reload`\n- Docs auto-generated at `/docs`",
    },
    "django": {
        "build": "container", "manifest": _PYPROJECT, "entry": "manage.py",
        "notes": "- Entry point: `manage.py`\n- Run: `python manage.py runserver`\n- Migrations: `python manage.py migrate`",
    },
    "python-cli": {
        "build": "native", "manifest": _PYPROJECT, "entry": "src/main.py",
        "notes": "- Entry point: `src/main.py`\n- Tests: `pytest -v --tb=short`\n- Publish: `python -m build && twine upload dist/*`",
    },
    "streamlit": {
        "build": "container", "manifest": _PYPROJECT, "entry": "app.py",
        "notes": "- Entry point: `app.py`\n- Run: `streamlit run app.py`\n- Deploy: Streamlit Cloud or containerised",
    },
    # Node / TypeScript
    "express": {
        "build": "container", "manifest": _PKG_JSON, "entry": "src/index.js",
        "notes": "- Entry point: `src/index.js`\n- Run: `npx nodemon src/index.js`\n- Deps: `npm install`",
    },
    "nestjs": {
        "build": "container", "manifest": _PKG_JSON, "entry": "src/main.ts",
        "notes": "- Entry point: `src/main.ts`\n- Run: `npm run start:dev`\n- CLI: `nest generate`",
    },
    "ts-node": {
        "build": "container", "manifest": _PKG_JSON, "entry": "src/index.ts",
        "notes": "- Entry point: `src/index.ts`\n- Run: `npx tsx watch src/index.ts`\n- Build: `tsc`",
    },
    # Frontend
    "react": {
        "build": "native", "manifest": _PKG_JSON, "entry": "src/App.tsx",
        "notes": "- Entry point: `src/App.tsx`\n- Dev: `npm run dev`\n- Build: `npm run build` → `dist/`",
    },
    "nextjs": {
        "build": "container", "manifest": _PKG_JSON, "entry": "app/page.tsx",
        "notes": "- Entry point: `app/page.tsx`\n- Dev: `npm run dev`\n- Build: `npm run build`",
    },
    "vue": {
        "build": "native", "manifest": _PKG_JSON, "entry": "src/App.vue",
        "notes": "- Entry point: `src/App.vue`\n- Dev: `npm run dev`\n- Build: `npm run build` → `dist/`",
    },
    "svelte": {
        "build": "native", "manifest": _PKG_JSON, "entry": "src/App.svelte",
        "notes": "- Entry point: `src/App.svelte`\n- Dev: `npm run dev`\n- Build: `npm run build`",
    },
    "angular": {
        "build": "native", "manifest": _PKG_JSON, "entry": "src/app/app.component.ts",
        "notes": "- Entry point: `src/app/app.component.ts`\n- Dev: `npm start`\n- Build: `ng build --prod`",
    },
    # Systems
    "go": {
        "build": "container", "manifest": _NONE, "entry": "main.go",
        "notes": "- Entry point: `main.go`\n- Live reload: `air` (`go install github.com/air-verse/air@latest`)\n- Build: `go build -o bin/app`",
    },
    "rust": {
        "build": "container", "manifest": _CARGO, "entry": "src/main.rs",
        "notes": "- Entry point: `src/main.rs`\n- Live reload: `cargo watch -x run`\n- Build: `cargo build --release`",
    },
    "dotnet": {
        "build": "container", "manifest": _NONE, "entry": "Program.cs",
        "notes": "- Entry point: `Program.cs`\n- Run: `dotnet watch run`\n- Build: `dotnet publish -c Release`",
    },
    # Desktop / Mobile
    "electron": {
        "build": "native", "manifest": _PKG_JSON, "entry": "main.js",
        "notes": "- Entry point: `main.js`\n- Run: `npm run dev`\n- Build: `npm run build` via electron-builder",
    },
    "tauri": {
        "build": "native", "manifest": _PKG_JSON, "entry": "src-tauri/src/main.rs",
        "notes": "- Entry point: `src-tauri/src/main.rs`\n- Dev: `npm run tauri dev`\n- Build: `npm run tauri build`",
    },
    "react-native": {
        "build": "native", "manifest": _PKG_JSON, "entry": "App.tsx",
        "notes": "- Entry point: `App.tsx`\n- Dev: `npx react-native start`\n- Build: Android Studio / Xcode for release",
    },
    "flutter": {
        "build": "native", "manifest": _PUBSPEC, "entry": "lib/main.dart",
        "notes": "- Entry point: `lib/main.dart`\n- Run: `flutter run`\n- Build: `flutter build apk` / `flutter build ios`",
    },
    # Data / ML
    "databricks": {
        "build": "databricks", "manifest": _PYPROJECT, "entry": "src/main.py",
        "notes": "- Entry point: `src/main.py`\n- Pipeline: `src/pipeline.py`\n- Notebooks: `notebooks/`\n- Job config: `conf/deployment.yml`\n- Tests: `pytest tests/`",
    },
    "jupyter": {
        "build": "data", "manifest": _PYPROJECT, "entry": "notebooks/",
        "notes": "- Notebooks in `notebooks/`\n- Run: `jupyter lab`\n- Export: `jupyter nbconvert --to script`",
    },
    "mlflow": {
        "build": "data", "manifest": _PYPROJECT, "entry": "train.py",
        "notes": "- Entry point: `train.py`\n- Tracking UI: `mlflow ui`\n- Models: `mlflow models serve`",
    },
    "dbt": {
        "build": "data", "manifest": _NONE, "entry": "models/",
        "notes": "- Models in `models/`\n- Run: `dbt run`\n- Test: `dbt test`\n- Docs: `dbt docs serve`",
    },
    "bi-report": {
        "build": "data", "manifest": _NONE, "entry": "scripts/refresh.py",
        "notes": "- Refresh pipeline: `scripts/refresh.py`\n- Reports: `reports/`\n- Exports: `exports/`",
    },
    # Other Backend
    "spring-boot": {
        "build": "container", "manifest": _POM, "entry": "src/main/java",
        "notes": "- Entry point: `src/main/java`\n- Run: `./mvnw spring-boot:run`\n- Build: `./mvnw package`",
    },
    "rails": {
        "build": "container", "manifest": _NONE, "entry": "app/",
        "notes": "- Entry point: `app/`\n- Run: `bin/rails server`\n- Migrations: `bin/rails db:migrate`",
    },
    "laravel": {
        "build": "container", "manifest": _COMPOSER, "entry": "app/",
        "notes": "- Entry point: `app/`\n- Run: `php artisan serve`\n- Migrations: `php artisan migrate`",
    },
    # IaC
    "terraform": {
        "build": "iac", "manifest": _NONE, "entry": "main.tf",
        "notes": "- Entry: `main.tf`\n- Plan: `terraform plan`\n- Apply: `terraform apply`\n- State: configure backend in `backend.tf`",
    },
    "pulumi": {
        "build": "iac", "manifest": _NONE, "entry": "index.ts",
        "notes": "- Entry: `index.ts` (or `__main__.py`)\n- Preview: `pulumi preview`\n- Deploy: `pulumi up`",
    },
    # Swift / Apple
    "swift": {
        "build": "swift_native", "manifest": _NONE, "entry": "Sources/main.swift",
        "notes": "- Entry point: `Sources/main.swift`\n- Build: `swift build`\n- Test: `swift test`\n- Release: `swift build -c release`",
    },
    "vapor": {
        "build": "container", "manifest": _NONE, "entry": "Sources/App/configure.swift",
        "notes": "- Entry: `Sources/App/configure.swift`\n- Run: `swift run`\n- Build: `swift build -c release`\n- Containerised via `Dockerfile`",
    },
    "swiftui": {
        "build": "swift_native", "manifest": _NONE, "entry": "App/ContentView.swift",
        "notes": "- Entry: `App/ContentView.swift`\n- Build: Xcode or `xcodebuild`\n- Deploy: App Store Connect / TestFlight",
    },
    "ios": {
        "build": "swift_native", "manifest": _NONE, "entry": "App/AppDelegate.swift",
        "notes": "- Entry: `App/AppDelegate.swift`\n- Build: `xcodebuild archive`\n- Deploy: App Store Connect / TestFlight",
    },
}


def print_stack_menu(console: "Console") -> None:
    """Print a categorized, numbered stack menu."""
    idx = 1
    for category, stacks in STACK_CATEGORIES.items():
        console.print(f"\n  [dim]{category}[/]")
        pairs = []
        for stack in stacks:
            pairs.append(f"  [cyan]{idx:>2}[/]. {stack:<18}")
            idx += 1
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
