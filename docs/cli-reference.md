# CLI reference

Every command below prints a JSON envelope with `--json`. The envelope shape,
the per-action keys, and the error codes are specified in
[json-contract.md](json-contract.md) — this page describes the surface, that
page is the contract.

CLI and MCP share the same core. Neither names applications.

## Commands

| Command                                                                        | MCP tool  | Grant               |
| ------------------------------------------------------------------------------ | --------- | ------------------- |
| `mangouse doctor`                                                              | `doctor`  | observe             |
| `mangouse desktop`                                                             | `desktop` | observe             |
| `mangouse shot [--output NAME] [--window ID] [--full] [--lossless] [--fit PX]` | `shot`    | observe             |
| `mangouse zoom X Y [--size PX] [--lossless] [--fit PX]`                        | —         | observe             |
| `mangouse target`                                                              | `target`  | observe             |
| `mangouse devtools [--hold] [--stop]`                                          | —         | observe             |
| `mangouse clipboard`                                                           | —         | `--allow-clipboard` |
| `mangouse focus ID`                                                            | —         | `--allow-input`     |
| `mangouse type TEXT`                                                           | —         | `--allow-input`     |
| `mangouse key COMBO`                                                           | —         | `--allow-input`     |
| `mangouse click X Y [--button left\|right\|middle] [--window ID]`              | —         | `--allow-input`     |
| `mangouse dispatch SPEC`                                                       | —         | `--allow-input`     |

Global flags: `--json`, `--backend NAME`, `--allow-input`, `--allow-clipboard`,
`--version`. `--monitor` is an alias of `--output`.

Every mutate command takes `--then none|desktop|shot`, which attaches a fresh
observation to the same envelope so you do not need a second round trip.

The MCP extra exposes `doctor`, `desktop`, `shot`, and `target`. All four are
read-only; mutation is CLI-only by design, not by omission.

## doctor

Generic seat checks (Wayland, `grim`, the input binaries) plus whatever the
active backend reports. `backend` is a field, not a hardcoded assumption.

`ready` is session health; the envelope's `ok` is command health. Do not
collapse them: `doctor` returning `ok: true` with `ready: false` is the normal
way it tells you the session is unusable.

DevTools status appears here as a row in `checks[]` with id `devtools`, not as
a top-level object. For its `state` and `via` as real fields, call `devtools`.

## desktop

`backend`, `version`, `outputs`, `windows`, `focused`, `cursor`.

Prefer this over `shot` when you want to find something. It is cheaper, it is
structured, and it does not require interpreting an image.

Grouping is exposed as `groups` / `active_groups`, whatever the backend calls
them underneath — tags, workspaces, or otherwise. Backend-private fields live
in `extras`; hosts must not depend on them.

Pointer position is `desktop.cursor`. There is no separate command for it.

## shot and zoom

`shot` writes `$XDG_RUNTIME_DIR/mangouse/shot-*.jpg` (JPEG q90), or a PNG with
`--lossless`. Hosts read the path; no image bytes travel in the envelope.

`--fit PX` (default 1568) shrinks the long edge with `magick` when it is
present and rewrites `scale` accordingly, so this still holds:

```
global = origin + pixel / scale
```

`--fit 0` leaves the native capture. `--lossless` still fits unless you also
pass `--fit 0`.

`shot` captures a whole output unless you narrow it with `--window`. `zoom X Y`
crops around a global point instead, naming the output that contains it — reach
for it instead of a full capture when you want to read one region.

## Seat grant and input

Without a grant, mutate returns `readonly` with exit 2. The three ways to grant
it, and why the flag is the honest default, are in
[security-model.md](security-model.md).

- Keyboard is `wtype`; pointer is `ydotool`.
- `click --window ID` focuses first, the same way `type` and `key` do.
- `key` refuses Super/logo combos with `bad_key`. Compositor bindings go
  through `dispatch SPEC`, which is opaque backend text, not a keystroke.
- ydotool is evdev/uinput, not `wl_pointer`. Envelope `ok` means the uinput
  click ran — nothing more.

`--then shot` after a mutate captures that window when `--window` was given,
and otherwise the output under the click coordinates. On `click` it also sets
`hit`:

| `hit`       | Meaning                                                      |
| ----------- | ------------------------------------------------------------ |
| `changed`   | Pixels under the point moved. Something reacted.             |
| `unchanged` | Delivered, nothing reacted. **Do not retry the same point.** |
| `unknown`   | The crop could not be hashed.                                |

`target` reports compositor keyboard focus versus the window under the pointer.
It does not distinguish window chrome from content inside a client.

`clipboard` reads `text/plain` only, only with its own grant, and never writes.

## DevTools protocol clicks

Some webviews ignore evdev entirely: `click` returns `ok` with
`hit: unchanged`, forever. For those, mangouse can dispatch the click through
the Chrome DevTools Protocol instead, when an endpoint is reachable.

This is a fallback for one operation. mangouse is not a DOM agent and will not
grow `evaluate`, `fill`, or accessibility trees — for page automation, run a
real DevTools MCP alongside it.

**Discovery**, in order: `MANGOUSE_DEVTOOLS_WS`, then `devtools_url` /
`MANGOUSE_DEVTOOLS_URL`, then a `DevToolsActivePort` file found under
`$XDG_CONFIG_HOME/*`. `click` reports which path it used as `via`; a seat
fallback reports `via: "ydotool"`.

**Status.** `mangouse --json devtools` reports:

| `state`     | Meaning                                                              |
| ----------- | -------------------------------------------------------------------- |
| `unset`     | No endpoint configured or discovered                                 |
| `listening` | An endpoint answered, but exposes no page                            |
| `pending`   | The handshake timed out — usually the inspect **Allow** dialog is up |
| `connected` | Usable                                                               |

with `via` naming the discovery path (`env`, `config`, `port-file`, `ws`,
`http`, `hold`).

**The holder.** Each new WebSocket to the browser re-prompts Allow, which would
mean one dialog per click. So the first `click` starts a local holder that
keeps a single browser connection for the seat session, and CLI processes talk
to it over a `0600` unix socket instead of to the browser. Allow happens once.

```bash
mangouse --json devtools --hold   # run it in the foreground
mangouse --json devtools --stop   # tear it down: {"stopped": true, "holder": false}
```

`MANGOUSE_DEVTOOLS_HOLD=0` disables the auto-start.

**Two ways to expose an endpoint.** They are different Chrome behaviours, not
alternatives to pick between by version:

1. **Daily profile.** Chrome 144+ exposes a checkbox at
   `chrome://inspect/#remote-debugging`. Turn it on; the first client raises an
   **Allow** prompt on the browser chrome, which you confirm with a seat click
   once. A banner while attached is expected.
2. **Isolated profile.** Launch Chrome with a **non-default**
   `--user-data-dir` plus `--remote-debugging-port=9222`. Chrome 136+ ignores
   `--remote-debugging-port` on the default profile, so this only works on a
   separate one — and you should not add the flag to your daily browser's
   launch options.
