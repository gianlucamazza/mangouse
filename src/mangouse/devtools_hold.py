"""One long-lived protocol client for the inspect endpoint.

Each new WebSocket to the engine re-prompts Allow. CLI processes therefore
do not talk to the engine: they talk to a holder over a user-only unix
socket under ``XDG_RUNTIME_DIR``. The holder keeps a single engine
connection for the seat session.

Not a DOM agent. Not a TCP service.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mangouse.models import Window

_HOLD_ENV = "MANGOUSE_DEVTOOLS_HOLD"
_ACCEPT_TIMEOUT = 1.0
_CLIENT_TIMEOUT = 8.0
_SPAWN_WAIT = 2.0


def runtime_dir() -> Path:
    raw = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    base = Path(raw) if raw else Path(f"/run/user/{os.getuid()}")
    path = base / "mangouse"
    path.mkdir(mode=0o700, exist_ok=True)
    return path


def socket_path() -> Path:
    return runtime_dir() / "devtools.sock"


def hold_enabled() -> bool:
    return os.environ.get(_HOLD_ENV, "1").strip().lower() not in {"0", "false", "no"}


def _encode(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode()


def _recv_json(sock: socket.socket) -> dict[str, Any]:
    buf = bytearray()
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf.extend(chunk)
    if not buf:
        raise OSError("holder closed")
    line = bytes(buf).split(b"\n", 1)[0]
    data = json.loads(line.decode())
    if not isinstance(data, dict):
        raise OSError("holder payload is not an object")
    return data


def call(request: dict[str, Any], *, timeout: float = _CLIENT_TIMEOUT) -> dict[str, Any] | None:
    """Send one request to a running holder. None if none is listening."""
    path = socket_path()
    if not path.exists():
        return None
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(path))
        sock.sendall(_encode(request))
        return _recv_json(sock)
    except OSError:
        return None
    finally:
        sock.close()


def ping() -> bool:
    reply = call({"op": "ping"}, timeout=1.0)
    return bool(reply and reply.get("ok") and reply.get("op") == "pong")


def stop() -> bool:
    reply = call({"op": "stop"}, timeout=1.0)
    if reply and reply.get("ok"):
        return True
    path = socket_path()
    if path.exists():
        with __import__("contextlib").suppress(OSError):
            path.unlink()
    return False


def ensure(*, spawn: bool = True) -> bool:
    """Return True when a holder is accepting requests."""
    if ping():
        return True
    if not spawn or not hold_enabled():
        return False
    from mangouse.devtools import browser_ws_url, configured_url

    if not browser_ws_url() and not configured_url():
        return False
    path = socket_path()
    if path.exists() and not ping():
        with __import__("contextlib").suppress(OSError):
            path.unlink()
    subprocess.Popen(
        [sys.executable, "-m", "mangouse", "devtools", "--hold"],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    deadline = time.time() + _SPAWN_WAIT
    while time.time() < deadline:
        if ping():
            return True
        time.sleep(0.05)
    return ping()


def _window_from(payload: dict[str, Any]) -> Window:
    return Window(
        id=int(payload.get("id") or 0),
        pid=int(payload.get("pid") or 0),
        app_id=str(payload.get("app_id") or ""),
        title=str(payload.get("title") or ""),
        output=str(payload.get("output") or ""),
        groups=list(payload.get("groups") or []),
        x=int(payload.get("x") or 0),
        y=int(payload.get("y") or 0),
        width=int(payload.get("width") or 0),
        height=int(payload.get("height") or 0),
        focused=bool(payload.get("focused", True)),
        visible=bool(payload.get("visible", True)),
    )


def window_payload(window: Window) -> dict[str, Any]:
    return {
        "id": window.id,
        "pid": window.pid,
        "app_id": window.app_id,
        "title": window.title,
        "output": window.output,
        "groups": list(window.groups),
        "x": window.x,
        "y": window.y,
        "width": window.width,
        "height": window.height,
        "focused": window.focused,
        "visible": window.visible,
    }


class Holder:
    """Owns one engine WebSocket and serves local CLI clients."""

    def __init__(self) -> None:
        self._engine: socket.socket | None = None
        self._msg_id = 100
        self._stop = False

    def close_engine(self) -> None:
        if self._engine is not None:
            with __import__("contextlib").suppress(OSError):
                self._engine.close()
            self._engine = None

    def connect_engine(self) -> str:
        """Return connected / pending / unset. Reuses an open socket."""
        if self._engine is not None:
            return "connected"
        from mangouse.devtools import _ws_connect, browser_ws_url

        ws = browser_ws_url()
        if not ws:
            return "unset"
        try:
            self._engine = _ws_connect(ws)
        except (OSError, TimeoutError):
            self._engine = None
            return "pending"
        return "connected"

    def call_engine(
        self,
        method: str,
        params: dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        from mangouse.devtools import _call

        if self._engine is None:
            raise OSError("holder has no engine")
        self._msg_id += 1
        try:
            return _call(
                self._engine,
                method,
                params,
                self._msg_id,
                session_id=session_id,
            )
        except (OSError, TimeoutError):
            self.close_engine()
            raise

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        op = str(request.get("op") or "")
        if op == "ping":
            return {"ok": True, "op": "pong"}
        if op == "stop":
            self._stop = True
            return {"ok": True, "op": "stop"}
        if op == "probe":
            return self._probe()
        if op == "click":
            return self._click(request)
        return {"ok": False, "error": "unknown_op"}

    def _probe(self) -> dict[str, Any]:
        from mangouse.devtools import _is_page

        state = self.connect_engine()
        pages = 0
        if state == "connected" and self._engine is not None:
            try:
                infos = self.call_engine("Target.getTargets", {}).get("targetInfos") or []
                pages = len([t for t in infos if _is_page(t)])
                if pages == 0:
                    state = "listening"
            except OSError:
                state = "pending"
        return {
            "ok": True,
            "op": "probe",
            "state": state,
            "pages": pages,
            "via": "hold",
            "holder": True,
        }

    def _click(self, request: dict[str, Any]) -> dict[str, Any]:
        from mangouse.devtools import click_on_engine

        state = self.connect_engine()
        if state != "connected" or self._engine is None:
            return {"ok": False, "error": state or "pending"}
        window = _window_from(request.get("window") or {})
        try:
            ok = click_on_engine(
                self._engine,
                global_x=float(request["global_x"]),
                global_y=float(request["global_y"]),
                window=window,
                button=str(request.get("button") or "left"),
                call=self.call_engine,
                close=False,
            )
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": bool(ok), "op": "click"}

    def serve(self) -> int:
        path = socket_path()
        if path.exists():
            if ping():
                return 0
            with __import__("contextlib").suppress(OSError):
                path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path))
        os.chmod(path, 0o600)
        server.listen(4)
        server.settimeout(_ACCEPT_TIMEOUT)

        def _stop(_signum: int, _frame: object) -> None:
            self._stop = True

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
        self.connect_engine()
        try:
            while not self._stop:
                try:
                    client, _ = server.accept()
                except TimeoutError:
                    continue
                except OSError:
                    if self._stop:
                        break
                    continue
                with client:
                    client.settimeout(_CLIENT_TIMEOUT)
                    try:
                        request = _recv_json(client)
                        reply = self.handle(request)
                        client.sendall(_encode(reply))
                    except OSError:
                        continue
        finally:
            self.close_engine()
            with __import__("contextlib").suppress(OSError):
                server.close()
            with __import__("contextlib").suppress(OSError):
                path.unlink()
        return 0


def run_holder() -> int:
    return Holder().serve()
