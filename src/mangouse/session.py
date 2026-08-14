"""Pick a backend. Core lists adapters; it does not special-case apps or hosts."""

from __future__ import annotations

import os

from mangouse.backend import Backend
from mangouse.backends.mango import MangoBackend
from mangouse.config import load_config
from mangouse.errors import NoSession

REGISTRY: dict[str, type] = {
    "mango": MangoBackend,
}


def resolve_backend(
    name: str | None = None,
    *,
    mango_runner=None,
) -> Backend:
    wanted = (name or os.environ.get("MANGOUSE_BACKEND") or load_config().backend or "auto").lower()
    if wanted != "auto":
        cls = REGISTRY.get(wanted)
        if cls is None:
            raise NoSession(f"unknown backend {wanted!r}; known: {', '.join(sorted(REGISTRY))}")
        backend = _make(cls, mango_runner)
        return backend

    for cls in REGISTRY.values():
        backend = _make(cls, mango_runner)
        if backend.available():
            return backend
    raise NoSession("no supported compositor session (tried: " + ", ".join(REGISTRY) + ")")


def _make(cls: type, mango_runner) -> Backend:
    if cls is MangoBackend and mango_runner is not None:
        return MangoBackend(runner=mango_runner)
    return cls()
