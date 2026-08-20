"""Read-only clipboard. Opt-in: secrets often live here.

Not a seat mutate. Separate grant from ``allow_input``. Never writes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable

from mangouse.config import load_config
from mangouse.errors import Denied, MissingDep

MAX_BYTES = 65536


def clipboard_allowed(*, flag: bool = False) -> bool:
    if flag:
        return True
    if os.environ.get("MANGOUSE_ALLOW_CLIPBOARD", "").strip() in {"1", "true", "yes"}:
        return True
    return bool(load_config().allow_clipboard)


def read_clipboard(
    *,
    allow: bool = False,
    runner: Callable[[list[str]], bytes | str] | None = None,
) -> dict[str, object]:
    if not clipboard_allowed(flag=allow):
        raise Denied("clipboard disabled (set allow_clipboard or --allow-clipboard)")
    exe = shutil.which("wl-paste")
    if not exe:
        raise MissingDep("wl-paste")
    cmd = [exe, "-n", "-t", "text"]
    if runner:
        raw = runner(cmd)
    else:
        try:
            proc = subprocess.run(cmd, check=False, capture_output=True, timeout=3)
        except subprocess.TimeoutExpired as exc:
            raise MissingDep("wl-paste") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or b"failed").decode("utf-8", "replace")
            raise MissingDep(f"wl-paste: {detail.strip()}")
        raw = proc.stdout
    data = raw.encode() if isinstance(raw, str) else bytes(raw)
    clipped = data[:MAX_BYTES]
    text = clipped.decode("utf-8", errors="replace")
    return {"text": text, "bytes": len(clipped), "mime": "text/plain"}
