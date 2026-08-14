# mangouse — agent notes

- Comments and docs: English.
- Style: small modules, no framework. Match `nstream` (uv, hatchling, ruff, pytest).
- Tests: unit tests on recorded `tests/testdata/<backend>/*.json`. Do not require a live
  compositor for the default suite. Skip or gate anything that shells out to `grim`
  / compositor IPC unless `MANGO_INSTANCE_SIGNATURE` is set.
- Layout: `hosts/` (CLI, MCP), core modules, `backends/<name>.py`. Do not put
  compositor CLIs in hosts or core.
- Local install: `./install.sh` (`uv tool install --force --reinstall`). Do not
  `grok mcp add` from this repo.
- Never drive the live seat in CI. Input unit tests mock `wtype` / `ydotool`.
- The CLI `--json` envelope in `docs/headless.md` is the contract (`schema: 1`).
  Host playbooks must not invent fields or hard-code application names.
- Follow `docs/practices.md`. Do not add mutate tools to the MCP extra.
- Do not edit `~/.grok/config.toml`, `jarvis-shot`, or systemd units from this repo.
- Compositor IPC belongs in `mangouse.backends.<name>`. Core uses `Backend` only.
- No shipped deny list. Policy tokens come from user config.
- Do not add `hyprctl` (or any other compositor) into the core.
