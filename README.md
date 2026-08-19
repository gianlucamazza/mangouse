# mangouse

[![CI](https://github.com/gianlucamazza/mangouse/actions/workflows/ci.yml/badge.svg)](https://github.com/gianlucamazza/mangouse/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](pyproject.toml)

**Coding agents have no native computer use on a Linux Wayland seat.** The
servers that exist are bound to one compositor, one agent host, or a hardcoded
list of applications. mangouse is a seat adapter instead: it answers _what is
on this desktop_ as structured JSON, and — only with an explicit grant — types,
clicks, and focuses on the same seat you are using.

It observes by default. Mutation needs `--allow-input`. The optional MCP server
is observe-only and cannot be talked into typing.

```console
$ mangouse --json desktop | jq '.desktop.focused.app_id, .desktop.cursor'
"org.example.Editor"
{ "x": 1840, "y": 622, "output": "DP-2" }
```

## Requirements

- A Wayland session (`WAYLAND_DISPLAY` set) and a supported compositor
- Python 3.13+
- One backend's IPC binary — today [MangoWM](docs/backends/mango.md)'s `mmsg`

| Binary     | Needed for          | Required                            |
| ---------- | ------------------- | ----------------------------------- |
| `grim`     | `shot`, `zoom`      | yes                                 |
| `mmsg`     | the mango backend   | yes, for that backend               |
| `wtype`    | `type`, `key`       | only with a seat grant              |
| `ydotool`  | `click`             | only with a seat grant              |
| `wl-paste` | `clipboard`         | only when clipboard read is enabled |
| `magick`   | `--fit` downscaling | optional                            |

`mangouse --json doctor` probes every one of them and names what is missing.
The Python core itself has **zero** dependencies.

## Install

```bash
uv tool install "mangouse[mcp] @ git+https://github.com/gianlucamazza/mangouse"
mangouse --json doctor
```

Drop `[mcp]` if you do not want the optional MCP server. To work on the code
instead, clone it and use the repo's installer, which also links the agent
skill into any skill root you already have:

```bash
git clone https://github.com/gianlucamazza/mangouse
cd mangouse
./install.sh
```

`install.sh` is idempotent. It runs `uv tool install --force --reinstall`,
creates `~/.config/mangouse/config.toml` only if absent, and symlinks
`skills/mangouse/SKILL.md` into `~/.claude/skills`, `~/.grok/skills`, and
`~/.agents/skills` — only into roots that already exist. It never registers an
MCP server for you and never edits an agent host's config.

To remove it: `uv tool uninstall mangouse`, then delete
`~/.config/mangouse/`, `$XDG_RUNTIME_DIR/mangouse/`, and the `mangouse` skill
symlink from whichever skill roots you have.

## Quickstart

[docs/quickstart.md](docs/quickstart.md) walks from `doctor` to your first
screenshot, and lists what to do when `doctor` reports a blocker.

## Safety

mangouse can see every pixel on an output and, with a grant, share your
keyboard and pointer. Treat an input-enabled session like screen sharing.
Observation is the default; `--allow-input` is per-invocation; a running lock
screen refuses input outright. The full model is in
[docs/security-model.md](docs/security-model.md), and reporting is in
[SECURITY.md](SECURITY.md).

## Documentation

| Doc                                      | For                                                    |
| ---------------------------------------- | ------------------------------------------------------ |
| [Quickstart](docs/quickstart.md)         | First run and troubleshooting                          |
| [CLI reference](docs/cli-reference.md)   | Every command, flag, and the MCP surface               |
| [JSON contract](docs/json-contract.md)   | Envelope, error codes, rules — authoritative for hosts |
| [Configuration](docs/configuration.md)   | `config.toml` keys and environment variables           |
| [Security model](docs/security-model.md) | What the core enforces, and what it does not           |
| [Architecture](docs/architecture.md)     | Layers, glossary, non-goals                            |
| [Backends](docs/backends/README.md)      | Writing an adapter for another compositor              |
| [Contributing](CONTRIBUTING.md)          | Dev loop, tests, layout rules                          |
| [Changelog](CHANGELOG.md)                | Version history                                        |

## License

MIT — see [LICENSE](LICENSE).
