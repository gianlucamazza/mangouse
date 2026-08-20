"""Pick a backend. Core lists adapters; it does not special-case apps or hosts."""

from __future__ import annotations

import os

from mangouse.backend import Backend, BackendType, Runner
from mangouse.backends.mango import MangoBackend
from mangouse.config import load_config
from mangouse.errors import NoSession

REGISTRY: dict[str, BackendType] = {
    "mango": MangoBackend,
}


def resolve_backend(
    name: str | None = None,
    *,
    runner: Runner | None = None,
) -> Backend:
    wanted = (name or os.environ.get("MANGOUSE_BACKEND") or load_config().backend or "auto").lower()
    if wanted != "auto":
        cls = REGISTRY.get(wanted)
        if cls is None:
            raise NoSession(f"unknown backend {wanted!r}; known: {', '.join(sorted(REGISTRY))}")
        return _make(cls, runner)

    for cls in REGISTRY.values():
        backend = _make(cls, runner)
        if backend.available():
            return backend
    raise NoSession("no supported compositor session (tried: " + ", ".join(REGISTRY) + ")")


def _make(cls: BackendType, runner: Runner | None) -> Backend:
    if runner is not None:
        return cls(runner=runner)
    return cls()
