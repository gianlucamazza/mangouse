"""Optional stdio MCP server (extra `mangouse[mcp]`). Observe-only."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from mangouse.contract import envelope
from mangouse.errors import MangouseError


def observe_call(action: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Run an observe tool and keep the JSON envelope on core errors.

    CLI already does this in ``main``. Without it, a missing compositor or
    ``grim`` becomes an SDK tool-error instead of ``schema: 1``.
    """
    try:
        return fn()
    except MangouseError as exc:
        return envelope(ok=False, action=action, error=exc.code, message=exc.message)


def main() -> int:
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.types import ToolAnnotations
    except ImportError:
        sys.stderr.write("mangouse-mcp needs the optional extra: pip/uv install 'mangouse[mcp]'\n")
        return 2

    from mangouse.doctor import run_doctor
    from mangouse.models import to_dict
    from mangouse.screen import capture
    from mangouse.screen import zoom as take_zoom
    from mangouse.session import resolve_backend

    server = MCPServer("mangouse")
    readonly = ToolAnnotations(read_only_hint=True)

    @server.tool(annotations=readonly)
    def doctor() -> dict:
        """Session and dependency readiness. Read-only."""
        return observe_call(
            "doctor",
            lambda: envelope(ok=True, action="doctor", data=run_doctor()),
        )

    @server.tool(annotations=readonly)
    def desktop() -> dict:
        """Semantic snapshot: outputs, windows, focus, cursor. Read-only."""
        return observe_call(
            "desktop",
            lambda: envelope(
                ok=True,
                action="desktop",
                data={"desktop": to_dict(resolve_backend().desktop())},
            ),
        )

    @server.tool(annotations=readonly)
    def shot(output: str | None = None, window: int | None = None, full: bool = False) -> dict:
        """Capture the focused output, a named output, or a window id. Read-only."""
        return observe_call(
            "shot",
            lambda: envelope(
                ok=True,
                action="shot",
                data={
                    "shot": to_dict(
                        capture(resolve_backend(), output=output, window_id=window, full=full)
                    )
                },
            ),
        )

    @server.tool(annotations=readonly)
    def zoom(x: float, y: float, size: int = 400) -> dict:
        """Native-resolution crop around a global point. Read-only."""
        return observe_call(
            "zoom",
            lambda: envelope(
                ok=True,
                action="zoom",
                data={"shot": to_dict(take_zoom(resolve_backend(), x, y, size=size))},
            ),
        )

    @server.tool(annotations=readonly)
    def target() -> dict:
        """Who receives keys vs who is under the pointer. Read-only."""
        from mangouse.screen import target_snapshot

        return observe_call(
            "target",
            lambda: envelope(ok=True, action="target", data=target_snapshot(resolve_backend())),
        )

    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
