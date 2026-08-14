"""Screenshot via grim. Geometry comes from the active backend, not an app."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from mangouse.backend import Backend
from mangouse.contract import DEFAULT_FIT
from mangouse.errors import GrimFailed, MissingDep, UnknownWindow
from mangouse.models import Shot


def runtime_dir() -> Path:
    base = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    out = base / "mangouse"
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    return out


def grim_geometry(x: int, y: int, w: int, h: int) -> str:
    return f"{x},{y} {w}x{h}"


def fit_scale(width: int, height: int, long_edge: int) -> tuple[float, int, int]:
    """Return (factor, new_w, new_h). factor is 1.0 when no shrink is needed."""
    if long_edge <= 0 or width <= 0 or height <= 0:
        return 1.0, width, height
    current = max(width, height)
    if current <= long_edge:
        return 1.0, width, height
    factor = long_edge / current
    return factor, max(1, round(width * factor)), max(1, round(height * factor))


def apply_fit(
    path: Path, width: int, height: int, scale: float, long_edge: int
) -> tuple[float, int, int]:
    factor, new_w, new_h = fit_scale(width, height, long_edge)
    if factor == 1.0:
        return scale, width, height
    magick = shutil.which("magick")
    if not magick:
        return scale, width, height
    proc = subprocess.run(
        [magick, str(path), "-resize", f"{long_edge}x{long_edge}>", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return scale, width, height
    return scale * factor, new_w, new_h


def capture(
    backend: Backend,
    *,
    output: str | None = None,
    window_id: int | None = None,
    full: bool = False,
    lossless: bool = False,
    fit: int = DEFAULT_FIT,
    region: tuple[int, int, int, int] | None = None,
) -> Shot:
    grim = shutil.which("grim")
    if not grim:
        raise MissingDep("grim")

    out_name: str | None = None
    wid: int | None = None
    x = y = 0
    width = height = 0
    scale = 1.0
    args: list[str] = []
    outputs = backend.outputs()

    if region is not None:
        x, y, width, height = region
        args += ["-g", grim_geometry(x, y, width, height)]
        focused = next((item for item in outputs if item.active), outputs[0] if outputs else None)
        if focused:
            out_name = focused.name
            scale = focused.scale
    elif window_id is not None:
        window = backend.window(window_id)
        wid = window.id
        out_name = window.output
        x, y, width, height = window.x, window.y, window.width, window.height
        args += ["-g", grim_geometry(x, y, width, height)]
        for item in outputs:
            if item.name == window.output:
                scale = item.scale
                break
    elif output:
        found = {item.name: item for item in outputs}
        if output not in found:
            raise GrimFailed(f"unknown output {output}")
        item = found[output]
        out_name = item.name
        x, y, width, height = item.x, item.y, item.width, item.height
        scale = item.scale
        args += ["-o", item.name]
    else:
        focused = next((item for item in outputs if item.active), outputs[0] if outputs else None)
        if focused is None:
            raise GrimFailed("no outputs")
        if full and len(outputs) > 1:
            min_x = min(item.x for item in outputs)
            min_y = min(item.y for item in outputs)
            max_x = max(item.x + item.width for item in outputs)
            max_y = max(item.y + item.height for item in outputs)
            x, y = min_x, min_y
            width, height = max_x - min_x, max_y - min_y
        else:
            out_name = focused.name
            x, y, width, height = focused.x, focused.y, focused.width, focused.height
            scale = focused.scale
            args += ["-o", focused.name]

    ext = "png" if lossless else "jpg"
    dest = runtime_dir() / f"shot-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.{ext}"
    cmd = [grim]
    if lossless:
        cmd += ["-t", "png"]
    else:
        cmd += ["-t", "jpeg", "-q", "90"]
    cmd += [*args, str(dest)]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired as exc:
        raise GrimFailed("grim timed out") from exc
    if proc.returncode != 0 or not dest.exists():
        raise GrimFailed((proc.stderr or proc.stdout or "grim failed").strip())
    if window_id is not None and (width <= 0 or height <= 0):
        raise UnknownWindow(window_id)
    scale, width, height = apply_fit(dest, width, height, scale, fit)
    return Shot(
        path=str(dest),
        x=x,
        y=y,
        width=width,
        height=height,
        scale=scale,
        output=out_name,
        window_id=wid,
    )


def zoom(
    backend: Backend,
    x: float,
    y: float,
    *,
    size: int = 400,
    lossless: bool = False,
    fit: int = DEFAULT_FIT,
) -> Shot:
    half = max(8, size // 2)
    rx, ry = int(x) - half, int(y) - half
    outputs = backend.outputs()
    box = outputs[0] if outputs else None
    for item in outputs:
        if item.x <= x < item.x + item.width and item.y <= y < item.y + item.height:
            box = item
            break
    if box is not None:
        rx = max(box.x, min(rx, box.x + box.width - 1))
        ry = max(box.y, min(ry, box.y + box.height - 1))
        width = min(size, box.x + box.width - rx)
        height = min(size, box.y + box.height - ry)
    else:
        width = height = size
    box = (rx, ry, max(1, width), max(1, height))
    return capture(backend, region=box, lossless=lossless, fit=fit)
