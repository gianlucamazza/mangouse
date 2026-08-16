"""Optional stdio MCP server (extra `mangouse[mcp]`). Observe-only."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.types import ToolAnnotations
    except ImportError:
        sys.stderr.write("mangouse-mcp needs the optional extra: pip/uv install 'mangouse[mcp]'\n")
        return 2

    from mangouse.contract import envelope
    from mangouse.doctor import run_doctor
    from mangouse.models import to_dict
    from mangouse.screen import capture
    from mangouse.session import resolve_backend

    server = MCPServer("mangouse")
    readonly = ToolAnnotations(readOnlyHint=True)

    @server.tool(annotations=readonly)
    def doctor() -> dict:
        """Session and dependency readiness. Read-only."""
        return envelope(ok=True, action="doctor", data=run_doctor())

    @server.tool(annotations=readonly)
    def desktop() -> dict:
        """Semantic snapshot: outputs, windows, focus, cursor. Read-only."""
        return envelope(
            ok=True,
            action="desktop",
            data={"desktop": to_dict(resolve_backend().desktop())},
        )

    @server.tool(annotations=readonly)
    def shot(output: str | None = None, window: int | None = None, full: bool = False) -> dict:
        """Capture the focused output, a named output, or a window id. Read-only."""
        result = capture(resolve_backend(), output=output, window_id=window, full=full)
        return envelope(ok=True, action="shot", data={"shot": to_dict(result)})

    @server.tool(annotations=readonly)
    def target() -> dict:
        """Who receives keys vs who is under the pointer. Read-only."""
        from mangouse.screen import target_snapshot

        return envelope(ok=True, action="target", data=target_snapshot(resolve_backend()))

    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
