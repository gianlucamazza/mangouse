from __future__ import annotations

from mangouse.errors import Readonly
from mangouse.models import Window
from mangouse.policy import is_denied
from mangouse.safety import require_input


def _window(app_id: str) -> Window:
    return Window(
        id=1,
        pid=1,
        app_id=app_id,
        title="",
        output="out",
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


def test_allow_input_from_config(tmp_path, monkeypatch) -> None:
    cfg = tmp_path / "cfg.toml"
    cfg.write_text("allow_input = true\n")
    monkeypatch.setenv("MANGOUSE_CONFIG", str(cfg))
    require_input(False)


def test_deny_uses_caller_tokens_only() -> None:
    tokens = ("vault",)
    assert is_denied(_window("com.example.vault"), tokens=tokens)
    assert not is_denied(_window("term"), tokens=tokens)
