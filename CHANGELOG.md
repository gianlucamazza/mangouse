# Changelog

All notable changes to mangouse are documented here. Version source:
`src/mangouse/__init__.py`.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.5.0] — 2026-08-16

### Added

- One protocol **holder** per seat session. CLI `click` / `devtools` talk to
  `$XDG_RUNTIME_DIR/mangouse/devtools.sock` (0600). The holder keeps a single
  engine WebSocket, so inspect Allow is once, not once per process.
  `mangouse devtools --hold` runs it in the foreground; the first `click`
  starts it in the background when an endpoint exists.
  `mangouse devtools --stop` tears it down. `probe` / `doctor` report
  `via=hold` when the holder is the client. `MANGOUSE_DEVTOOLS_HOLD=0`
  disables auto-start. Still not a DOM agent.

## [0.4.1] — 2026-08-16

### Fixed

- Inspect-mode engines that listen locally but answer HTTP `/json/list`
  with 404 are discovered from a `DevToolsActivePort` file under the
  user config tree, then `Target.getTargets`. The 0.4.0 install only
  spoke `/json/list`, so `doctor` reported `unset` while a server was
  already listening.
- `pick_page` accepts `Target.getTargets` rows (`targetId`, no page
  WebSocket). Title/URL hint is the compositor's active tab; inspector
  `devtools://` targets are skipped. `Target.activateTarget` runs before
  the click.
- `doctor` / `devtools` report `state`: `unset` · `listening` ·
  `pending` (handshake timed out — usually the inspect Allow dialog) ·
  `connected`, plus `via` (`env` / `config` / `port-file` / `ws`).

### Changed

- Each CLI click still opens its own protocol client (no daemon). Multi-step
  page work stays on a long-lived official DevTools MCP so the engine does
  not re-prompt on every process.

## [0.4.0] — 2026-08-16

### Added

- Optional DevTools Protocol input: when a protocol endpoint is reachable,
  `click` maps seat coordinates into the page viewport and sends
  `Input.dispatchMouseEvent`. Envelope `via` is `devtools` or `ydotool`.
  `mangouse devtools` probes the endpoint. Not a DOM/AX agent — pair the
  official DevTools MCP for that.

## [0.3.0] — 2026-08-16

### Fixed

- `zoom` / region shots label the **output that contains the crop**, not the
  focused output. A crop on DP-2 no longer reports `eDP-1`.
- `--then shot` after `click`/`type`/`key`/`focus` inherits `--window`. A
  click without `--window` captures the output under the click point, not
  whatever output is focused.

### Added

- `click --then shot` sets `hit`: `changed` / `unchanged` / `unknown`
  (hash of a tiny crop around the point, before and after). `ok` is still
  not a hit.
- `target`: observe who receives keys vs who sits under the pointer.
- `clipboard`: read `text/plain` via `wl-paste`. Opt-in
  (`--allow-clipboard`, `allow_clipboard`, or `MANGOUSE_ALLOW_CLIPBOARD`).
  Never writes. Not on MCP.

## [0.2.2] — 2026-08-15

### Added

- `click --window ID` focuses first, matching `type`/`key`. Envelope includes
  `window_id` when set. Skill and practices: `--then shot` after click; `ok`
  is not a hit; do not retry an unchanged shot (ydotool is not `wl_pointer`).

## [0.2.1] — 2026-08-14

### Changed

- Contract and skill name `desktop.cursor` (`x`, `y`, `output`). `click` /
  `zoom` stay explicit coordinates; no second observe command.

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
