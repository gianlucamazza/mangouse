"""CLI surface and version stay documented."""

from __future__ import annotations

from pathlib import Path

from mangouse import __version__
from mangouse.config import parse_config
from mangouse.hosts.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]


def test_version_in_changelog_and_readme() -> None:
    assert f"## [{__version__}]" in (ROOT / "CHANGELOG.md").read_text()
    assert f"**{__version__}**" in (ROOT / "README.md").read_text()


def test_cli_actions_are_documented() -> None:
    parser = build_parser()
    cmds = set()
    for action in parser._actions:
        if action.dest == "cmd" and action.choices:
            cmds = set(action.choices)
            break
    headless = (ROOT / "docs" / "headless.md").read_text()
    for name in cmds:
        assert f"`{name}`" in headless, f"{name} missing from docs/headless.md"


def test_example_config_keys_parse() -> None:
    import tomllib

    data = tomllib.loads((ROOT / "examples" / "config.toml").read_text())
    cfg = parse_config(data)
    assert cfg.allow_input is False
    assert cfg.backend == "auto"
