"""Optional user config. Nothing app- or host-specific is shipped."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

    data = tomllib.loads(target.read_text())
    return parse_config(data)


def parse_config(data: dict[str, Any]) -> Config:
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
        deny_app_ids=tuple(str(x) for x in deny),
        confine_groups=tuple(int(x) for x in confine),
        confine_app_ids=tuple(str(x) for x in confine_apps),
        lock_procs=tuple(str(x) for x in locks) if locks is not None else DEFAULT_LOCK_PROCS,
    )
