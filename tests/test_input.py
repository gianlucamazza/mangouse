from __future__ import annotations

from mangouse.config import Config, parse_config
from mangouse.errors import BadArg, BadKey, Denied, Readonly
from mangouse.input import click, dispatch, focus, press_key, type_text
from mangouse.models import Window
from mangouse.policy import assert_target


def _win(**kwargs) -> Window:
    base = dict(
        id=7,
        pid=1,
        app_id="foot",
        title="term",
        output="eDP-1",
        groups=[1],
        x=0,
        y=0,
        width=200,
        height=200,
        focused=True,
        visible=True,
    )
    base.update(kwargs)
    return Window(**base)


class FakeBackend:
    name = "fake"

    def __init__(self, window: Window | None = None) -> None:
        self.win = window or _win()
        self.calls: list[tuple] = []

    def window(self, window_id: int) -> Window:
        return self.win

    def focusing(self) -> Window | None:
        return self.win

    def windows(self) -> list[Window]:
        return [self.win]

    def focus_window(self, window_id: int) -> None:
        self.calls.append(("focus", window_id))

    def dispatch_action(self, spec: str) -> object:
        self.calls.append(("dispatch", spec))
        return {"success": True}


def test_type_requires_allow() -> None:
    try:
        type_text("hi", backend=FakeBackend())
    except Readonly:
        return
    raise AssertionError("expected Readonly")


def test_type_calls_wtype(seat_bins) -> None:
    seen: list[list[str]] = []
    type_text("hi", allow_input=True, backend=FakeBackend(), runner=seen.append)
    assert seen[0][-2:] == ["--", "hi"]


def test_key_refuses_super() -> None:
    try:
        press_key("super+q", allow_input=True, backend=FakeBackend())
    except BadKey as exc:
        assert exc.code == "bad_key"
        return
    raise AssertionError("expected BadKey")


def test_key_ctrl_c_builds_wtype_args(seat_bins) -> None:
    seen: list[list[str]] = []
    press_key("ctrl+c", allow_input=True, backend=FakeBackend(), runner=seen.append)
    assert "-M" in seen[0] and "ctrl" in seen[0]


def test_focus_records_backend() -> None:
    be = FakeBackend()
    out = focus(7, allow_input=True, backend=be)
    assert be.calls == [("focus", 7)]
    assert out["window_id"] == 7


def test_dispatch_passthrough() -> None:
    be = FakeBackend()
    dispatch("focusid client,7", allow_input=True, backend=be)
    assert be.calls == [("dispatch", "focusid client,7")]


def test_empty_dispatch_is_bad_arg() -> None:
    try:
        dispatch("  ", allow_input=True, backend=FakeBackend())
    except BadArg as exc:
        assert exc.code == "bad_arg"
        return
    raise AssertionError("expected BadArg")


def test_click_moves_then_clicks(seat_bins) -> None:
    seen: list[list[str]] = []
    out = click(10, 20, allow_input=True, backend=FakeBackend(), runner=seen.append)
    assert seen[0][1:3] == ["mousemove", "-a"]
    assert seen[1][1:] == ["click", "0xC0"]
    assert out["via"] == "ydotool"


def test_click_with_window_focuses_first(seat_bins) -> None:
    """type/key already focus --window; click did not, so a webview never saw the seat."""
    be = FakeBackend()
    seen: list[list[str]] = []
    out = click(10, 20, allow_input=True, window_id=7, backend=be, runner=seen.append)
    assert be.calls == [("focus", 7)]
    assert seen[0][1:3] == ["mousemove", "-a"]
    assert out["window_id"] == 7
    assert out["via"] == "ydotool"


def test_denied_window() -> None:
    win = _win(app_id="keepassxc")
    try:
        assert_target(win, Config(deny_app_ids=("keepassxc",)))
    except Denied:
        return
    raise AssertionError("expected Denied")


def test_confine_rejects_other_group() -> None:
    cfg = parse_config({"policy": {"confine_groups": [2]}})
    try:
        assert_target(_win(groups=[1]), cfg)
    except Denied:
        return
    raise AssertionError("expected Denied")


def test_click_falls_back_to_seat_when_devtools_misbehaves(monkeypatch, backend, seat_bins) -> None:
    """A malformed protocol reply must degrade to ydotool, not raise."""
    from mangouse import input as input_mod

    def boom(**kwargs):
        raise ValueError("devtools sent garbage")

    monkeypatch.setattr(input_mod, "click_via_devtools", boom)
    monkeypatch.setattr(input_mod, "require_input", lambda flag=False: None)

    ran: list[list[str]] = []

    def runner(cmd: list[str]) -> str:
        ran.append(cmd)
        return ""

    out = input_mod.click(
        100.0,
        200.0,
        allow_input=True,
        backend=backend,
        runner=runner,
    )
    assert out["via"] == "ydotool"
    assert any("mousemove" in c for c in ran)
