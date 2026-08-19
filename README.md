# mangouse

Seat adapter for coding agents: observe and (with a seat grant) drive a
Wayland desktop. MangoWM is the first compositor backend.

The core is **not** an app catalog and **not** a Grok plugin. MangoWM is the
first compositor backend (`mangouse.backends.mango`). Hosts (CLI, MCP, skills)
sit above the same `--json` contract.

Not a browser agent. Not hypruse. Not a port of `hyprland_agent`.

## Status

v1. Observe always; mutate only with `--allow-input`. MCP stays observe-only.

## Install (local)

```bash
cd ~/Workspace/tooling/mangouse
./install.sh
mangouse --json doctor
```

`install.sh` (idempotent, same pattern as nstream):

- `uv tool install --force --reinstall .[mcp]` → `~/.local/bin/mangouse`
  and `mangouse-mcp` (the `mcp` extra; the core itself has no dependencies)
- creates `~/.config/mangouse/config.toml` only if missing
- symlinks the skill into `~/.claude/skills`, `~/.grok/skills`, and
  `~/.agents/skills` — only into roots that already exist
- does **not** register MCP or edit `~/.grok/config.toml`

Dev loop without installing:

```bash
uv sync --group dev
uv run mangouse --json doctor
```

System binaries: `grim` (required for `shot`), `mmsg` (mango backend).
Needed only for the opt-in paths: `wtype` (`type`/`key`), `ydotool`
(`click`), `wl-paste` (`clipboard`). Optional: `magick` (`--fit`).
`mangouse --json doctor` probes all of them.

## Agent contract

Always pass `--json`. The envelope and error codes live in [`docs/headless.md`](docs/headless.md).
The Grok playbook is [`skills/mangouse/SKILL.md`](skills/mangouse/SKILL.md).

```bash
uv run mangouse --json desktop
uv run mangouse --json shot --output NAME
```

Grok Build (this machine): skill is linked; MCP is `mangouse-mcp` in
`~/.grok/config.toml`. Observe-only tools: `doctor`, `desktop`, `shot`,
`target`. Permission allow is scoped to
`mangouse --json doctor|desktop|shot|target` and
`MCPTool(mangouse__*)`. Restart the TUI after a reinstall.

To register MCP on another box (after `./install.sh`):

```bash
grok mcp add mangouse -- mangouse-mcp
```

## Docs

| File | What |
|------|------|
| [docs/practices.md](docs/practices.md) | Normative best practices |
| [docs/design.md](docs/design.md) | Layers, agnostic core, v0/v1 |
| [docs/config.md](docs/config.md) | Optional backend + policy file |
| [docs/README.md](docs/README.md) | Doc index |
| [docs/backends/mango.md](docs/backends/mango.md) | Mango adapter mapping |
| [docs/tools.md](docs/tools.md) | CLI / MCP surface |
| [docs/headless.md](docs/headless.md) | `--json` contract |
| [docs/safety.md](docs/safety.md) | Seat gates; user policy |

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Current version: **0.7.0**.

## Panic

```bash
pkill -f mangouse
```

Stops a hung `shot` / input / MCP process.
