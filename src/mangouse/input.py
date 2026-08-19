"""Seat input: wtype (keys) + ydotool (pointer) + backend focus/dispatch."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

from mangouse.backend import Backend
from mangouse.devtools import click_via_devtools
from mangouse.errors import BadArg, BadKey, MissingDep
from mangouse.policy import assert_target
from mangouse.safety import refuse_compositor_combo, require_input
from mangouse.screen import window_at
from mangouse.session import resolve_backend

Runner = Callable[[list[str]], str]

_MODIFIERS = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "shift": "shift",
    "alt": "alt",
    "altgr": "altgr",
}

_KEY_NAMES = {
    "enter": "Return",
    "return": "Return",
    "tab": "Tab",
    "escape": "Escape",
    "esc": "Escape",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "space": "space",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "page_up": "Prior",
    "pagedown": "Next",
    "page_down": "Next",
    "insert": "Insert",
}

_CLICK_CODES = {"left": "0xC0", "right": "0xC1", "middle": "0xC2"}


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise MissingDep(cmd[0]) from exc
    if proc.returncode != 0:
        raise MissingDep(f"{cmd[0]}: {(proc.stderr or proc.stdout or 'failed').strip()}")
    return proc.stdout


def _wtype(args: list[str], runner: Runner | None) -> str:
    exe = shutil.which("wtype")
    if not exe:
        raise MissingDep("wtype")
    cmd = [exe, *args]
    return runner(cmd) if runner else _run(cmd)


def _ydotool(args: list[str], runner: Runner | None) -> str:
    exe = shutil.which("ydotool")
    if not exe:
        raise MissingDep("ydotool")
    env_socket = os.environ.get("YDOTOOL_SOCKET") or f"/run/user/{os.getuid()}/.ydotool_socket"
    cmd = [exe, *args]
    if runner:
        return runner(cmd)
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "YDOTOOL_SOCKET": env_socket},
        )
    except subprocess.TimeoutExpired as exc:
        raise MissingDep("ydotool") from exc
    if proc.returncode != 0:
        raise MissingDep(f"ydotool: {(proc.stderr or proc.stdout or 'failed').strip()}")
    return proc.stdout


def _key_args(combo: str) -> list[str]:
    parts = [p.strip() for p in combo.split("+") if p.strip()]
    if not parts:
        raise BadKey(combo, "empty key combo")
    args: list[str] = []
    held: list[str] = []
    for part in parts[:-1]:
        mod = _MODIFIERS.get(part.lower())
        if not mod:
            raise BadKey(combo, f"unknown modifier {part}")
        args += ["-M", mod]
        held.append(mod)
    key = parts[-1]
    named = _KEY_NAMES.get(key.lower(), key)
    args += ["-k", named]
    for mod in reversed(held):
        args += ["-m", mod]
    return args


def _prepare(
    *,
    allow_input: bool,
    window_id: int | None,
    backend: Backend | None,
) -> Backend:
    require_input(allow_input)
    be = backend or resolve_backend()
    if window_id is not None:
        win = be.window(window_id)
        assert_target(win)
        be.focus_window(window_id)
    else:
        win = be.focusing()
        if win is not None:
            assert_target(win)
    return be


def type_text(
    text: str,
    *,
    allow_input: bool = False,
    window_id: int | None = None,
    backend: Backend | None = None,
    runner: Runner | None = None,
) -> dict[str, Any]:
    be = _prepare(allow_input=allow_input, window_id=window_id, backend=backend)
    _wtype(["--", text], runner)
    return {"typed": len(text), "backend": be.name}


def press_key(
    combo: str,
    *,
    allow_input: bool = False,
    window_id: int | None = None,
    backend: Backend | None = None,
    runner: Runner | None = None,
) -> dict[str, Any]:
    refuse_compositor_combo(combo)
    be = _prepare(allow_input=allow_input, window_id=window_id, backend=backend)
    _wtype(_key_args(combo), runner)
    return {"combo": combo, "backend": be.name}


def click(
    x: float,
    y: float,
    *,
    button: str = "left",
    allow_input: bool = False,
    window_id: int | None = None,
    backend: Backend | None = None,
    runner: Runner | None = None,
) -> dict[str, Any]:
    # Same focus path as type/key. A click that does not own the seat first is
    # how a webview reports nothing while ydotool still exits 0.
    be = _prepare(allow_input=allow_input, window_id=window_id, backend=backend)
    code = _CLICK_CODES.get(button)
    if not code:
        raise BadArg(f"unknown button {button}")
    target = window_at(be.windows(), x, y) or be.focusing()
    if target is not None:
        assert_target(target)
        try:
            if click_via_devtools(global_x=x, global_y=y, window=target, button=button):
                out: dict[str, Any] = {
                    "x": int(x),
                    "y": int(y),
                    "button": button,
                    "backend": be.name,
                    "via": "devtools",
                }
                if window_id is not None:
                    out["window_id"] = window_id
                return out
        except OSError:
            pass
    _ydotool(["mousemove", "-a", "-x", str(int(x)), "-y", str(int(y))], runner)
    _ydotool(["click", code], runner)
    out = {
        "x": int(x),
        "y": int(y),
        "button": button,
        "backend": be.name,
        "via": "ydotool",
    }
    if window_id is not None:
        out["window_id"] = window_id
    return out


def focus(
    window_id: int,
    *,
    allow_input: bool = False,
    backend: Backend | None = None,
) -> dict[str, Any]:
    require_input(allow_input)
    be = backend or resolve_backend()
    win = be.window(window_id)
    assert_target(win)
    be.focus_window(window_id)
    return {"window_id": window_id, "backend": be.name}


def dispatch(
    spec: str,
    *,
    allow_input: bool = False,
    backend: Backend | None = None,
) -> dict[str, Any]:
    require_input(allow_input)
    be = backend or resolve_backend()
    result = be.dispatch_action(spec)
    return {"spec": spec, "result": result, "backend": be.name}
