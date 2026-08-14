# Changelog

All notable changes to mangouse are documented here. Version source:
`src/mangouse/__init__.py`.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] — 2026-08-14

First tagged release.

### Added

- Observe: `doctor`, `desktop`, `shot`, `zoom` with `--json` envelope `schema: 1`.
- Mutate (opt-in): `focus`, `type`, `key`, `click`, `dispatch` via `wtype` /
  `ydotool` / mango `focusid`.
- Safety: readonly default; `allow_input` in config or `--allow-input` or
  `MANGOUSE_ALLOW_INPUT`; user `deny_app_ids` / `confine_*`; lock refuse;
  Super/logo combos rejected (`bad_key`).
- Hosts: CLI + optional stdio MCP (`MCPServer`, observe-only) + agent skill.
- Layered layout: `hosts/` → core → `backends/mango`.
- `./install.sh` (`uv tool install --force --reinstall` + skill links).

### Not included

- Browser automation, extra compositor backends, AUR, published GitHub release.
