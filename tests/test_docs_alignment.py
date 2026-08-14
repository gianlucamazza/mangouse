"""Fail if docs/skill drift from the shipped contract."""

from __future__ import annotations

import re
from pathlib import Path

from mangouse import __version__
from mangouse.hosts.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# Phrases that were true in scaffold v0 and must not reappear.
STALE = (
    "input_implemented` is `false`",
    "Stubs in v0",
    "Mutate stubs stay CLI-only",
    "Even with the flag: `not_implemented`",
    "Input is not live in v0",
)


def test_version_in_changelog_and_readme() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text()
    readme = (ROOT / "README.md").read_text()
    assert f"## [{__version__}]" in changelog
    assert f"**{__version__}**" in readme


def test_docs_have_no_v0_stub_claims() -> None:
    blob = "\n".join(p.read_text() for p in DOCS.rglob("*.md"))
    blob += (ROOT / "README.md").read_text()
    for phrase in STALE:
        assert phrase not in blob, f"stale phrase still in docs: {phrase!r}"


def test_cli_actions_are_documented() -> None:
    parser = build_parser()
    cmds = set()
    for action in parser._actions:
        if action.dest == "cmd" and action.choices:
            cmds = set(action.choices)
            break
    headless = (DOCS / "headless.md").read_text()
    for name in cmds:
        assert f"`{name}`" in headless, f"{name} missing from docs/headless.md"
    assert cmds == {
        "doctor",
        "desktop",
        "shot",
        "zoom",
        "focus",
        "type",
        "key",
        "click",
        "dispatch",
    }


def test_example_config_keys_parse() -> None:
    import tomllib

    from mangouse.config import parse_config

    data = tomllib.loads((ROOT / "examples" / "config.toml").read_text())
    cfg = parse_config(data)
    assert cfg.allow_input is False
    assert cfg.backend == "auto"
    assert cfg.deny_app_ids == ()
    assert cfg.confine_groups == ()
    assert cfg.confine_app_ids == ()
    # no leftover 0.1.x keys
    assert "allow-inout" not in (ROOT / "examples" / "config.toml").read_text()


def test_skill_mentions_config_grant() -> None:
    skill = (ROOT / "skills" / "mangouse" / "SKILL.md").read_text()
    assert "allow_input" in skill
    assert re.search(r"--json doctor", skill)
    assert "super+" in skill.lower() or "Super" in skill
