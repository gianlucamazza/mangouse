"""CLI surface and version stay documented."""

from __future__ import annotations

from pathlib import Path

from mangouse import __version__
from mangouse.config import parse_config
from mangouse.hosts.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_in_the_changelog() -> None:
    assert f"## [{__version__}]" in (ROOT / "CHANGELOG.md").read_text()


def _markdown_files() -> list[Path]:
    skip = {".venv", ".git", "node_modules"}
    return [
        path
        for path in ROOT.rglob("*.md")
        if not any(part in skip for part in path.relative_to(ROOT).parts)
    ]


def test_no_document_hardcodes_a_version() -> None:
    """A version string in prose goes stale. CHANGELOG is the one exception.

    Regression: the architecture page claimed the shipped package was 0.5.0
    two releases after that stopped being true.
    """
    import re

    # Anchored so an IPv4 literal (127.0.0.1) is not read as a version.
    pattern = re.compile(r"(?<![\d.])\d+\.\d+\.\d+(?![\d.])")
    allowed = {__version__, "0.16.0"}  # 0.16.0 is a compositor fixture value
    stale: list[str] = []
    for path in _markdown_files():
        if path.name == "CHANGELOG.md":
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            for found in pattern.findall(line):
                if found not in allowed:
                    rel = path.relative_to(ROOT)
                    stale.append(f"{rel}:{lineno} {found}")
    assert not stale, f"hardcoded versions in docs: {stale}"


def test_relative_links_resolve() -> None:
    """Renaming a doc must not leave a dangling link behind."""
    import re

    link = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    broken: list[str] = []
    for path in _markdown_files():
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            for target in link.findall(line):
                target = target.split("#", 1)[0].strip()
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                if not (path.parent / target).exists():
                    broken.append(f"{path.relative_to(ROOT)}:{lineno} -> {target}")
    assert not broken, f"broken relative links: {broken}"


def test_env_vars_are_documented() -> None:
    """Every MANGOUSE_* the code reads is in the configuration reference."""
    import re

    names: set[str] = set()
    for path in (ROOT / "src").rglob("*.py"):
        names |= set(re.findall(r"MANGOUSE_[A-Z_]+", path.read_text()))
    assert names, "no MANGOUSE_* env vars found in src/"
    docs = (ROOT / "docs" / "configuration.md").read_text()
    missing = sorted(n for n in names if n not in docs)
    assert not missing, f"undocumented env vars in docs/configuration.md: {missing}"


def test_cli_actions_are_documented() -> None:
    parser = build_parser()
    cmds = set()
    for action in parser._actions:
        if action.dest == "cmd" and action.choices:
            cmds = set(action.choices)
            break
    headless = (ROOT / "docs" / "json-contract.md").read_text()
    for name in cmds:
        assert f"`{name}`" in headless, f"{name} missing from docs/json-contract.md"


def test_skill_and_contract_name_cursor() -> None:
    skill = (ROOT / "skills" / "mangouse" / "SKILL.md").read_text()
    headless = (ROOT / "docs" / "json-contract.md").read_text()
    assert "desktop.cursor" in skill
    assert "Cursor:" in headless
    assert "click X Y --window ID --then shot" in skill
    assert "ok` means ydotool ran" in skill or "ok` means ydotool" in skill
    assert "hit" in skill
    assert "target" in skill
    assert "shot_ready" in skill
    assert "click_ready" in skill
    assert 'error: "usage"' in skill
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
    """docs/cli-reference.md is the flag reference. A new flag must land there too."""
    parser = build_parser()
    flags = _optstrings(parser)
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            for sub in choices.values():
                flags |= _optstrings(sub)
    tools = (ROOT / "docs" / "cli-reference.md").read_text()
    missing = sorted(f for f in flags if f not in tools)
    assert not missing, f"undocumented flags in docs/cli-reference.md: {missing}"


def test_error_codes_are_documented() -> None:
    """Every structured code an agent can branch on is in the headless table."""
    import re

    body = (ROOT / "src" / "mangouse" / "errors.py").read_text()
    codes = set(re.findall(r'super\(\)\.__init__\(\s*"([a-z_]+)"', body))
    assert codes, "no error codes found in errors.py"
    headless = (ROOT / "docs" / "json-contract.md").read_text()
    missing = sorted(c for c in codes if f"| `{c}` |" not in headless)
    assert not missing, f"undocumented error codes in docs/json-contract.md: {missing}"


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
    # Two homes by design: the surface reference and the security model. The
    # README deliberately does not enumerate them a third time.
    for rel, marker in (
        ("docs/cli-reference.md", "The MCP extra exposes"),
        ("docs/security-model.md", "The extra exposes"),
    ):
        text = (ROOT / rel).read_text()
        assert marker in text, f"{rel} lost its MCP tool sentence"
        window = text.split(marker, 1)[1].split(".")[0]
        listed = set(re.findall(r"`([a-z_]+)`", window))
        assert listed == tools, f"{rel} lists {sorted(listed)}, MCP exposes {sorted(tools)}"


def test_doctor_keys_are_documented(backend) -> None:
    """SKILL/docs must not invent doctor fields (e.g. a `devtools` object)."""
    from mangouse.doctor import run_doctor

    headless = (ROOT / "docs" / "json-contract.md").read_text()
    row = next(line for line in headless.splitlines() if line.startswith("| `doctor` |"))
    report = run_doctor(backend)
    missing = sorted(k for k in report if f"`{k}`" not in row)
    assert not missing, f"doctor keys missing from docs/json-contract.md: {missing}"
