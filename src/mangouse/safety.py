"""Seat gates. App identity lives in policy.py (user config), not here."""

from __future__ import annotations

import os
import subprocess

from mangouse.errors import BadKey, InputBlocked, Readonly

_COMPOSITOR_MODS = frozenset({"super", "logo", "win", "meta"})


def allow_input_enabled(cli_flag: bool = False) -> bool:
    if cli_flag:
        return True
    if os.environ.get("MANGOUSE_ALLOW_INPUT", "") in {"1", "true", "yes"}:
        return True
    from mangouse.config import load_config

    return load_config().allow_input


def require_input(cli_flag: bool = False) -> None:
    if not allow_input_enabled(cli_flag):
        raise Readonly(
            "input disabled; pass --allow-input, set MANGOUSE_ALLOW_INPUT=1, "
            "or allow_input = true in config"
        )
    if session_locked():
        raise InputBlocked("session is locked")


def session_locked() -> bool:
    from mangouse.config import load_config

    for name in load_config().lock_procs:
        try:
            proc = subprocess.run(
                ["pgrep", "-x", name],
                check=False,
                capture_output=True,
                timeout=2,
            )
        except FileNotFoundError:
            return False  # no pgrep at all: the check cannot run
        except subprocess.TimeoutExpired:
            continue  # one slow probe must not skip the other lock clients
        if proc.returncode == 0:
            return True
    return False


def refuse_compositor_combo(combo: str) -> None:
    parts = {p.strip().lower() for p in combo.split("+") if p.strip()}
    if parts & _COMPOSITOR_MODS:
        raise BadKey(combo)
