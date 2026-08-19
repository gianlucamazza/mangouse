# Design

## Problem

Coding agents have no native computer use on a Linux Wayland seat. Off-the-shelf
servers are bound to one compositor, one host, or a list of applications.

mangouse is a **seat adapter**: observe (and later drive) whatever desktop is
in front of the user. It does not know about password managers, browsers,
terminals, or which coding agent called it.

## Layers

```
hosts/cli.py  hosts/mcp.py  skills/     # how you talk to mangouse
        │
   contract.py  (--json, schema 1)
        │
   core: models, errors, config, policy, safety, doctor, session,
         screen, input, clipboard, devtools, devtools_hold
        │
   backend.py  (Backend protocol)
        │
   backends/mango.py                  # first adapter
        │
   compositor IPC + grim + wtype/ydotool + wl-paste + DevTools
```

| Layer | Knows about | Must not know about |
|-------|-------------|---------------------|
| Core models | windows, outputs, groups, cursor, shots | app names, hosts, mango tags |
| Policy | user tokens from config | shipped fingerprints |
| Safety | readonly seat gate | 1Password, Grok, polkit |
| Backend | one compositor’s IPC | Grok, MCP, specific apps |
| Host adapters | CLI flags / MCP tools / skill text | compositor internals |

MangoWM is the first **backend**, not the product identity. `dispatch` is an
opaque backend action string, not `mmsg` in the core.

## Policy

`~/.config/mangouse/config.toml` (or `MANGOUSE_CONFIG`):

```toml
backend = "auto"        # or "mango"
allow_input = false     # seat grant for type/click/focus
allow_clipboard = false # clipboard read
devtools_url = ""       # empty = discover DevToolsActivePort, else seat only

[policy]
deny_app_ids = []   # user-supplied substrings; empty = deny none
```

`examples/config.toml` is the full key list; `docs/config.md` documents each.

The library ships **no** deny list. If you want to protect a vault or a
browser profile, you add the `app_id` tokens.

## Versions

| | Ships |
|---|---|
| **v0** | `doctor`, `desktop`, `shot`. |
| **v1** | `focus` / `type` / `key` / `click` / `dispatch` / `zoom` + policy + lock refuse. |
| **v1.1** | `--then shot` follows window/point; `hit`; `target`; clipboard read opt-in. |
| **v1.2** | Optional DevTools Protocol click (`via`); inspect discovery via `DevToolsActivePort`; `devtools` reports `state`/`via`. Not a browser/DOM agent. |
| **v1.3** | One local protocol holder (`devtools --hold`) so inspect Allow is once per seat session. |
| **v2** | More backends; optional AT-SPI as another observer, not an app list. |

Milestones are scope, not release numbers. The shipped package is `0.5.0`
(v1.3); `CHANGELOG.md` is the version history.

## Non-goals

- Bundling knowledge of specific applications.
- Being a browser agent (separate long-lived DevTools MCP).
- Being a Grok-only tool (CLI + MCP + skill are hosts).
- Reviving `hyprland_agent` or replacing `jarvis-shot`.
