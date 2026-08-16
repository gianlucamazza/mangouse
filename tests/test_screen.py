from __future__ import annotations

from mangouse.models import Output, Window
from mangouse.screen import (
    classify_hit,
    output_containing,
    then_capture_kwargs,
    window_at,
)


def _out(
    name: str, x: int, y: int, w: int = 1920, h: int = 1200, *, active: bool = False
) -> Output:
    return Output(name=name, x=x, y=y, width=w, height=h, scale=1.0, active=active)


def _win(wid: int, x: int, y: int, *, focused: bool = False, visible: bool = True) -> Window:
    return Window(
        id=wid,
        pid=1,
        app_id="app",
        title="t",
        output="DP-2",
        groups=[1],
        x=x,
        y=y,
        width=400,
        height=400,
        focused=focused,
        visible=visible,
    )


def test_output_containing_ignores_active() -> None:
    dp = _out("DP-2", 0, 0, 2560, 1440, active=False)
    edp = _out("eDP-1", 2560, 0, 1920, 1200, active=True)
    found = output_containing([dp, edp], 1204, 140)
    assert found is not None
    assert found.name == "DP-2"


def test_then_shot_prefers_window_then_output_under_point() -> None:
    outputs = [_out("DP-2", 0, 0, 2560, 1440), _out("eDP-1", 2560, 0, active=True)]
    assert then_capture_kwargs(window_id=81, at=(1204, 140), outputs=outputs) == {"window_id": 81}
    assert then_capture_kwargs(window_id=None, at=(1204, 140), outputs=outputs) == {
        "output": "DP-2"
    }
    assert then_capture_kwargs(window_id=None, at=None, outputs=outputs) == {}


def test_window_at_prefers_focused() -> None:
    lower = _win(1, 0, 0, focused=False)
    upper = _win(2, 0, 0, focused=True)
    assert window_at([lower, upper], 10, 10).id == 2


def test_classify_hit() -> None:
    assert classify_hit("aa", "bb") == "changed"
    assert classify_hit("aa", "aa") == "unchanged"
    assert classify_hit(None, "aa") == "unknown"
    assert classify_hit("aa", None) == "unknown"
