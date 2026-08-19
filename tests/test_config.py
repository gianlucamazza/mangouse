from __future__ import annotations

from mangouse.config import parse_config
from mangouse.session import resolve_backend


def test_empty_config() -> None:
    cfg = parse_config({})
    assert cfg.backend == "auto"
    assert cfg.deny_app_ids == ()
    assert cfg.allow_input is False
    assert cfg.allow_clipboard is False
    assert cfg.devtools_url == ""


def test_policy_from_toml_shape() -> None:
    cfg = parse_config(
        {
            "backend": "mango",
            "policy": {
                "deny_app_ids": ["keepassxc"],
                "confine_groups": [1],
                "confine_app_ids": ["foot"],
            },
        }
    )
    assert cfg.backend == "mango"
    assert cfg.deny_app_ids == ("keepassxc",)
    assert cfg.confine_groups == (1,)
    assert cfg.confine_app_ids == ("foot",)


def test_resolve_forced_mango(backend) -> None:
    got = resolve_backend("mango", runner=backend._runner)
    assert got.name == "mango"
    assert got.version().startswith("0.")


def test_scalar_string_is_one_token_not_characters() -> None:
    """`deny_app_ids = "vault"` must not become eight one-letter substrings.

    The same slip on `confine_app_ids` would silently disable confinement,
    and on `lock_procs` would break lock detection.
    """
    cfg = parse_config({"policy": {"deny_app_ids": "vault", "confine_app_ids": "foot"}})
    assert cfg.deny_app_ids == ("vault",)
    assert cfg.confine_app_ids == ("foot",)
    assert parse_config({"lock_procs": "swaylock"}).lock_procs == ("swaylock",)


def test_bad_config_shapes_raise_structured_errors() -> None:
    import pytest

    from mangouse.errors import BadConfig

    with pytest.raises(BadConfig):
        parse_config({"policy": {"confine_groups": ["nope"]}})
    with pytest.raises(BadConfig):
        parse_config({"policy": {"deny_app_ids": 7}})
    with pytest.raises(BadConfig):
        parse_config({"policy": {"confine_groups": "12"}})


def test_unreadable_config_is_a_structured_error(tmp_path) -> None:
    import pytest

    from mangouse.config import load_config
    from mangouse.errors import BadConfig

    broken = tmp_path / "config.toml"
    broken.write_text("backend = [[[\n")
    with pytest.raises(BadConfig):
        load_config(broken)


def test_deny_policy_survives_a_scalar_deny_list() -> None:
    """Regression: char-exploded tokens matched nearly every window."""
    from mangouse.models import Window
    from mangouse.policy import is_denied

    cfg = parse_config({"policy": {"deny_app_ids": "vault"}})
    window = Window(
        id=1,
        pid=1,
        app_id="org.example.Terminal",
        title="build log",
        output="DP-1",
        groups=[1],
        x=0,
        y=0,
        width=100,
        height=100,
        focused=True,
        visible=True,
    )
    assert is_denied(window, cfg.deny_app_ids) is False
