from __future__ import annotations

import pytest

from mangouse.contract import envelope
from mangouse.errors import NoSession
from mangouse.hosts.mcp import observe_call


def test_observe_call_wraps_mangouse_error() -> None:
    def boom() -> dict:
        raise NoSession("gone")

    payload = observe_call("desktop", boom)
    assert payload["ok"] is False
    assert payload["schema"] == 1
    assert payload["error"] == "no_session"
    assert payload["action"] == "desktop"
    assert "gone" in payload["message"]


def test_observe_call_passes_success() -> None:
    payload = observe_call(
        "doctor",
        lambda: envelope(ok=True, action="doctor", data={"ready": True}),
    )
    assert payload["ok"] is True
    assert payload["ready"] is True
    assert "error" not in payload


def test_mcp_extra_imports_server() -> None:
    """CI installs the extra; a local `uv sync --group dev` may not."""
    pytest.importorskip("mcp")
    from mcp.server.mcpserver import MCPServer

    assert MCPServer is not None
