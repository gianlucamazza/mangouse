"""Shipped layout: hosts stay off compositor IPC; no product names in core."""

from __future__ import annotations

import json
from pathlib import Path

from mangouse.hosts.cli import main

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "mangouse"
HOSTS = SRC / "hosts"

_BANNED = (
    "mmsg",
    "hyprctl",
    "foot",
    "keepass",
    "1password",
    "onepassword",
    "chromium",
    "firefox",
    "claude",
    "codex",
    "eDP",
    "gianluca",
    "hyprland",
    "kitty",
    "alacritty",
    "polkit",
)


def test_install_sh_uses_uv_tool_and_skips_mcp() -> None:
    script = (ROOT / "install.sh").read_text()
    assert "uv tool install --force --reinstall" in script
    assert "grok mcp add" not in script


def test_console_scripts_point_at_hosts() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert 'mangouse = "mangouse.hosts.cli:main"' in text
    assert 'mangouse-mcp = "mangouse.hosts.mcp:main"' in text


def test_shipped_core_has_no_app_or_host_names() -> None:
    for path in [*SRC.glob("*.py"), *HOSTS.glob("*.py")]:
        body = path.read_text().lower()
        for token in _BANNED:
            assert token.lower() not in body, f"{path.name} contains {token!r}"


def test_shipped_cli_entry_readonly_envelope(capsys) -> None:
    rc = main(["--json", "type", "hello"])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == 1
    assert payload["error"] == "readonly"
