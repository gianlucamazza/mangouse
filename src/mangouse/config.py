"""Optional user config. Nothing app- or host-specific is shipped."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mangouse.errors import BadConfig

# Override via config `lock_procs`. Names are lock clients, not apps.
DEFAULT_LOCK_PROCS: tuple[str, ...] = (
    "swaylock",
    "gtklock",
    "waylock",
    "hyprlock",
)


@dataclass(frozen=True)
class Config:
    backend: str = "auto"
    allow_input: bool = False
    allow_clipboard: bool = False
    devtools_url: str = ""
    deny_app_ids: tuple[str, ...] = ()
    confine_groups: tuple[int, ...] = ()
    confine_app_ids: tuple[str, ...] = ()
    lock_procs: tuple[str, ...] = DEFAULT_LOCK_PROCS


def config_path() -> Path:
    override = os.environ.get("MANGOUSE_CONFIG")
    if override:
        return Path(override)
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "mangouse" / "config.toml"


def load_config(path: Path | None = None) -> Config:
    target = path or config_path()
    if not target.is_file():
        return Config()
    import tomllib

    try:
        data = tomllib.loads(target.read_text())
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as exc:
        raise BadConfig(f"{target}: {exc}") from exc
    return parse_config(data)


def _str_tuple(value: Any, key: str) -> tuple[str, ...]:
    """A bare string is one token, never a sequence of characters.

    `deny_app_ids = "vault"` is the natural mistake; iterating it would turn
    the policy into eight single-letter substrings that match nearly every
    window, and the same slip silently disables `confine_*` and `lock_procs`.
    """
    if isinstance(value, str):
        return (value,) if value else ()
    if not isinstance(value, (list, tuple)):
        raise BadConfig(f"{key} must be a list of strings, got {type(value).__name__}")
    return tuple(str(x) for x in value)


def _int_tuple(value: Any, key: str) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise BadConfig(f"{key} must be a list of integers, got {type(value).__name__}")
    out: list[int] = []
    for item in value:
        try:
            out.append(int(item))
        except (TypeError, ValueError) as exc:
            raise BadConfig(f"{key} holds a non-integer: {item!r}") from exc
    return tuple(out)


def parse_config(data: dict[str, Any]) -> Config:
    if not isinstance(data, dict):
        raise BadConfig("config root must be a table")
    policy = data.get("policy") or {}
    deny = policy.get("deny_app_ids") or data.get("deny_app_ids") or []
    backend = str(data.get("backend") or "auto")
    confine = policy.get("confine_groups") or []
    confine_apps = policy.get("confine_app_ids") or []
    allow = data.get("allow_input", policy.get("allow_input", False))
    clip = data.get("allow_clipboard", policy.get("allow_clipboard", False))
    devtools = str(data.get("devtools_url") or policy.get("devtools_url") or "")
    locks = data.get("lock_procs", policy.get("lock_procs"))
    return Config(
        backend=backend,
        allow_input=bool(allow),
        allow_clipboard=bool(clip),
        devtools_url=devtools.strip(),
        deny_app_ids=_str_tuple(deny, "deny_app_ids"),
        confine_groups=_int_tuple(confine, "confine_groups"),
        confine_app_ids=_str_tuple(confine_apps, "confine_app_ids"),
        lock_procs=_str_tuple(locks, "lock_procs") if locks is not None else DEFAULT_LOCK_PROCS,
    )
