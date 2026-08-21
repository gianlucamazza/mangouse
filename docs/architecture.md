# Architecture

## The problem

Coding agents have no native computer use on a Linux Wayland seat. The
off-the-shelf servers that exist are each bound to one compositor, one agent
host, or a hardcoded list of applications — so they break when you change your
desktop, your agent, or your apps.

mangouse is a **seat adapter** instead. It observes, and with a grant drives,
whatever desktop is in front of the user. It does not know about password
managers, browsers, terminals, or which coding agent called it. That ignorance
is the design, not a gap: the moment the core learns an application name, it
starts rotting the way the alternatives did.

## Glossary

The rest of the docs use these words without stopping to define them:

| Term           | Meaning                                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **seat**       | One keyboard, one pointer, one set of outputs — the physical session a person is using. mangouse shares yours; it does not create a second one.                                |
| **seat grant** | Explicit permission to mutate that seat (`--allow-input`). Observation never needs one.                                                                                        |
| **output**     | A monitor, in the compositor's coordinate space.                                                                                                                               |
| **group**      | The compositor's way of grouping windows — tags in mango, workspaces elsewhere. mangouse exposes `groups` / `active_groups` and does not care which metaphor the backend uses. |
| **confine**    | A user policy that limits which windows may be targeted at all, by `app_id` or by group.                                                                                       |
| **hit**        | Whether the pixels under a click actually changed. Distinguishes "delivered" from "had an effect".                                                                             |
| **via**        | Which transport carried an operation — `ydotool` for the seat, `devtools` for the browser protocol.                                                                            |
| **holder**     | A local daemon owning the single browser protocol connection, so the browser's Allow prompt happens once per session rather than once per click. Drops that TCP when the browser closes so the browser can quit; the unix socket stays and reconnects. |
| **dispatch**   | An opaque backend action string passed straight through. Not a synthesized keystroke, and not parsed by the core.                                                              |

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

| Layer         | Knows about                             | Must not know about                  |
| ------------- | --------------------------------------- | ------------------------------------ |
| Core models   | windows, outputs, groups, cursor, shots | app names, hosts, compositor jargon  |
| Policy        | user tokens from config                 | shipped fingerprints                 |
| Safety        | the readonly seat gate                  | specific applications or agent hosts |
| Backend       | one compositor's IPC                    | agent hosts, MCP, specific apps      |
| Host adapters | CLI flags, MCP tools, skill text        | compositor internals                 |

Two invariants hold this together, and both are enforced by
`tests/test_layout.py`, not by convention:

1. **No compositor IPC outside `backends/`.** The core and the hosts may not
   name `mmsg`, `hyprctl`, or any successor. `dispatch` is an opaque string.
2. **No application names anywhere in the shipped code.** Policy tokens come
   from the user's config; the library ships an empty deny list.

MangoWM is the first backend, not the product identity. Adding another is
[documented separately](backends/README.md).

## Configuration

There is one authoritative sample — `examples/config.toml` — and one page that
explains each key: [configuration.md](configuration.md). This page deliberately
does not inline a third copy.

## Scope

| Milestone | Ships                                                                                |
| --------- | ------------------------------------------------------------------------------------ |
| **v0**    | `doctor`, `desktop`, `shot`                                                          |
| **v1**    | `focus` / `type` / `key` / `click` / `dispatch` / `zoom`, policy, lock refusal       |
| **v1.1**  | `--then shot` follows window or point; `hit`; `target`; opt-in clipboard read        |
| **v1.2**  | Optional DevTools Protocol click (`via`), inspect discovery via `DevToolsActivePort` |
| **v1.3**  | One local protocol holder so inspect Allow is once per seat session                  |
| **v2**    | More backends; optionally AT-SPI as another observer — not an app list               |

These are scope milestones, not release numbers. For what is actually shipped,
read [CHANGELOG.md](../CHANGELOG.md).

## Non-goals

- **An LLM inside the tool.** mangouse returns data; the agent decides.
- **Browser automation.** The DevTools path exists to make one click land on a
  webview that ignores evdev. Page, DOM, and accessibility automation belong to
  a separate long-lived DevTools MCP.
- **Shipped application fingerprints.** No deny list, no app catalog, no
  special cases.
- **A network daemon.** stdio only. The single socket is local, owner-only, and
  exists for the browser holder.
- **Being one agent host's plugin.** CLI, MCP, and the skill are peers over the
  same contract.
