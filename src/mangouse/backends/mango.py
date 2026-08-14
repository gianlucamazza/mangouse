"""MangoWM adapter: mmsg → generic Desktop/Window/Output."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mangouse.errors import IpcFailed, NoSession, UnknownWindow
from mangouse.models import Check, Cursor, Desktop, Group, Output, Window

Runner = Callable[[list[str]], str]


def default_runner(args: list[str]) -> str:
    mmsg = shutil.which("mmsg")
    if not mmsg:
        raise IpcFailed("mmsg not on PATH")
    if not os.environ.get("MANGO_INSTANCE_SIGNATURE"):
        raise NoSession("MANGO_INSTANCE_SIGNATURE is unset")
    try:
        proc = subprocess.run(
            [mmsg, *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        raise IpcFailed("mmsg timed out") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "mmsg failed").strip()
        raise IpcFailed(err)
    return proc.stdout


def parse_window(item: dict[str, Any]) -> Window:
    extras = {
        "floating": bool(item.get("is_floating")),
        "fullscreen": bool(item.get("is_fullscreen")),
        "scratchpad": bool(item.get("is_scratchpad")),
        "xwayland": bool(item.get("is_xwayland")),
        "urgent": bool(item.get("is_urgent")),
        "foreign_toplevel_id": str(item.get("foreign_toplevel_id") or ""),
    }
    return Window(
        id=int(item["id"]),
        pid=int(item.get("pid") or 0),
        app_id=str(item.get("appid") or ""),
        title=str(item.get("title") or ""),
        output=str(item.get("monitor") or ""),
        groups=[int(t) for t in item.get("tags") or []],
        x=int(item.get("x") or 0),
        y=int(item.get("y") or 0),
        width=int(item.get("width") or 0),
        height=int(item.get("height") or 0),
        focused=bool(item.get("is_focused")),
        visible=bool(item.get("is_visible")),
        extras=extras,
    )


def parse_output(item: dict[str, Any]) -> Output:
    groups = [
        Group(
            index=int(t["index"]),
            active=bool(t.get("is_active")),
            urgent=bool(t.get("is_urgent")),
            label=str(t.get("layout") or ""),
            window_count=int(t.get("client_count") or 0),
        )
        for t in item.get("tags") or []
    ]
    active = item.get("active_client") or {}
    focused_id = int(active["id"]) if active.get("id") is not None else None
    extras = {
        "layout_symbol": str(item.get("layout_symbol") or ""),
        "keyboardlayout": str(item.get("keyboardlayout") or ""),
        "keymode": str(item.get("keymode") or ""),
    }
    return Output(
        name=str(item["name"]),
        x=int(item.get("x") or 0),
        y=int(item.get("y") or 0),
        width=int(item.get("width") or 0),
        height=int(item.get("height") or 0),
        scale=float(item.get("scale") or 1),
        active=bool(item.get("active")),
        groups=groups,
        active_groups=[int(t) for t in item.get("active_tags") or []],
        focused_window_id=focused_id,
        extras=extras,
    )


class MangoBackend:
    name = "mango"

    def __init__(self, runner: Runner | None = None) -> None:
        self._runner = runner or default_runner

    def available(self) -> bool:
        sock = os.environ.get("MANGO_INSTANCE_SIGNATURE", "")
        return bool(sock) and Path(sock).exists() and shutil.which("mmsg") is not None

    def checks(self) -> list[Check]:
        sock = os.environ.get("MANGO_INSTANCE_SIGNATURE", "")
        sock_ok = bool(sock) and Path(sock).exists()
        mmsg = shutil.which("mmsg")
        rows = [
            Check(
                id="backend_socket",
                ok=sock_ok,
                detail=sock or "MANGO_INSTANCE_SIGNATURE unset",
                blocker=True,
            ),
            Check(
                id="backend_ipc",
                ok=bool(mmsg),
                detail=mmsg or "mmsg not on PATH",
                blocker=True,
            ),
        ]
        try:
            ver = self.version()
            rows.append(Check(id="backend_rpc", ok=True, detail=ver, blocker=True))
        except (NoSession, IpcFailed) as exc:
            rows.append(Check(id="backend_rpc", ok=False, detail=exc.message, blocker=True))
        return rows

    def raw(self, *args: str) -> Any:
        text = self._runner(list(args)).strip()
        if not text:
            raise IpcFailed("mmsg returned empty output")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise IpcFailed(f"mmsg returned non-JSON: {text[:120]!r}") from exc
        if isinstance(data, dict) and "error" in data:
            raise IpcFailed(str(data["error"]))
        return data

    def version(self) -> str:
        data = self.raw("get", "version")
        if isinstance(data, dict):
            return str(data.get("version", ""))
        return str(data)

    def windows(self) -> list[Window]:
        data = self.raw("get", "all-clients")
        return [parse_window(item) for item in data.get("clients", [])]

    def outputs(self) -> list[Output]:
        data = self.raw("get", "all-monitors")
        return [parse_output(item) for item in data.get("monitors", [])]

    def focusing(self) -> Window | None:
        data = self.raw("get", "focusing-client")
        if not data:
            return None
        return parse_window(data)

    def cursor(self) -> Cursor:
        data = self.raw("get", "cursorpos")
        return Cursor(
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            output=data.get("monitor"),
        )

    def desktop(self) -> Desktop:
        return Desktop(
            backend=self.name,
            version=self.version(),
            outputs=self.outputs(),
            windows=self.windows(),
            focused=self.focusing(),
            cursor=self.cursor(),
        )

    def window(self, window_id: int) -> Window:
        data = self.raw("get", "client", str(window_id))
        if not data:
            raise UnknownWindow(window_id)
        return parse_window(data)

    def focus_window(self, window_id: int) -> None:
        self.window(window_id)
        self.raw("dispatch", "focusid", f"client,{window_id}")

    def dispatch_action(self, spec: str) -> object:
        tokens = spec.split()
        if not tokens:
            raise IpcFailed("empty dispatch")
        return self.raw("dispatch", *tokens)
