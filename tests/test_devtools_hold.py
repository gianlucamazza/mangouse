from __future__ import annotations

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
