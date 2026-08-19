# Safety

mangouse can see the screen and, with a seat grant, share the seat.
Treat an input-enabled session like screen sharing.

## What the core enforces

- **Readonly default.** Mutate refuses with `readonly` unless `--allow-input`,
  `MANGOUSE_ALLOW_INPUT=1`, or `allow_input = true` in config.
- **Policy.** User `deny_app_ids` / `confine_*` → `denied`. Lock screen →
  `input_blocked`. Super/logo key combos → `bad_key`.
- **stdio only.** No TCP listen, no telemetry. The optional DevTools
  holder binds a user-only unix socket (0600) under
  `$XDG_RUNTIME_DIR/mangouse/`; `devtools --stop` removes it.
- **Shots** in `$XDG_RUNTIME_DIR/mangouse/` (tmpfs, 0700).
- **MCP** is observe-only (`doctor`, `desktop`, `shot`, `target`).

## What the core does not enforce

No shipped application deny list. No Grok/Claude/Codex special cases.
If you want to block targeting some `app_id` values, put them in config:

```toml
[policy]
deny_app_ids = ["example-vault"]
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
