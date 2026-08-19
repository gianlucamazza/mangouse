# Configuration

Optional. Path: `$MANGOUSE_CONFIG` or `~/.config/mangouse/config.toml`.
Missing file = `backend = "auto"` and empty deny list.
The authoritative sample is [`examples/config.toml`](../examples/config.toml).

```toml
backend = "auto"
allow_input = false
allow_clipboard = false
# Optional DevTools Protocol HTTP origin, e.g. http://127.0.0.1:9222
devtools_url = ""

[policy]
deny_app_ids = []
confine_groups = []
confine_app_ids = []
```

| key | default | meaning |
|-----|---------|---------|
| `allow_input` | `false` | same as `--allow-input` / `MANGOUSE_ALLOW_INPUT=1` |
| `allow_clipboard` | `false` | same as `--allow-clipboard` / `MANGOUSE_ALLOW_CLIPBOARD=1` |
| `devtools_url` | `""` | HTTP origin of a DevTools Protocol endpoint. Empty: look for `DevToolsActivePort` under `$XDG_CONFIG_HOME/*` |
| `backend` | `auto` | `auto` or a name in `session.REGISTRY` |
| `policy.deny_app_ids` | `[]` | case-insensitive substrings matched against `app_id` and title |
| `policy.confine_groups` | `[]` | if set, only windows on these group indexes |
| `policy.confine_app_ids` | `[]` | if set, only matching `app_id` |
| `lock_procs` | swaylock, gtklock, waylock, hyprlock | `pgrep -x` names treated as a session lock; input refuses while one runs |

A bare string is accepted wherever a list is expected and treated as a single
token: `deny_app_ids = "vault"` means one token, not eight one-letter
substrings. Anything else of the wrong shape raises `bad_config` (exit 2) with
the offending key named, rather than failing silently or crashing.

Environment overrides:

| var | effect |
|-----|--------|
| `MANGOUSE_CONFIG` | config path |
| `MANGOUSE_BACKEND` | force backend (wins over file for detect, after `--backend`) |
| `MANGOUSE_ALLOW_INPUT` | same as `--allow-input` |
| `MANGOUSE_ALLOW_CLIPBOARD` | same as `--allow-clipboard` |
| `MANGOUSE_DEVTOOLS_URL` | DevTools HTTP origin (wins over file) |
| `MANGOUSE_DEVTOOLS_WS` | Browser WebSocket URL (wins over the port file) |
| `MANGOUSE_DEVTOOLS_HOLD` | `0` disables auto-starting the protocol holder |

Read but not owned by mangouse:

| var | effect |
|-----|--------|
| `WAYLAND_DISPLAY` | Must be set; `doctor` blocks without it |
| `XDG_RUNTIME_DIR` | Where shots and the holder socket land (mode `0700`) |
| `XDG_CONFIG_HOME` | Searched for a browser `DevToolsActivePort` file |
| `YDOTOOL_SOCKET` | Passed through to `ydotool`; defaults to `/run/user/$UID/.ydotool_socket` |

Precedence everywhere is the same: command-line flag, then environment, then
the config file, then the built-in default.
