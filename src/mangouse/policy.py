"""User-supplied targeting policy. The core ships an empty deny list."""

from __future__ import annotations

from collections.abc import Sequence

from mangouse.config import Config, load_config
from mangouse.models import Window


def deny_tokens(config: Config | None = None) -> tuple[str, ...]:
    return (config or load_config()).deny_app_ids


def is_confined(window: Window, config: Config | None = None) -> bool:
    """False if a confine list is set and the window is outside it."""
    cfg = config or load_config()
    if cfg.confine_app_ids:
        app = window.app_id.lower()
        if not any(t.lower() in app for t in cfg.confine_app_ids):
            return False
    groups_ok = not cfg.confine_groups or any(g in window.groups for g in cfg.confine_groups)
    return groups_ok


def assert_target(window: Window, config: Config | None = None) -> None:
    from mangouse.errors import Denied

    cfg = config or load_config()
    if is_denied(window, cfg.deny_app_ids):
        raise Denied(f"window {window.id} matches deny_app_ids")
    if not is_confined(window, cfg):
        raise Denied(f"window {window.id} is outside confine policy")


def is_denied(window: Window, tokens: Sequence[str] | None = None) -> bool:
    """True if app_id or title matches a user token (substring, case-insensitive)."""
    needles = tuple(t.lower() for t in (tokens if tokens is not None else deny_tokens()))
    if not needles:
        return False
    app = window.app_id.lower()
    short = app.rsplit(".", 1)[-1]
    title = window.title.lower()
    return any(token in app or token == short or token in title for token in needles)
