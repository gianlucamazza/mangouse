from __future__ import annotations

from pathlib import Path

from mangouse.devtools import (
    browser_ws_url,
    chrome_inset,
    configured_url,
    pick_page,
    probe,
    viewport_from_global,
)
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


def test_viewport_subtracts_chrome() -> None:
    vx, vy = viewport_from_global(
        global_x=310, global_y=240, window=_win(), chrome_top=100, chrome_left=0
    )
    assert (vx, vy) == (300.0, 100.0)


def test_pick_page_by_title_hint() -> None:
    pages = [
        {"type": "page", "title": "Other", "webSocketDebuggerUrl": "ws://a"},
        {"type": "page", "title": "Sign in - Admin", "webSocketDebuggerUrl": "ws://b"},
        {"type": "iframe", "title": "Sign in - Admin", "webSocketDebuggerUrl": "ws://c"},
    ]
    picked = pick_page(pages, "Sign in - Admin extra chrome")
    assert picked is not None
    assert picked["webSocketDebuggerUrl"] == "ws://b"


def test_pick_page_accepts_target_id_without_page_socket() -> None:
    pages = [
        {"type": "page", "title": "Sign in - Admin", "targetId": "t1", "url": "https://ex.test/a"},
        {"type": "page", "title": "Other", "targetId": "t2", "url": "https://ex.test/b"},
    ]
    picked = pick_page(pages, "Sign in - Admin")
    assert picked is not None
    assert picked["targetId"] == "t1"


def test_pick_page_skips_inspector_targets() -> None:
    pages = [
        {
            "type": "page",
            "title": "inspect",
            "targetId": "t0",
            "url": "devtools://devtools/bundled/inspector.html",
        },
        {"type": "page", "title": "App", "targetId": "t1", "url": "https://ex.test/"},
    ]
    picked = pick_page(pages, None)
    assert picked is not None
    assert picked["targetId"] == "t1"


def test_pick_page_prefers_attached_among_title_matches() -> None:
    pages = [
        {
            "type": "page",
            "title": "Docs",
            "targetId": "t0",
            "url": "https://a.test/",
            "attached": False,
        },
        {
            "type": "page",
            "title": "Docs",
            "targetId": "t1",
            "url": "https://b.test/",
            "attached": True,
        },
    ]
    picked = pick_page(pages, "Docs")
    assert picked is not None
    assert picked["targetId"] == "t1"


def test_chrome_inset_from_outer_inner() -> None:
    top, left = chrome_inset(
        {"outerHeight": 900, "innerHeight": 800, "outerWidth": 1400, "innerWidth": 1400}
    )
    assert top == 100.0
    assert left == 0.0


def test_port_file_discovery(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("MANGOUSE_DEVTOOLS_URL", raising=False)
    monkeypatch.delenv("MANGOUSE_DEVTOOLS_WS", raising=False)
    monkeypatch.setattr(
        "mangouse.devtools.load_config", lambda: type("C", (), {"devtools_url": ""})()
    )
    port = tmp_path / "engine" / "DevToolsActivePort"
    port.parent.mkdir()
    port.write_text("9222\n/devtools/browser/abc\n")
    assert browser_ws_url() == "ws://127.0.0.1:9222/devtools/browser/abc"
    assert configured_url() == "http://127.0.0.1:9222"


def test_probe_unset_without_endpoint(monkeypatch) -> None:
    monkeypatch.setattr("mangouse.devtools_hold.call", lambda *a, **k: None)
    monkeypatch.delenv("MANGOUSE_DEVTOOLS_URL", raising=False)
    monkeypatch.delenv("MANGOUSE_DEVTOOLS_WS", raising=False)
    monkeypatch.setattr("mangouse.devtools._active_port_file", lambda: None)
    monkeypatch.setattr(
        "mangouse.devtools.load_config", lambda: type("C", (), {"devtools_url": ""})()
    )
    result = probe()
    assert result["state"] == "unset"
    assert result["ok"] is False
    assert result["via"] is None


def test_probe_pending_when_handshake_times_out(monkeypatch) -> None:
    monkeypatch.setattr("mangouse.devtools_hold.call", lambda *a, **k: None)
    monkeypatch.setenv("MANGOUSE_DEVTOOLS_WS", "ws://127.0.0.1:9/devtools/browser/x")
    monkeypatch.delenv("MANGOUSE_DEVTOOLS_URL", raising=False)
    monkeypatch.setattr(
        "mangouse.devtools.load_config", lambda: type("C", (), {"devtools_url": ""})()
    )
    monkeypatch.setattr("mangouse.devtools._active_port_file", lambda: None)
    monkeypatch.setattr("mangouse.devtools.configured_url", lambda: None)
    monkeypatch.setattr("mangouse.devtools.fetch_targets", lambda _base: [])

    def _boom(_url: str, timeout: float = 0.0):
        raise TimeoutError("handshake")

    monkeypatch.setattr("mangouse.devtools._ws_connect", _boom)
    result = probe()
    assert result["state"] == "pending"
    assert result["ok"] is False
    assert result["via"] == "ws"


def _server_frame(opcode: int, payload: bytes, *, fin: bool = True) -> bytes:
    """Server-to-client frame: no mask bit, as the engine sends them."""
    import struct

    head = bytearray([(0x80 if fin else 0x00) | opcode])
    n = len(payload)
    if n < 126:
        head.append(n)
    elif n < 65536:
        head.append(126)
        head.extend(struct.pack("!H", n))
    else:
        head.append(127)
        head.extend(struct.pack("!Q", n))
    return bytes(head) + payload


def test_ws_recv_reassembles_fragmented_text() -> None:
    """A message split across continuation frames must not arrive truncated."""
    import socket

    from mangouse.devtools import _ws_recv

    left, right = socket.socketpair()
    try:
        right.sendall(_server_frame(0x1, b'{"id":1,"res', fin=False))
        right.sendall(_server_frame(0x9, b"ping"))  # control frame interleaved
        right.sendall(_server_frame(0x0, b'ult":{}}', fin=True))
        left.settimeout(5.0)
        assert _ws_recv(left) == '{"id":1,"result":{}}'
    finally:
        left.close()
        right.close()


def test_ws_recv_rejects_an_oversized_frame() -> None:
    import socket
    import struct

    import pytest

    from mangouse.devtools import _MAX_FRAME, _ws_recv

    left, right = socket.socketpair()
    try:
        # Advertise more than the cap without sending it: must fail fast.
        right.sendall(bytes([0x81, 127]) + struct.pack("!Q", _MAX_FRAME + 1))
        left.settimeout(5.0)
        with pytest.raises(OSError):
            _ws_recv(left)
    finally:
        left.close()
        right.close()


def test_call_turns_invalid_json_into_oserror() -> None:
    """Callers guard the protocol path with `except OSError`; nothing else."""
    import socket

    import pytest

    from mangouse.devtools import _call

    left, right = socket.socketpair()
    try:
        left.settimeout(5.0)
        right.sendall(_server_frame(0x1, b"{not json"))
        with pytest.raises(OSError):
            _call(left, "Target.getTargets", {}, 1)
    finally:
        left.close()
        right.close()
