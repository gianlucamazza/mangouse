"""Readiness: generic seat checks + whatever the active backend reports."""

from __future__ import annotations

import os
import shutil

from mangouse.backend import Backend
from mangouse.errors import MangouseError, NoSession
from mangouse.input import ydotool_socket_path
from mangouse.models import Check
from mangouse.session import resolve_backend


def _which(name: str) -> str | None:
    return shutil.which(name)


def run_doctor(backend: Backend | None = None, name: str | None = None) -> dict:
    checks: list[Check] = []

    wayland = os.environ.get("WAYLAND_DISPLAY", "")
    checks.append(
        Check(
            id="wayland",
            ok=bool(wayland),
            detail=wayland or "WAYLAND_DISPLAY unset",
            blocker=True,
        )
    )

    grim = _which("grim")
    wtype = _which("wtype")
    ydotool = _which("ydotool")
    wlpaste = _which("wl-paste")
    bins = {"grim": grim, "wtype": wtype, "ydotool": ydotool, "wl-paste": wlpaste}
    # grim is required for shot/zoom, not for desktop/target. A missing
    # binary must not claim the compositor session is unobservable.
    checks.append(
        Check(id="bin_grim", ok=bool(grim), detail=grim or "grim not on PATH", blocker=False)
    )
    checks.append(
        Check(id="bin_wtype", ok=bool(wtype), detail=wtype or "wtype not on PATH", blocker=False)
    )
    checks.append(
        Check(
            id="bin_ydotool",
            ok=bool(ydotool),
            detail=ydotool or "ydotool not on PATH",
            blocker=False,
        )
    )

    ydo = ydotool_socket_path()
    checks.append(
        Check(
            id="ydotool_socket",
            ok=ydo.exists(),
            detail=str(ydo) if ydo.exists() else f"{ydo} missing",
            blocker=False,
        )
    )
    checks.append(
        Check(
            id="bin_wl_paste",
            ok=bool(wlpaste),
            detail=wlpaste or "wl-paste not on PATH (clipboard)",
            blocker=False,
        )
    )
    from mangouse.devtools import probe as devtools_probe

    dt = devtools_probe()
    state = str(dt.get("state") or "unset")
    detail = "unset" if state == "unset" else f"{state} via={dt.get('via')} pages={dt.get('pages')}"
    checks.append(
        Check(
            id="devtools",
            ok=state == "connected",
            detail=detail,
            blocker=False,
        )
    )

    version = ""
    backend_name = ""
    try:
        active = backend or resolve_backend(name)
        backend_name = active.name
        checks.append(Check(id="backend", ok=True, detail=active.name, blocker=True))
        checks.extend(active.checks())
        version = active.version()
    except (NoSession, MangouseError) as exc:
        checks.append(Check(id="backend", ok=False, detail=exc.message, blocker=True))

    blockers = [c.id for c in checks if c.blocker and not c.ok]
    observe_ready = not blockers
    return {
        "ready": observe_ready,
        "observe_ready": observe_ready,
        "shot_ready": observe_ready and bool(grim),
        "input_ready": observe_ready and bool(wtype),
        "click_ready": observe_ready and bool(ydotool) and ydo.exists(),
        "input_implemented": True,
        "backend": backend_name,
        "version": version,
        "session": {
            "wayland": wayland,
            "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        },
        "bins": bins,
        "checks": [c.__dict__ for c in checks],
        "blockers": blockers,
    }
