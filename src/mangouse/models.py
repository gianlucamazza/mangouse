"""Compositor-agnostic snapshots. Backends map their IPC into these types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return obj


@dataclass(frozen=True)
class Group:
    """Workspace, tag, or any backend grouping on an output."""

    index: int
    active: bool
    urgent: bool = False
    label: str = ""
    window_count: int = 0


@dataclass(frozen=True)
class Window:
    id: int
    pid: int
    app_id: str
    title: str
    output: str
    groups: list[int]
    x: int
    y: int
    width: int
    height: int
    focused: bool
    visible: bool
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Output:
    name: str
    x: int
    y: int
    width: int
    height: int
    scale: float
    active: bool
    groups: list[Group] = field(default_factory=list)
    active_groups: list[int] = field(default_factory=list)
    focused_window_id: int | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Cursor:
    x: float
    y: float
    output: str | None


@dataclass(frozen=True)
class Desktop:
    backend: str
    version: str
    outputs: list[Output]
    windows: list[Window]
    focused: Window | None
    cursor: Cursor | None


@dataclass(frozen=True)
class Check:
    id: str
    ok: bool
    detail: str = ""
    blocker: bool = False


@dataclass(frozen=True)
class Shot:
    path: str
    x: int
    y: int
    width: int
    height: int
    scale: float
    output: str | None
    window_id: int | None = None
