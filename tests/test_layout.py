"""Shipped layout: hosts never call compositor CLIs; ipc shim is gone."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from mangouse.hosts.cli import main

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "mangouse"
HOSTS = SRC / "hosts"


def test_ipc_shim_removed() -> None:
    assert not (SRC / "ipc.py").exists()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("mangouse.ipc")


def test_install_sh_uses_uv_tool_and_skips_mcp() -> None:
    script = (ROOT / "install.sh").read_text()
    assert "uv tool install --force --reinstall" in script
    assert "${REPO}[mcp]" in script or "[mcp]" in script
    assert "mangouse --json doctor" in script
    assert "grok mcp add" not in script
    assert "Does not register MCP" in script


def test_console_scripts_point_at_hosts() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert 'mangouse = "mangouse.hosts.cli:main"' in text
    assert 'mangouse-mcp = "mangouse.hosts.mcp:main"' in text


def test_mcp_host_uses_sdk_v2() -> None:
    body = (HOSTS / "mcp.py").read_text()
    assert "MCPServer" in body
    assert "FastMCP" not in body


def test_hosts_do_not_name_compositor_clis() -> None:
    for path in (HOSTS / "cli.py", HOSTS / "mcp.py"):
        body = path.read_text()
        assert "mmsg" not in body
        assert "hyprctl" not in body


# Product/app/host tokens that must not appear in shipped core/hosts.
_BANNED = (
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
    "hyprctl",
    "hyprland",
    "kitty",
    "alacritty",
    "polkit",
)


def test_core_modules_do_not_invoke_compositor_clis() -> None:
    for path in SRC.glob("*.py"):
        body = path.read_text()
        assert "mmsg" not in body, path.name
        assert "hyprctl" not in body, path.name


def test_shipped_core_has_no_app_or_host_names() -> None:
    for path in [*SRC.glob("*.py"), *HOSTS.glob("*.py")]:
        body = path.read_text().lower()
        for token in _BANNED:
            assert token.lower() not in body, f"{path.relative_to(SRC.parent)} contains {token!r}"


def test_shipped_cli_entry_readonly_envelope(capsys) -> None:
    rc = main(["--json", "type", "hello"])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == 1
    assert payload["ok"] is False
    assert payload["error"] == "readonly"
    assert payload["action"] == "type"
