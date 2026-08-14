from __future__ import annotations

from mangouse.errors import Readonly
from mangouse.hosts.cli import main
from mangouse.models import Window
from mangouse.policy import is_denied
from mangouse.safety import require_input


def _window(app_id: str, title: str = "") -> Window:
    return Window(
        id=1,
        pid=1,
        app_id=app_id,
        title=title,
        output="eDP-1",
        groups=[1],
        x=0,
        y=0,
        width=100,
        height=100,
        focused=False,
        visible=True,
    )


def test_require_input_default() -> None:
    try:
        require_input(False)
    except Readonly as exc:
        assert exc.code == "readonly"
    else:
        raise AssertionError("expected Readonly")


def test_require_input_flag() -> None:
    require_input(True)


def test_allow_input_from_config(tmp_path, monkeypatch) -> None:
    cfg = tmp_path / "cfg.toml"
    cfg.write_text("allow_input = true\n")
    monkeypatch.setenv("MANGOUSE_CONFIG", str(cfg))
    require_input(False)


def test_deny_list_is_empty_by_default() -> None:
    assert not is_denied(_window("1Password"), tokens=())
    assert not is_denied(_window("foot"), tokens=())


def test_deny_uses_caller_tokens_only() -> None:
    tokens = ("onepassword", "keepassxc")
    assert is_denied(_window("com.onepassword.OnePassword"), tokens=tokens)
    assert not is_denied(_window("foot"), tokens=tokens)


def test_cli_type_readonly() -> None:
    rc = main(["--json", "type", "hello"])
    assert rc == 2


