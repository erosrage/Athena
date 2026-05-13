from __future__ import annotations
import subprocess
import sys
from pathlib import Path

import typer
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Input, Label, Static

from proj.config import load_config

# proj binary lives next to the current interpreter (same pipx venv)
_PROJ = str(Path(sys.executable).parent / "proj")

app = typer.Typer()

# ---------------------------------------------------------------------------
# Retro pixel-art ASCII banner (fits ~72 cols)
# ---------------------------------------------------------------------------

_BANNER = """\
██████╗ ██████╗  ██████╗      ██╗
██╔══██╗██╔══██╗██╔═══██╗     ██║
██████╔╝██████╔╝██║   ██║     ██║
██╔═══╝ ██╔══██╗██║   ██║██   ██║
██║     ██║  ██║╚██████╔╝╚█████╔╝
╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚════╝"""

_TAGLINE = "L A Z Y   M O D E   ·   © 1994  P R O J  S Y S T E M S"

# ---------------------------------------------------------------------------
# Name-input modal  (retro styled)
# ---------------------------------------------------------------------------

class _NameModal(ModalScreen[str | None]):
    """Ask for a project name before running proj new."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    _NameModal {
        align: center middle;
    }
    _NameModal > Vertical {
        background: #0d0208;
        border: double #ffd60a;
        padding: 2 4;
        width: 54;
        height: auto;
    }
    _NameModal Label {
        margin-bottom: 1;
        color: #ffd60a;
        text-style: bold;
    }
    _NameModal Input {
        background: #1a0412;
        border: tall #ffd60a;
        color: #ffffff;
        margin-bottom: 1;
    }
    _NameModal Input:focus {
        border: tall #ff006e;
    }
    _NameModal #modal-buttons {
        height: auto;
    }
    _NameModal Button {
        margin-left: 1;
        background: #0d0208;
        border: double #ffd60a;
        color: #ffd60a;
    }
    _NameModal Button:hover {
        background: #2a1008;
        color: #ffffff;
    }
    _NameModal Button.-primary {
        border: double #39ff14;
        color: #39ff14;
    }
    _NameModal Button.-primary:hover {
        background: #0a2008;
        color: #ffffff;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("▶  E N T E R   P R O J E C T   N A M E :")
            yield Input(placeholder="my-project", id="name-input")
            with Center(id="modal-buttons"):
                yield Button("[ C R E A T E ]", variant="primary", id="ok")
                yield Button("[ C A N C E L ]", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            name = self.query_one("#name-input", Input).value.strip()
            self.dismiss(name or None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Main retro dashboard
# ---------------------------------------------------------------------------

class _LazyDashboard(App):

    CSS = """
    /* ── Global ─────────────────────────────────────────────── */
    Screen {
        background: #0d0208;
        align: center top;
    }

    /* ── Banner ──────────────────────────────────────────────── */
    #banner-box {
        width: 100%;
        height: auto;
        border: double #39ff14;
        margin: 1 2 0 2;
        padding: 0 2;
        align-horizontal: center;
    }

    #banner-art {
        color: #39ff14;
        text-style: bold;
        text-align: center;
        width: 100%;
    }

    #banner-tagline {
        color: #555555;
        text-align: center;
        width: 100%;
        padding-bottom: 0;
    }

    /* ── Project context strip ───────────────────────────────── */
    #ctx-strip {
        width: 100%;
        height: auto;
        padding: 0 4;
        margin-top: 1;
        align-horizontal: center;
    }

    #ctx-text {
        color: #ffd60a;
        text-style: bold;
        text-align: center;
        width: 100%;
    }

    /* ── Button grid ─────────────────────────────────────────── */
    #button-grid {
        grid-size: 3;
        grid-gutter: 1 2;
        padding: 1 2;
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    Button {
        width: 100%;
        height: 7;
        text-align: center;
        background: #0d0208;
        color: #888888;
        border: double #333333;
        text-style: bold;
    }

    Button:hover  { background: #160810; }
    Button:focus  { background: #160810; }

    /* Neon per-button colours */
    #btn-plan    { border: double #00e5ff; color: #00e5ff; }
    #btn-new     { border: double #39ff14; color: #39ff14; }
    #btn-dev     { border: double #ffd60a; color: #ffd60a; }
    #btn-build   { border: double #ff6b35; color: #ff6b35; }
    #btn-release { border: double #ff006e; color: #ff006e; }
    #btn-status  { border: double #bf5af2; color: #bf5af2; }

    #btn-plan:hover    { background: #001a20; }
    #btn-new:hover     { background: #021a00; }
    #btn-dev:hover     { background: #1a1200; }
    #btn-build:hover   { background: #1a0800; }
    #btn-release:hover { background: #1a0010; }
    #btn-status:hover  { background: #100020; }

    /* ── HUD status bar ──────────────────────────────────────── */
    #hud {
        width: 100%;
        height: auto;
        padding: 1 6 0 6;
        align-horizontal: center;
    }

    #hud-text {
        color: #39ff14;
        text-align: center;
        width: 100%;
        border-top: solid #1a1a1a;
        padding-top: 1;
    }

    /* ── Footer ──────────────────────────────────────────────── */
    Footer {
        background: #0d0208;
        color: #333333;
    }

    FooterKey {
        background: #1a0412;
        color: #39ff14;
    }

    FooterKey .footer-key--description {
        color: #555555;
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

    # --- Layout -----------------------------------------------------------

    def compose(self) -> ComposeResult:
        # Banner
        with Vertical(id="banner-box"):
            yield Static(_BANNER,  id="banner-art")
            yield Static(_TAGLINE, id="banner-tagline")

        # Project context strip
        with Vertical(id="ctx-strip"):
            if self.config:
                name  = self.config["name"].upper()
                stack = self.config.get("stack", "—").upper()
                cloud = self.config.get("cloud", "—").upper()
                yield Static(
                    f"▌ {name} ▌ {stack} ▌ {cloud} ▌",
                    id="ctx-text",
                )
            else:
                yield Static(
                    "▌ NO PROJECT FOUND ▌ PRESS  [ N ]  TO SCAFFOLD ▌",
                    id="ctx-text",
                )

        # Action grid
        yield Grid(
            Button("▶  P · L · A · N\n\n    [ P ]",     id="btn-plan"),
            Button("✚  N · E · W\n\n    [ N ]",          id="btn-new"),
            Button("⟳  D · E · V\n\n    [ D ]",          id="btn-dev"),
            Button("⚙  B · U · I · L · D\n\n    [ B ]", id="btn-build"),
            Button("★  R · E · L · E · A · S · E\n\n    [ L ]", id="btn-release"),
            Button("◈  S · T · A · T · U · S\n\n    [ S ]",     id="btn-status"),
            id="button-grid",
        )

        # HUD
        if self.config:
            jira_cfg = self.config.get("jira", {})
            epic     = (jira_cfg.get("epic_key") or "—").upper()
            version  = self.config.get("version", "—")
            secrets  = self.config.get("secrets_backend", "—").upper()
            with Vertical(id="hud"):
                yield Static(
                    f"▌ EPIC: {epic} ▌ VER: {version} ▌ SECRETS: {secrets} ▌",
                    id="hud-text",
                )

        yield Footer()

    # --- Button dispatcher ------------------------------------------------

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

    # --- Shell helper -----------------------------------------------------

    @work(thread=True)
    def _shell(self, *args: str) -> None:
        """Suspend TUI, hand off to interactive subprocess, then restore."""
        with self.suspend():
            subprocess.run([_PROJ, *args])

    # --- Actions ----------------------------------------------------------

    def action_run_plan(self)    -> None: self._shell("plan")
    def action_run_dev(self)     -> None: self._shell("dev")
    def action_run_build(self)   -> None: self._shell("build")
    def action_run_release(self) -> None: self._shell("release")
    def action_run_status(self)  -> None: self._shell("status")

    def action_run_new(self) -> None:
        def _on_name(name: str | None) -> None:
            if name:
                self._shell("new", name)
        self.push_screen(_NameModal(), _on_name)


# ---------------------------------------------------------------------------
# Typer entry point
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def lazy():
    """Full-screen retro TUI dashboard — run any proj command with a keypress."""
    config: dict | None = None
    try:
        config = load_config()
    except FileNotFoundError:
        pass
    _LazyDashboard(config).run()
