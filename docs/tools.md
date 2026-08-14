# Tools

CLI and MCP share the core. Neither names applications.

| CLI | MCP | Now |
|-----|-----|-----|
| `mangouse doctor` | `doctor` | implemented |
| `mangouse desktop` | `desktop` | implemented |
| `mangouse shot [--output NAME] [--window ID] [--full]` | `shot` | implemented |
| `mangouse focus ID` | — | `--allow-input` |
| `mangouse type TEXT` | — | `--allow-input` |
| `mangouse key COMBO` | — | `--allow-input` |
| `mangouse click X Y` | — | `--allow-input` |
| `mangouse dispatch SPEC` | — | `--allow-input` |
| `mangouse zoom X Y` | — | observe |

Global flags: `--json`, `--backend`, `--allow-input`, `--version`.
`--monitor` is an alias of `--output`.

## doctor

Generic seat (Wayland, grim) plus the active backend’s checks.
`backend` is a field (`"mango"` today), not a hardcoded assumption.
`input_implemented` is `false` in v0.

## desktop

`backend`, `version`, `outputs`, `windows`, `focused`, `cursor`.
Grouping is `groups` / `active_groups` (tags, workspaces, or whatever the
backend uses).

## shot

`$XDG_RUNTIME_DIR/mangouse/shot-*.jpg` (JPEG q90) or `--lossless` PNG.
JSON includes geometry and `scale`: `global = origin + pixel / scale`.
`--fit PX` (default 1568) shrinks the long edge with `magick` if present and
rewrites `scale`. `--fit 0` leaves the native capture.

MCP extra exposes only `doctor`, `desktop`, `shot`. Mutate stubs stay CLI-only.

## Stubs

Without `--allow-input` / `MANGOUSE_ALLOW_INPUT=1`: `readonly`, exit 2.
`--then desktop|shot` attaches a fresh observation after a mutate.
`key` refuses Super/logo (`bad_key`). Keyboard is `wtype`; pointer is `ydotool`.
Focus is `mmsg dispatch focusid client,<id>` on the mango backend.
