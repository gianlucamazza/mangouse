"""Optional DevTools Protocol input (HTTP + WebSocket).

A running page that speaks the DevTools Protocol accepts
``Input.dispatchMouseEvent`` in CSS viewport pixels. Seat evdev clicks
often never reach that surface. This module is protocol-generic: it does
not name browsers. Configure ``devtools_url`` (or ``MANGOUSE_DEVTOOLS_URL``).
If those are empty, a ``DevToolsActivePort`` file under the user config
tree is enough — some inspectors answer the browser WebSocket but not
HTTP ``/json/list``.

Not a DOM/AX agent. Official agent tooling for that is a separate MCP.
CLI processes share one engine client via ``devtools_hold`` so the
inspect Allow prompt happens once per seat session, not once per
command.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import socket
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mangouse.config import load_config
from mangouse.models import Window

_TIMEOUT = 8.0
_PROBE_TIMEOUT = 3.0
# A CDP reply is JSON, not a stream. Cap it so a hostile or wedged endpoint
# cannot drive this process out of memory.
_MAX_FRAME = 32 * 1024 * 1024


def _config_roots() -> list[Path]:
    roots: list[Path] = []
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        roots.append(Path(xdg))
    roots.append(Path.home() / ".config")
    return roots


def _active_port_file() -> Path | None:
    seen: set[Path] = set()
    for root in _config_roots():
        if not root.is_dir():
            continue
        for path in root.glob("*/DevToolsActivePort"):
            resolved = path.resolve()
            if resolved in seen or not path.is_file():
                continue
            seen.add(resolved)
            return path
    return None


def _port_file_ws(path: Path) -> str | None:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None
    if len(lines) >= 2 and lines[0].strip().isdigit():
        return f"ws://127.0.0.1:{lines[0].strip()}{lines[1].strip()}"
    return None


def browser_ws_url() -> str | None:
    """Discover the browser WebSocket from DevToolsActivePort or HTTP /json."""
    explicit = os.environ.get("MANGOUSE_DEVTOOLS_WS", "").strip()
    if explicit:
        return explicit
    port_file = _active_port_file()
    if port_file:
        ws = _port_file_ws(port_file)
        if ws:
            return ws
    base = configured_url()
    if not base:
        return None
    req = urllib.request.Request(f"{base}/json/version", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    ws = body.get("webSocketDebuggerUrl") if isinstance(body, dict) else None
    return str(ws) if ws else None


def configured_url() -> str | None:
    env = os.environ.get("MANGOUSE_DEVTOOLS_URL", "").strip()
    if env:
        return env.rstrip("/")
    url = (load_config().devtools_url or "").strip()
    if url:
        return url.rstrip("/")
    port_file = _active_port_file()
    if port_file:
        port = port_file.read_text().splitlines()[:1]
        if port and port[0].strip().isdigit():
            return f"http://127.0.0.1:{port[0].strip()}"
    return None


def _discovery_via() -> str | None:
    if os.environ.get("MANGOUSE_DEVTOOLS_URL", "").strip():
        return "env"
    if os.environ.get("MANGOUSE_DEVTOOLS_WS", "").strip():
        return "ws"
    if (load_config().devtools_url or "").strip():
        return "config"
    if _active_port_file() is not None:
        return "port-file"
    return None


def viewport_from_global(
    *,
    global_x: float,
    global_y: float,
    window: Window,
    chrome_top: float,
    chrome_left: float = 0.0,
) -> tuple[float, float]:
    """Map seat coordinates into the page viewport (CSS pixels)."""
    return (
        global_x - window.x - chrome_left,
        global_y - window.y - chrome_top,
    )


def _is_page(item: dict[str, Any]) -> bool:
    kind = item.get("type")
    if kind not in (None, "page"):
        return False
    if not (item.get("webSocketDebuggerUrl") or item.get("targetId") or item.get("id")):
        return False
    url = str(item.get("url") or "")
    return not url.startswith("devtools://")


def _hint_match(item: dict[str, Any], hint: str) -> bool:
    title = str(item.get("title") or "").lower()
    url = str(item.get("url") or "").lower()
    if title and (title in hint or hint[: max(8, len(title))] in title):
        return True
    return bool(url and (url in hint or hint in url))


def pick_page(pages: list[dict[str, Any]], title_hint: str | None) -> dict[str, Any] | None:
    """Pick the visible page. Compositor title is the active tab.

    Accepts HTTP ``/json/list`` rows (need a page WebSocket) and
    ``Target.getTargets`` rows (need ``targetId``). Inspector-internal
    targets are skipped. Title/URL hint wins so a seat click stays on
    the tab the user sees; ``attached`` breaks ties.
    """
    candidates = [p for p in pages if _is_page(p)]
    if not candidates:
        return None
    hint = (title_hint or "").strip().lower()
    if hint:
        matched = [p for p in candidates if _hint_match(p, hint)]
        if matched:
            candidates = matched
    candidates.sort(key=lambda p: 1 if p.get("attached") else 0, reverse=True)
    return candidates[0]


def fetch_targets(base: str) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        f"{base}/json/list",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []
    return body if isinstance(body, list) else []


def _targets_from_browser_ws(ws: str, timeout: float) -> tuple[list[dict[str, Any]], str]:
    """Return (page targets, state). state is connected / pending / listening."""
    try:
        sock = _ws_connect(ws, timeout=timeout)
    except TimeoutError:
        return [], "pending"
    except OSError:
        return [], "pending"
    try:
        result = _call(sock, "Target.getTargets", {}, 1)
    except (OSError, TimeoutError):
        return [], "pending"
    finally:
        sock.close()
    infos = result.get("targetInfos") or []
    pages = [t for t in infos if t.get("type") == "page"]
    return pages, ("connected" if pages else "listening")


def probe(base: str | None = None) -> dict[str, Any]:
    if base is None:
        from mangouse.devtools_hold import call as hold_call

        held = hold_call({"op": "probe"})
        if held and held.get("ok") and held.get("op") == "probe":
            return {
                "ok": held.get("state") == "connected",
                "url": configured_url() or browser_ws_url(),
                "pages": int(held.get("pages") or 0),
                "state": held.get("state") or "pending",
                "via": "hold",
                "holder": True,
            }
    url = base or configured_url()
    ws = browser_ws_url()
    via = _discovery_via()
    if base and not via:
        via = "http"
    if not url and not ws:
        return {"ok": False, "url": None, "pages": 0, "state": "unset", "via": None}

    pages = fetch_targets(url) if url else []
    state = "connected" if pages else None
    if pages and via is None:
        via = "http"
    if not pages and ws:
        pages, state = _targets_from_browser_ws(ws, timeout=_PROBE_TIMEOUT)
        if via is None:
            via = "port-file"
    if state is None:
        state = "listening" if (url or ws) else "unset"
    return {
        "ok": state == "connected",
        "url": url or ws,
        "pages": len(pages),
        "state": state,
        "via": via,
    }


def _ws_connect(ws_url: str, timeout: float = _TIMEOUT) -> socket.socket:
    parsed = urlparse(ws_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    sock = socket.create_connection((host, port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(req.encode())
    header = b""
    while b"\r\n\r\n" not in header:
        chunk = sock.recv(4096)
        if not chunk:
            sock.close()
            raise OSError("devtools handshake closed")
        header += chunk
    if b" 101 " not in header.split(b"\r\n", 1)[0]:
        sock.close()
        raise OSError("devtools handshake refused")
    expected = base64.b64encode(
        hashlib.sha1(f"{key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11".encode()).digest()
    )
    if expected not in header:
        sock.close()
        raise OSError("devtools accept mismatch")
    sock.settimeout(timeout)
    return sock


def _ws_send(sock: socket.socket, text: str) -> None:
    raw = text.encode()
    header = bytearray([0x81])
    n = len(raw)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    mask = os.urandom(4)
    header.extend(mask)
    payload = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
    sock.sendall(header + payload)


def _ws_frame(sock: socket.socket) -> tuple[int, bool, bytes]:
    """One frame: (opcode, fin, payload). Raises OSError on anything odd."""
    hdr = _recvexact(sock, 2)
    opcode = hdr[0] & 0x0F
    fin = bool(hdr[0] & 0x80)
    length = hdr[1] & 0x7F
    try:
        if length == 126:
            length = struct.unpack("!H", _recvexact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", _recvexact(sock, 8))[0]
    except struct.error as exc:  # short/garbled length header
        raise OSError(f"devtools frame header: {exc}") from exc
    if length > _MAX_FRAME:
        raise OSError(f"devtools frame too large ({length} bytes)")
    if hdr[1] & 0x80:
        mask = _recvexact(sock, 4)
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(_recvexact(sock, length)))
    else:
        data = _recvexact(sock, length)
    return opcode, fin, data


def _ws_recv(sock: socket.socket) -> str:
    """One complete text message. Reassembles continuation frames."""
    opcode, fin, data = _ws_frame(sock)
    if opcode == 0x8:
        raise OSError("devtools closed")
    if opcode in (0x9, 0xA):
        return ""
    buf = bytearray(data)
    while not fin:
        # Control frames may interleave a fragmented message; skip them.
        cont_op, fin, chunk = _ws_frame(sock)
        if cont_op == 0x8:
            raise OSError("devtools closed")
        if cont_op in (0x9, 0xA):
            fin = False
            continue
        if len(buf) + len(chunk) > _MAX_FRAME:
            raise OSError("devtools message too large")
        buf.extend(chunk)
    try:
        return bytes(buf).decode() if buf else ""
    except UnicodeDecodeError as exc:
        raise OSError(f"devtools payload is not utf-8: {exc}") from exc


def _recvexact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise OSError("devtools socket closed")
        buf.extend(chunk)
    return bytes(buf)


def _call(
    sock: socket.socket,
    method: str,
    params: dict[str, Any],
    msg_id: int,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    msg: dict[str, Any] = {"id": msg_id, "method": method, "params": params}
    if session_id:
        msg["sessionId"] = session_id
    _ws_send(sock, json.dumps(msg))
    # The engine interleaves events with replies; bound the wait so a chatty
    # target cannot keep this call spinning past the socket timeout.
    deadline = time.monotonic() + _TIMEOUT
    while True:
        if time.monotonic() > deadline:
            raise TimeoutError(f"devtools {method} timed out")
        raw = _ws_recv(sock)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise OSError(f"devtools sent invalid json: {exc}") from exc
        if not isinstance(payload, dict):
            raise OSError("devtools sent a non-object message")
        if payload.get("id") == msg_id:
            if "error" in payload:
                raise OSError(str(payload["error"]))
            result = payload.get("result")
            return result if isinstance(result, dict) else {}


def chrome_inset(metrics: dict[str, Any]) -> tuple[float, float]:
    """Title-bar / tab strip height from Runtime.evaluate window metrics."""
    outer_h = float(metrics.get("outerHeight") or 0)
    inner_h = float(metrics.get("innerHeight") or 0)
    outer_w = float(metrics.get("outerWidth") or 0)
    inner_w = float(metrics.get("innerWidth") or 0)
    top = max(0.0, outer_h - inner_h)
    left = max(0.0, outer_w - inner_w)
    return top, left


def _target_id(page: dict[str, Any]) -> str:
    return str(page.get("targetId") or page.get("id") or "")


def click_on_engine(
    sock: socket.socket,
    *,
    global_x: float,
    global_y: float,
    window: Window,
    button: str = "left",
    call: Any = None,
    close: bool = True,
) -> bool:
    """Click through an already-open engine WebSocket. Does not handshake."""
    next_id = 1

    def _invoke(
        method: str,
        params: dict[str, Any],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        nonlocal next_id
        next_id += 1
        return _call(sock, method, params, next_id, session_id=session_id)

    invoke = call or _invoke
    session_id: str | None = None
    infos = invoke("Target.getTargets", {}).get("targetInfos") or []
    picked = pick_page(list(infos), window.title)
    if picked is None or not _target_id(picked):
        if close:
            sock.close()
        return False
    tid = _target_id(picked)
    with contextlib.suppress(OSError):
        invoke("Target.activateTarget", {"targetId": tid})
    attached = invoke("Target.attachToTarget", {"targetId": tid, "flatten": True})
    session_id = str(attached.get("sessionId") or "")
    if not session_id:
        if close:
            sock.close()
        return False
    try:
        metrics = invoke(
            "Runtime.evaluate",
            {
                "expression": "({outerHeight, innerHeight, outerWidth, innerWidth})",
                "returnByValue": True,
            },
            session_id=session_id,
        )
        value = metrics.get("result", {}).get("value") or {}
        top, left = chrome_inset(value if isinstance(value, dict) else {})
        vx, vy = viewport_from_global(
            global_x=global_x,
            global_y=global_y,
            window=window,
            chrome_top=top,
            chrome_left=left,
        )
        if vx < 0 or vy < 0:
            return False
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            params: dict[str, Any] = {
                "type": kind,
                "x": vx,
                "y": vy,
                "button": button,
                "clickCount": 1 if kind != "mouseMoved" else 0,
                "pointerType": "mouse",
            }
            if kind != "mouseMoved":
                params["buttons"] = 1 if button == "left" else 0
            invoke("Input.dispatchMouseEvent", params, session_id=session_id)
    finally:
        if close:
            sock.close()
    return True


def click_via_devtools(
    *,
    global_x: float,
    global_y: float,
    window: Window,
    button: str = "left",
    base: str | None = None,
) -> bool:
    from mangouse.devtools_hold import call as hold_call
    from mangouse.devtools_hold import ensure as ensure_hold
    from mangouse.devtools_hold import window_payload

    if base is None:
        ensure_hold()
        held = hold_call(
            {
                "op": "click",
                "global_x": global_x,
                "global_y": global_y,
                "button": button,
                "window": window_payload(window),
            }
        )
        if held is not None:
            return bool(held.get("ok"))

    url = base or configured_url()
    page = pick_page(fetch_targets(url), window.title) if url else None
    if page is not None and page.get("webSocketDebuggerUrl"):
        sock = _ws_connect(str(page["webSocketDebuggerUrl"]))
        tid = _target_id(page)
        if tid:
            with contextlib.suppress(OSError):
                _call(sock, "Target.activateTarget", {"targetId": tid}, 1)
        try:
            metrics = _call(
                sock,
                "Runtime.evaluate",
                {
                    "expression": "({outerHeight, innerHeight, outerWidth, innerWidth})",
                    "returnByValue": True,
                },
                10,
            )
            value = metrics.get("result", {}).get("value") or {}
            top, left = chrome_inset(value if isinstance(value, dict) else {})
            vx, vy = viewport_from_global(
                global_x=global_x,
                global_y=global_y,
                window=window,
                chrome_top=top,
                chrome_left=left,
            )
            if vx < 0 or vy < 0:
                return False
            for i, kind in enumerate(("mouseMoved", "mousePressed", "mouseReleased"), start=11):
                params: dict[str, Any] = {
                    "type": kind,
                    "x": vx,
                    "y": vy,
                    "button": button,
                    "clickCount": 1 if kind != "mouseMoved" else 0,
                    "pointerType": "mouse",
                }
                if kind != "mouseMoved":
                    params["buttons"] = 1 if button == "left" else 0
                _call(sock, "Input.dispatchMouseEvent", params, i)
        finally:
            sock.close()
        return True

    ws = browser_ws_url()
    if not ws:
        return False
    sock = _ws_connect(ws)
    return click_on_engine(
        sock,
        global_x=global_x,
        global_y=global_y,
        window=window,
        button=button,
        close=True,
    )
