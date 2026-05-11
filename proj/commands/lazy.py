from __future__ import annotations
import subprocess
import sys

import typer
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from proj.config import load_config

app = typer.Typer()

# ---------------------------------------------------------------------------
# Name-input modal (used by the New button)
# ---------------------------------------------------------------------------

class _NameModal(ModalScreen[str | None]):
    """Ask for a project name before running proj new."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    _NameModal {
        align: center middle;
    }
    _NameModal > Vertical {
        background: $panel;
        border: thick $primary;
        padding: 2 4;
        width: 52;
        height: auto;
    }
    _NameModal Label {
        margin-bottom: 1;
        color: $text;
    }
    _NameModal Input {
        margin-bottom: 1;
    }
    _NameModal #modal-buttons {
        height: auto;
        align-horizontal: right;
    }
    _NameModal Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Enter a project name:")
            yield Input(placeholder="my-project", id="name-input")
            with Center(id="modal-buttons"):
                yield Button("Create", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            name = self.query_one("#name-input", Input).value.strip()
            self.dismiss(name or None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        self.dismiss(name or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Main TUI dashboard
# ---------------------------------------------------------------------------

class _LazyDashboard(App):

    CSS = """
    Screen {
        background: $surface;
        align: center top;
    }

    #header-box {
        width: 100%;
        height: auto;
        padding: 1 2 0 2;
        align-horizontal: center;
    }

    #project-title {
        text-align: center;
        color: #a78bfa;
        text-style: bold;
        width: 100%;
    }

    #project-ctx {
        text-align: center;
        color: $text-muted;
        width: 100%;
        padding-bottom: 1;
    }

    #button-grid {
        grid-size: 3;
        grid-gutter: 1 2;
        padding: 1 4;
        width: 80;
        height: auto;
    }

    Button {
        width: 100%;
        height: 5;
        text-align: center;
    }

    #status-bar {
        padding: 1 2;
        color: $text-muted;
        text-align: center;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("p", "run_plan",    "Plan"),
        Binding("n", "run_new",     "New"),
        Binding("d", "run_dev",     "Dev"),
        Binding("b", "run_build",   "Build"),
        Binding("l", "run_release", "reLease"),
        Binding("s", "run_status",  "Status"),
        Binding("q", "quit",        "Quit"),
    ]

    def __init__(self, config: dict | None) -> None:
        super().__init__()
        self.config = config

    # --- Layout ---

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="header-box"):
            if self.config:
                name  = self.config["name"]
                stack = self.config.get("stack", "—")
                cloud = self.config.get("cloud", "—")
                yield Static(f"proj lazy  ·  {name}", id="project-title")
                yield Static(f"{stack}  /  {cloud}", id="project-ctx")
            else:
                yield Static("proj lazy mode", id="project-title")
                yield Static("No proj.yaml found — press [N] to scaffold a new project", id="project-ctx")

        yield Grid(
            Button("⚡ Plan\n[P]",     variant="primary", id="btn-plan"),
            Button("✦  New\n[N]",     variant="success", id="btn-new"),
            Button("⟳  Dev\n[D]",     variant="warning", id="btn-dev"),
            Button("⚙  Build\n[B]",   variant="error",   id="btn-build"),
            Button("🚀 Release\n[L]",  variant="primary", id="btn-release"),
            Button("◎  Status\n[S]",  variant="default", id="btn-status"),
            id="button-grid",
        )

        if self.config:
            jira_cfg = self.config.get("jira", {})
            epic     = jira_cfg.get("epic_key") or "—"
            version  = self.config.get("version", "—")
            secrets  = self.config.get("secrets_backend", "—")
            yield Static(
                f"Jira: {epic}  ·  Version: {version}  ·  Secrets: {secrets}",
                id="status-bar",
            )

        yield Footer()

    # --- Button dispatcher ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        dispatch = {
            "btn-plan":    self.action_run_plan,
            "btn-new":     self.action_run_new,
            "btn-dev":     self.action_run_dev,
            "btn-build":   self.action_run_build,
            "btn-release": self.action_run_release,
            "btn-status":  self.action_run_status,
        }
        handler = dispatch.get(event.button.id)
        if handler:
            handler()

    # --- Shell helper ---

    def _shell(self, *args: str) -> None:
        """Suspend the TUI, run a proj subcommand interactively, then restore."""
        with self.suspend():
            subprocess.run([sys.executable, "-m", "proj", *args])

    # --- Actions ---

    def action_run_plan(self) -> None:
        self._shell("plan")

    def action_run_new(self) -> None:
        def _on_name(name: str | None) -> None:
            if name:
                self._shell("new", name)
        self.push_screen(_NameModal(), _on_name)

    def action_run_dev(self) -> None:
        self._shell("dev")

    def action_run_build(self) -> None:
        self._shell("build")

    def action_run_release(self) -> None:
        self._shell("release")

    def action_run_status(self) -> None:
        self._shell("status")


# ---------------------------------------------------------------------------
# Typer entry point
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def lazy():
    """Full-screen TUI dashboard — run any proj command with a single keypress."""
    config: dict | None = None
    try:
        config = load_config()
    except FileNotFoundError:
        pass
    _LazyDashboard(config).run()
