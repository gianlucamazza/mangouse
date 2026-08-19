# Tools

CLI and MCP share the core. Neither names applications.

| CLI | MCP | Now |
|-----|-----|-----|
| `mangouse doctor` | `doctor` | implemented |
| `mangouse desktop` | `desktop` | implemented |
| `mangouse shot [--output NAME] [--window ID] [--full] [--lossless] [--fit PX]` | `shot` | implemented |
| `mangouse focus ID` | — | `--allow-input` |
| `mangouse type TEXT` | — | `--allow-input` |
| `mangouse key COMBO` | — | `--allow-input` |
| `mangouse click X Y [--button left\|right\|middle] [--window ID]` | — | `--allow-input` |
| `mangouse dispatch SPEC` | — | `--allow-input` |
| `mangouse zoom X Y [--size PX] [--lossless] [--fit PX]` | — | observe |
| `mangouse target` | `target` | observe |
| `mangouse clipboard` | — | `--allow-clipboard` |
| `mangouse devtools [--hold] [--stop]` | — | observe |

Global flags: `--json`, `--backend`, `--allow-input`, `--allow-clipboard`,
`--version`.
`--monitor` is an alias of `--output`.

## doctor

Generic seat (Wayland, grim) plus the active backend’s checks.
`backend` is a field (`"mango"` today), not a hardcoded assumption.
`input_implemented` is `true`. Mutate still needs a seat grant.

## desktop

`backend`, `version`, `outputs`, `windows`, `focused`, `cursor`.
Grouping is `groups` / `active_groups` (tags, workspaces, or whatever the
backend uses).

## shot

`$XDG_RUNTIME_DIR/mangouse/shot-*.jpg` (JPEG q90) or `--lossless` PNG.
JSON includes geometry and `scale`: `global = origin + pixel / scale`.
`--fit PX` (default 1568) shrinks the long edge with `magick` if present and
rewrites `scale`. `--fit 0` leaves the native capture.

MCP extra exposes only `doctor`, `desktop`, `shot`, `target`. Mutate is CLI-only.

## Seat grant

Without `--allow-input`, `MANGOUSE_ALLOW_INPUT=1`, or `allow_input = true` in
config: `readonly`, exit 2.
`--then desktop|shot` attaches a fresh observation after a mutate.
`--then shot` inherits `--window`; a click without it captures the output
under the point. `click --then shot` sets `hit`.
`key` refuses Super/logo (`bad_key`). Keyboard is `wtype`; pointer is `ydotool`.
`click --window ID` focuses first, same as `type`/`key`. ydotool is not
`wl_pointer`: envelope `ok` means the uinput click ran. Confirm with `hit`.
`target` reports compositor focus vs window under the pointer.
`clipboard` is CLI-only, read-only, and denied unless opted in.
`click` uses a DevTools endpoint when one is reachable (`via` in the
envelope): `devtools_url` / `MANGOUSE_DEVTOOLS_URL`, or a
`DevToolsActivePort` file under `$XDG_CONFIG_HOME/*`. Seat evdev is the
fallback. `mangouse devtools` / `doctor`'s `devtools` check report
`state` and `via`. `pending` means the handshake timed out (the engine
is waiting for an Allow on its chrome, not a page). The first `click` starts
a local holder that keeps one engine client for the seat session
(`via=hold`); `devtools --hold` runs it in the foreground and `devtools
--stop` ends it, answering `stopped` and `holder: false`. Official
page/DOM/AX automation is a separate, long-lived DevTools MCP — this CLI
must not grow evaluate/fill.
Focus is `mmsg dispatch focusid client,<id>` on the mango backend.
