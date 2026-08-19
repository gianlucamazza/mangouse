# Changelog

All notable changes to mangouse are documented here. Version source:
`src/mangouse/__init__.py`.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.8.0] — 2026-08-19

Documentation reorganized for a public repository. No behaviour change; the
minor bump signals that documentation paths moved, so anything linking to the
old ones breaks.

### Changed

- **Every fact now has one home.** The same rule used to live in four to eight
  files — the DevTools/holder explanation alone occupied ~90 lines across
  seven — which is the mechanism behind the drift fixed in 0.6.0: when a fact
  has six homes, five fall behind. Each duplicated fact was assigned a single
  page and linked from the rest.
- **`docs/practices.md` dissolved.** Three files claimed normative authority
  over the same rules with no stated precedence. Its agent-behaviour rules
  moved to `docs/json-contract.md` (now the only authority on the wire
  format), its layout and test invariants to `CONTRIBUTING.md`, and its safety
  doctrine to `docs/security-model.md`.
- **Docs renamed** to names a stranger can navigate: `tools.md` →
  `cli-reference.md`, `headless.md` → `json-contract.md`, `config.md` →
  `configuration.md`, `design.md` → `architecture.md`, `safety.md` →
  `security-model.md`, and `RELEASING.md` → `docs/releasing.md`.
- **README rewritten** for readers who are not the author: the problem
  statement first (it was buried in `design.md`), real requirements, an
  install line that does not assume the author's directory layout, and
  uninstall. Machine-specific setup notes were removed rather than moved.
- `ruff format` applied and enforced; it is now the third CI check.

### Added

- `docs/quickstart.md` — `doctor` to first screenshot, plus the
  blocker-to-fix table that previously existed only inside the agent playbook.
- `docs/backends/README.md` — how to write an adapter for another compositor.
- `CONTRIBUTING.md`, `SECURITY.md`, and a GitHub Actions workflow running
  ruff, ruff format, and pytest on Python 3.13.
- A glossary in `docs/architecture.md`: *seat grant*, *group*, *confine*,
  *hit*, *via*, and *holder* were used throughout without ever being defined.
- Three structural tests in `tests/test_docs_alignment.py`: every relative
  markdown link resolves, no document outside the changelog hardcodes a
  version, and every `MANGOUSE_*` variable the code reads appears in
  `docs/configuration.md`. These check names, not truth — the existing tests
  that compare docs against `build_parser()`, `errors.py`, and `run_doctor()`
  remain the ones that check whether a claim is correct.

### Fixed

- `docs/design.md` claimed the shipped package was `0.5.0`, two releases after
  that stopped being true. Documents no longer state a version at all; the new
  test enforces it.
- `docs/practices.md` still told readers to look for `doctor` `state=pending` —
  the field that does not exist, already removed from `SKILL.md` in 0.6.0.
- `SKILL.md` pointed at `docs/headless.md` as a relative path, but the file is
  symlinked into skill roots where that path does not resolve. The one
  cross-reference an agent needs was unreachable exactly where it is read; it
  is now an absolute URL.
- `MANGOUSE_DEVTOOLS_HOLD` was documented only in the skill and
  `YDOTOOL_SOCKET` nowhere; both are now in the configuration reference.
- `lock_procs` was documented but absent from `examples/config.toml`, so it
  could not be discovered by copying the sample.
- The generic CLI reference named `mmsg dispatch focusid client,<id>` — a
  backend-private argv in a compositor-agnostic document, crossing the
  boundary `tests/test_layout.py` enforces in code.

## [0.7.0] — 2026-08-19

Hardening pass on the seat gates and the hand-rolled protocol layer. No new
commands.

### Fixed

- **A scalar string in a policy key was iterated as characters.**
  `deny_app_ids = "vault"` became eight one-letter substrings that match
  almost every window; the same slip on `confine_app_ids` silently disabled
  confinement, and on `lock_procs` broke lock detection. A bare string is now
  one token.
- **A malformed `config.toml` escaped as a Python traceback** (`ValueError`,
  `TOMLDecodeError`) instead of the `--json` envelope, taking `doctor` — the
  diagnostic command — down with it. Config faults are now `bad_config`,
  exit 2.
- **The DevTools holder died on a malformed local request.**
  `json.JSONDecodeError` is not an `OSError`, so it escaped `serve()`'s
  handler and ended the seat session's protocol client. Malformed input is
  now an error reply; the holder stays up.
- **`_recv_json` buffered without bound**: a peer that never sent a newline
  could grow the holder's memory. Capped at 1 MiB.
- **The holder socket was chmod'd after `bind()`**, leaving a window where
  it carried the process umask. The bind now runs under `umask 0o077`, and
  `$XDG_RUNTIME_DIR/mangouse/` (shots and socket) has its `0700` re-asserted
  rather than inherited from whatever an earlier run left.
- **`_ws_recv` ignored the FIN bit**, so a fragmented CDP reply arrived
  truncated and parsed as invalid JSON. Continuation frames are reassembled
  and interleaved control frames skipped; frames are capped at 32 MiB.
- **Protocol faults escaped as `ValueError`/`struct.error`** past the
  `except OSError` guard that is supposed to fall back to ydotool, so a
  misbehaving endpoint failed the click instead of degrading to the seat.
- **`_call` could spin indefinitely** on a chatty target while waiting for
  its reply id; it now has a deadline.
- **`session_locked()` abandoned the whole scan** on the first `pgrep`
  timeout, so a lock client later in the list went unnoticed. It now
  continues; only a missing `pgrep` gives up.
- **`Holder.serve()` crashed when not on the main thread** (`signal.signal`
  raises there), which also made it untestable.

### Changed

- `runtime_dir()` has one definition (`screen.py`); `devtools_hold` delegates.

## [0.6.0] — 2026-08-19

### Changed

- Argument errors no longer masquerade as `missing_dep`. An empty or
  unmappable key combo is `bad_key`; an unknown `--button` is the new
  `bad_arg` code. Both exit 2, like the other caller-fault codes.
- `click` resolves the backend once per invocation instead of up to three
  times (each resolve re-read config and re-shelled the compositor IPC).
- `Backend` protocol declares `cursor()`, which `Desktop` and `target`
  already required from every adapter.

### Fixed

- Docs and skill described a smaller surface than the code: the MCP extra
  exposes four observe-only tools (`target` was missing from `README.md`,
  `docs/tools.md`, `docs/safety.md`); `--allow-clipboard`, `--button`,
  `--size`, `--lossless`, `--fit`, `devtools --hold/--stop` were
  undocumented; the error table lacked `not_implemented`; `docs/safety.md`
  still claimed "no listen socket" after the 0.5.0 holder.
- `SKILL.md` told agents to read `doctor` → `devtools.state` and
  `doctor` `via=hold`. Neither field exists: `doctor` carries DevTools as a
  `checks[]` row, and `state`/`via` belong to the `devtools` action.
- `install.sh` links the skill into `~/.claude/skills` too, not only
  `~/.grok/skills` and `~/.agents/skills`.
- `docs/backends/mango.md` claimed `mmsg dispatch` was backend-private
  (it is reachable through `mangouse dispatch`) and promised an `mmsg
  watch` integration that does not exist.

### Added

- `tests/test_docs_alignment.py` pins the classes of drift above: every
  parser flag appears in `docs/tools.md`, every error code in the
  `docs/headless.md` table, the `@server.tool` set matches all three
  documents that list it, and `run_doctor()`'s keys match the documented
  `doctor` row.

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
