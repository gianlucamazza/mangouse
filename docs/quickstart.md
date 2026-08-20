# Quickstart

From nothing to your first screenshot. Every command prints JSON when you pass
`--json`; the envelope is specified in [json-contract.md](json-contract.md).

## 1. Check the session

```bash
mangouse --json doctor
```

`doctor` never fails because the session is broken — it _reports_ that. Read
two fields:

- `ready` — can mangouse observe this desktop at all?
- `blockers` — the ids of the checks that say no. Empty means you are good.

```json
{
  "ok": true,
  "ready": true,
  "backend": "mango",
  "blockers": [],
  "checks": [
    { "id": "wayland", "ok": true, "detail": "wayland-0", "blocker": true }
  ]
}
```

If `blockers` is not empty, find the id in the table at the end of this page.

## 2. See the desktop

```bash
mangouse --json desktop
```

This is the command to reach for, not `shot`. It returns outputs, windows,
which window has keyboard focus, and where the pointer is — all as data, with
no image to interpret:

```json
{
  "desktop": {
    "backend": "mango",
    "outputs": [
      {
        "name": "DP-2",
        "x": 0,
        "y": 0,
        "width": 3840,
        "height": 2160,
        "scale": 1.5
      }
    ],
    "windows": [
      {
        "id": 130,
        "app_id": "org.example.Editor",
        "title": "main.py",
        "x": 12,
        "y": 40
      }
    ],
    "focused": { "id": 130 },
    "cursor": { "x": 1840, "y": 622, "output": "DP-2" }
  }
}
```

Coordinates are global logical pixels — the same space `grim -g` uses, and the
same space `click` and `zoom` expect.

## 3. Take a screenshot

```bash
mangouse --json shot --output DP-2
```

The image is written to `$XDG_RUNTIME_DIR/mangouse/` and the envelope carries
its path plus the geometry it covers. Open the path, or hand it to an agent to
read:

```json
{
  "shot": {
    "path": "/run/user/1000/mangouse/shot-20260819-101500-5517.jpg",
    "x": 0,
    "y": 0,
    "width": 1568,
    "height": 882,
    "scale": 0.408,
    "output": "DP-2"
  }
}
```

`width`/`height`/`scale` describe the **file on disk**, already downscaled by
`--fit` (default long edge 1568). To map a pixel you found in the image back to
the desktop: `global = origin + pixel / scale`. To look closer at one spot
without a full capture, use `mangouse --json zoom X Y`.

## 4. Drive the seat (optional)

Observation needs no permission. Typing and clicking do:

```bash
mangouse --json --allow-input click 1840 622 --then shot
```

The grant is per invocation. You can make it durable with
`MANGOUSE_ALLOW_INPUT=1` or `allow_input = true` in
[the config file](configuration.md) — read
[the security model](security-model.md) before you do.

`--then shot` captures right after the click and adds `hit`: `changed` means
the pixels under the point moved, `unchanged` means nothing happened. Envelope
`ok` only means the click was delivered to the kernel, not that anything
received it — branch on `hit`.

## Use it from an agent

Two hosts sit on the same core:

- **CLI + skill.** The primary path. `skills/mangouse/SKILL.md` is a playbook
  an agent can follow; `install.sh` symlinks it into the skill roots you have.
- **MCP.** Install the `mcp` extra and register the `mangouse-mcp` stdio server
  with your MCP client. It exposes `doctor`, `desktop`, `shot`, `target`, and
  `zoom`, all read-only. There is no mutate tool on MCP and there will not be one.

Registration is client-specific; the command to register is always
`mangouse-mcp` with no arguments. mangouse never writes an agent host's config
for you.

## Troubleshooting

Find the blocker id from `doctor`:

| `blockers` contains | Meaning                                             | Fix                                                                               |
| ------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------- |
| `wayland`           | `WAYLAND_DISPLAY` is unset                          | You are not in a Wayland session, or you are in a shell that did not inherit it   |
| `backend`           | No adapter reported itself available                | Your compositor has no backend yet — see [backends/README.md](backends/README.md) |
| `backend_socket`    | The compositor's IPC socket is missing              | The compositor is not running, or this shell lacks its instance environment       |
| `backend_ipc`       | The IPC binary is not on `PATH`                     | Install it (`mmsg` for mango)                                                     |
| `backend_rpc`       | The socket exists but the compositor did not answer | Version mismatch, or a stale socket from a dead session                           |

Non-blocking checks report a problem without stopping observation:

| Check                       | `ok: false` means                                                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `bin_grim`                  | `shot` and `zoom` cannot run; `desktop` / `target` still work (`shot_ready` is false)                                          |
| `bin_wtype` / `bin_ydotool` | Keyboard or pointer input is unavailable; observation still works                                                              |
| `ydotool_socket`            | `ydotool` is installed but its daemon is not running, so clicks will fail (`click_ready` is false)                             |
| `bin_wl_paste`              | `clipboard` cannot read                                                                                                        |
| `devtools`                  | No browser protocol endpoint is connected. Expected unless you want protocol clicks — see [cli-reference.md](cli-reference.md) |

Other symptoms:

- **Every command returns `bad_config`.** Your `config.toml` is unreadable or a
  key has the wrong shape; the `message` names the key. See
  [configuration.md](configuration.md).
- **Mutate returns `readonly`.** You did not pass `--allow-input`.
- **Mutate returns `input_blocked`.** A lock client is running. This is
  deliberate and cannot be overridden.
- **`click` returns `ok` but `hit: unchanged`.** The click was delivered but
  nothing reacted. Do not retry the same coordinates — some webviews ignore
  evdev entirely. [cli-reference.md](cli-reference.md) covers the protocol
  path for those.
- **Something is hung.** `pkill -f mangouse`.
