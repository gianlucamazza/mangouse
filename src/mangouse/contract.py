"""Shared --json envelope. Hosts must not invent fields."""

from __future__ import annotations

from typing import Any

SCHEMA = 1
DEFAULT_FIT = 1568


def envelope(
    *,
    ok: bool,
    action: str,
    data: dict[str, Any] | None = None,
    error: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": ok, "schema": SCHEMA, "action": action}
    if data:
        out.update(data)
    if error:
        out["error"] = error
    if message:
        out["message"] = message
    return out
