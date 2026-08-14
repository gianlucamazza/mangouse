from __future__ import annotations

import json
from pathlib import Path

from mangouse.backends.mango import parse_output, parse_window

FIX = Path(__file__).resolve().parents[1] / "testdata" / "mango"


def test_parse_windows_from_recorded_mango_fixture() -> None:
    data = json.loads((FIX / "all-clients.json").read_text())
    windows = [parse_window(c) for c in data["clients"]]
    assert windows
    assert all(w.id > 0 for w in windows)
    assert any(w.app_id == "foot" for w in windows)
    assert all(w.output for w in windows)


def test_parse_outputs_from_recorded_mango_fixture() -> None:
    data = json.loads((FIX / "all-monitors.json").read_text())
    outputs = [parse_output(m) for m in data["monitors"]]
    assert len(outputs) == 1
    assert outputs[0].name == "eDP-1"
    assert outputs[0].width == 1920
    assert outputs[0].groups
    assert outputs[0].focused_window_id is not None
