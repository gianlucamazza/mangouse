from __future__ import annotations

import contextlib
import time
from pathlib import Path

from mangouse.devtools import click_via_devtools, probe
from mangouse.devtools_hold import Holder, call, hold_enabled, socket_path, window_payload
from mangouse.models import Window


def _win() -> Window:
    return Window(
        id=1,
        pid=1,
        app_id="app",
        title="Sign in - Admin",
        output="DP-2",
        groups=[1],
        x=10,
        y=40,
        width=1400,
        height=900,
        focused=True,
        visible=True,
    )


def test_socket_path_uses_runtime_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    path = socket_path()
    assert path == tmp_path / "mangouse" / "devtools.sock"
    assert path.parent.is_dir()


def test_hold_enabled_env(monkeypatch) -> None:
    monkeypatch.delenv("MANGOUSE_DEVTOOLS_HOLD", raising=False)
    assert hold_enabled() is True
    monkeypatch.setenv("MANGOUSE_DEVTOOLS_HOLD", "0")
    assert hold_enabled() is False


def test_holder_ping_and_unknown_op() -> None:
    holder = Holder()
    assert holder.handle({"op": "ping"}) == {"ok": True, "op": "pong"}
    assert holder.handle({"op": "nope"})["ok"] is False


def test_probe_prefers_running_holder(monkeypatch) -> None:
    monkeypatch.setattr(
        "mangouse.devtools_hold.call",
        lambda req, timeout=8.0: {
            "ok": True,
            "op": "probe",
            "state": "connected",
            "pages": 3,
            "via": "hold",
            "holder": True,
        },
    )
    result = probe()
    assert result["state"] == "connected"
    assert result["via"] == "hold"
    assert result["pages"] == 3
    assert result["holder"] is True


def test_probe_falls_back_when_holder_absent(monkeypatch) -> None:
    monkeypatch.setattr("mangouse.devtools_hold.call", lambda req, timeout=8.0: None)
    monkeypatch.delenv("MANGOUSE_DEVTOOLS_URL", raising=False)
    monkeypatch.delenv("MANGOUSE_DEVTOOLS_WS", raising=False)
    monkeypatch.setattr("mangouse.devtools._active_port_file", lambda: None)
    monkeypatch.setattr(
        "mangouse.devtools.load_config", lambda: type("C", (), {"devtools_url": ""})()
    )
    result = probe()
    assert result["state"] == "unset"
    assert result.get("holder") is None


def test_click_via_uses_holder_and_skips_direct(monkeypatch) -> None:
    seen: list[dict] = []

    def _hold(req, timeout=8.0):
        seen.append(req)
        return {"ok": True, "op": "click"}

    monkeypatch.setattr("mangouse.devtools_hold.ensure", lambda spawn=True: True)
    monkeypatch.setattr("mangouse.devtools_hold.call", _hold)

    def _boom(*_a, **_k):
        raise AssertionError("direct engine client must not open")

    monkeypatch.setattr("mangouse.devtools._ws_connect", _boom)
    assert click_via_devtools(global_x=100, global_y=200, window=_win()) is True
    assert seen[0]["op"] == "click"
    assert seen[0]["window"]["title"] == "Sign in - Admin"


def test_click_via_holder_false_is_not_a_direct_fallback(monkeypatch) -> None:
    monkeypatch.setattr("mangouse.devtools_hold.ensure", lambda spawn=True: True)
    monkeypatch.setattr(
        "mangouse.devtools_hold.call",
        lambda req, timeout=8.0: {"ok": False, "error": "pending"},
    )
    monkeypatch.setattr(
        "mangouse.devtools._ws_connect",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no fallback")),
    )
    assert click_via_devtools(global_x=100, global_y=200, window=_win()) is False


def test_window_payload_roundtrip() -> None:
    win = _win()
    assert window_payload(win)["title"] == win.title
    assert window_payload(win)["x"] == 10


def test_call_none_without_socket(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert call({"op": "ping"}) is None


def _run_holder(tmp_path: Path, monkeypatch):
    """A real Holder on an isolated socket, with no engine to reach.

    Hermetic on purpose: a unit test must never open the developer's live
    browser, which would block on the inspect Allow dialog.
    """
    import socket
    import threading

    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("MANGOUSE_DEVTOOLS_HOLD", "0")
    monkeypatch.setattr("mangouse.devtools.browser_ws_url", lambda: "")

    holder = Holder()
    thread = threading.Thread(target=holder.serve, daemon=True)
    thread.start()
    path = tmp_path / "mangouse" / "devtools.sock"
    for _ in range(200):
        if path.exists() and call({"op": "ping"}, timeout=1.0):
            break
        time.sleep(0.02)
    assert call({"op": "ping"}, timeout=1.0), "holder never came up"
    assert socket.AF_UNIX  # unix-only by design
    return path, thread


def _stop_holder(thread) -> None:
    call({"op": "stop"}, timeout=2.0)
    thread.join(timeout=5.0)
    assert not thread.is_alive(), "holder did not exit"


def test_holder_survives_a_malformed_request(tmp_path: Path, monkeypatch) -> None:
    """Regression: JSONDecodeError is not an OSError, so serve() died on it."""
    import socket

    path, thread = _run_holder(tmp_path, monkeypatch)
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect(str(path))
        client.sendall(b"not json at all\n")
        with contextlib.suppress(OSError):
            client.recv(4096)
        client.close()
        assert call({"op": "ping"}, timeout=2.0) == {"ok": True, "op": "pong"}
    finally:
        _stop_holder(thread)


def test_holder_socket_is_owner_only(tmp_path: Path, monkeypatch) -> None:
    import stat

    path, thread = _run_holder(tmp_path, monkeypatch)
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    finally:
        _stop_holder(thread)


def test_recv_json_rejects_an_endless_line() -> None:
    """A peer that never sends a newline must not grow the holder's memory."""
    import socket
    import threading

    import pytest

    from mangouse.devtools_hold import _MAX_REQUEST, _recv_json

    left, right = socket.socketpair()
    stop = threading.Event()

    def _flood() -> None:
        with contextlib.suppress(OSError):
            while not stop.is_set():
                right.sendall(b"x" * 65536)  # never a newline

    sender = threading.Thread(target=_flood, daemon=True)
    sender.start()
    try:
        left.settimeout(10.0)
        with pytest.raises(OSError):
            _recv_json(left)
    finally:
        stop.set()
        left.close()
        right.close()
        sender.join(timeout=5.0)
    assert _MAX_REQUEST > 0
