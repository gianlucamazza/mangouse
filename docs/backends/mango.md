# Mango backend

Core talks to a `Backend`. Mango lives in `mangouse.backends.mango` and is the
only registry entry in v0.

Auto-detect (`backend = "auto"`): first adapter whose `available()` is true.
Force with `--backend mango`, `MANGOUSE_BACKEND=mango`, or config.

## Mapping (`mmsg` → generic types)

| mmsg | model |
|------|--------|
| client | `Window` (`appid`→`app_id`, `monitor`→`output`, `tags`→`groups`) |
| monitor | `Output` (`tags`→`groups`, `active_tags`→`active_groups`) |
| cursorpos.monitor | `Cursor.output` |
| mango-only flags | `Window.extras` / `Output.extras` |

Commands used by this adapter only:

| argv | Result |
|------|--------|
| `mmsg get version` | `{"version":"0.16.0(…)"}` |
| `mmsg get all-clients` | `{"clients":[…]}` |
| `mmsg get all-monitors` | `{"monitors":[…]}` |
| `mmsg get focusing-client` | one client object |
| `mmsg get client <id>` | one client object |
| `mmsg get cursorpos` | `{"x","y","monitor"}` |

Fixtures: `tests/testdata/mango/`.

`mmsg dispatch` and `mmsg watch` stay backend-private (v1).

Coordinates are global logical pixels (same space as grim `-g`).
