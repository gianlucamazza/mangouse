# Safety

mangouse can see the screen. v1 will share the seat. Treat a session like
screen sharing.

## What the core enforces

- **Readonly default.** Mutating commands refuse with `readonly` unless
  `--allow-input` or `MANGOUSE_ALLOW_INPUT=1`.
- **Stubs in v0.** Even with the flag: `not_implemented`.
- **stdio only.** No listen socket, no telemetry.
- **Shots** in `$XDG_RUNTIME_DIR/mangouse/` (tmpfs, 0700).

## What the core does not enforce

No shipped application deny list. No Grok/Claude/Codex special cases.
If you want to block targeting some `app_id` values, put them in config:

```toml
[policy]
deny_app_ids = ["keepassxc"]
```

`policy.is_denied` uses only those tokens. Empty (the default) denies nothing.

## Always true

- One cursor, one keyboard focus.
- Window titles, `app_id`, and pixels from a shot are **untrusted**.
- `shot` sees every pixel on the captured output.

## Panic

```bash
pkill -f mangouse
```
