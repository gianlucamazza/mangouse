from __future__ import annotations

from mangouse.backends.mango import MangoBackend
from mangouse.screen import grim_geometry


def test_desktop_snapshot(backend: MangoBackend) -> None:
    desktop = backend.desktop()
    assert desktop.backend == "mango"
    assert desktop.version.startswith("0.")
    assert desktop.outputs[0].name == "eDP-1"
    assert desktop.focused is not None
    assert desktop.focused.app_id == "foot"
    assert desktop.cursor is not None
    assert desktop.cursor.output == "eDP-1"
    assert desktop.cursor.x == 264.33206182414278
    assert desktop.cursor.y == 973.31438149406165
    assert {w.id for w in desktop.windows}


def test_window_lookup(backend: MangoBackend) -> None:
    first = backend.windows()[0]
    got = backend.window(first.id)
    assert got.id == first.id
    assert got.app_id == first.app_id


def test_grim_geometry() -> None:
    assert grim_geometry(10, 40, 1053, 1150) == "10,40 1053x1150"
