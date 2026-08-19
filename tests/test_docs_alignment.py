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


def test_skill_and_contract_name_cursor() -> None:
    skill = (ROOT / "skills" / "mangouse" / "SKILL.md").read_text()
    headless = (ROOT / "docs" / "headless.md").read_text()
    assert "desktop.cursor" in skill
    assert "Cursor:" in headless
    assert "click X Y --window ID --then shot" in skill
    assert "ok` means ydotool ran" in skill or "ok` means ydotool" in skill
    assert "hit" in skill
    assert "target" in skill
    # doctor reports DevTools as a `checks[]` row, not a `devtools` object.
    assert "devtools.state" not in skill
    assert "doctor` `via=hold" not in skill


def test_example_config_keys_parse() -> None:
    import tomllib

    data = tomllib.loads((ROOT / "examples" / "config.toml").read_text())
    cfg = parse_config(data)
    assert cfg.allow_input is False
    assert cfg.backend == "auto"


def _optstrings(parser) -> set[str]:
    out: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            if opt not in {"-h", "--help"}:
                out.add(opt)
    return out


def test_cli_flags_are_documented() -> None:
    """docs/tools.md is the flag reference. A new flag must land there too."""
    parser = build_parser()
    flags = _optstrings(parser)
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            for sub in choices.values():
                flags |= _optstrings(sub)
    tools = (ROOT / "docs" / "tools.md").read_text()
    missing = sorted(f for f in flags if f not in tools)
    assert not missing, f"undocumented flags in docs/tools.md: {missing}"


def test_error_codes_are_documented() -> None:
    """Every structured code an agent can branch on is in the headless table."""
    import re

    body = (ROOT / "src" / "mangouse" / "errors.py").read_text()
    codes = set(re.findall(r'super\(\)\.__init__\(\s*"([a-z_]+)"', body))
    assert codes, "no error codes found in errors.py"
    headless = (ROOT / "docs" / "headless.md").read_text()
    missing = sorted(c for c in codes if f"| `{c}` |" not in headless)
    assert not missing, f"undocumented error codes in docs/headless.md: {missing}"


def _mcp_tool_names() -> set[str]:
    """AST-only: hosts/mcp.py must stay importable without the `mcp` extra."""
    import ast

    tree = ast.parse((ROOT / "src" / "mangouse" / "hosts" / "mcp.py").read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            func = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(func, ast.Attribute) and func.attr == "tool":
                names.add(node.name)
    return names


def test_mcp_tool_list_matches_docs() -> None:
    import re

    tools = _mcp_tool_names()
    assert tools, "no @server.tool functions found in hosts/mcp.py"
    for rel, marker in (
        ("docs/tools.md", "MCP extra exposes only"),
        ("docs/safety.md", "**MCP** is observe-only"),
        ("README.md", "Observe-only tools:"),
    ):
        text = (ROOT / rel).read_text()
        assert marker in text, f"{rel} lost its MCP tool sentence"
        window = text.split(marker, 1)[1].split(".")[0]
        listed = set(re.findall(r"`([a-z_]+)`", window))
        assert listed == tools, f"{rel} lists {sorted(listed)}, MCP exposes {sorted(tools)}"


def test_doctor_keys_are_documented(backend) -> None:
    """SKILL/docs must not invent doctor fields (e.g. a `devtools` object)."""
    from mangouse.doctor import run_doctor

    headless = (ROOT / "docs" / "headless.md").read_text()
    row = next(line for line in headless.splitlines() if line.startswith("| `doctor` |"))
    report = run_doctor(backend)
    missing = sorted(k for k in report if f"`{k}`" not in row)
    assert not missing, f"doctor keys missing from docs/headless.md: {missing}"
