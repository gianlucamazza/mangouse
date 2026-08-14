from __future__ import annotations

from mangouse.config import parse_config
from mangouse.session import REGISTRY, resolve_backend


def test_empty_config() -> None:
    cfg = parse_config({})
    assert cfg.backend == "auto"
    assert cfg.deny_app_ids == ()
    assert cfg.allow_input is False


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


def test_registry_has_mango_only() -> None:
    assert set(REGISTRY) == {"mango"}


def test_resolve_forced_mango(backend) -> None:
    got = resolve_backend("mango", mango_runner=backend._runner)
    assert got.name == "mango"
    assert got.version().startswith("0.")
