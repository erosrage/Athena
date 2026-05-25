from __future__ import annotations

import os
import shutil
import subprocess


def available() -> bool:
    """True when running inside a cmux workspace and the cmux CLI is on PATH."""
    return bool(os.environ.get("CMUX_WORKSPACE_ID")) and shutil.which("cmux") is not None


def _run(args: list[str]) -> None:
    subprocess.run(args, check=False, capture_output=True, text=True)


def set_status(key: str, label: str, *, icon: str | None = None, color: str | None = None, priority: int | None = None) -> None:
    if not available():
        return
    cmd = ["cmux", "set-status", key, label]
    if icon:
        cmd.extend(["--icon", icon])
    if color:
        cmd.extend(["--color", color])
    if priority is not None:
        cmd.extend(["--priority", str(priority)])
    try:
        _run(cmd)
    except Exception:
        pass


def clear_status(key: str) -> None:
    if not available():
        return
    try:
        _run(["cmux", "clear-status", key])
    except Exception:
        pass


def set_progress(ratio: float, label: str = "") -> None:
    if not available():
        return
    cmd = ["cmux", "set-progress", str(ratio)]
    if label:
        cmd.extend(["--label", label])
    try:
        _run(cmd)
    except Exception:
        pass


def clear_progress() -> None:
    if not available():
        return
    try:
        _run(["cmux", "clear-progress"])
    except Exception:
        pass


def log(message: str, *, level: str = "info", source: str = "athena") -> None:
    if not available():
        return
    cmd = ["cmux", "log", message, "--level", level, "--source", source]
    try:
        _run(cmd)
    except Exception:
        pass


def notify(title: str, body: str = "", *, subtitle: str = "") -> None:
    if not available():
        return
    cmd = ["cmux", "notify", "--title", title]
    if subtitle:
        cmd.extend(["--subtitle", subtitle])
    if body:
        cmd.extend(["--body", body])
    try:
        _run(cmd)
    except Exception:
        pass
