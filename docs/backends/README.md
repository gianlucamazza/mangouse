# Backends

A backend is the only place in mangouse that knows how one compositor talks.
Everything above it — the core, the CLI, the MCP server, the skill — sees the
same `Backend` protocol and the same generic model types.

[mango.md](mango.md) documents the first adapter and is the worked example to
read alongside this page.

## What a backend must provide

Implement the protocol in `src/mangouse/backend.py`:

| Method                    | Returns                                                                 |
| ------------------------- | ----------------------------------------------------------------------- |
| `available()`             | Is this compositor reachable right now? Used by `backend = "auto"`      |
| `checks()`                | Doctor rows specific to this compositor (socket, IPC binary, RPC reply) |
| `version()`               | The compositor's version string                                         |
| `desktop()`               | The whole snapshot: outputs, windows, focus, cursor                     |
| `outputs()` / `windows()` | The pieces, for callers that need only one                              |
| `window(id)`              | One window, or raise `UnknownWindow`                                    |
| `focusing()`              | The window with keyboard focus, or `None`                               |
| `cursor()`                | Pointer position, or `None` if the compositor cannot report it          |
| `focus_window(id)`        | Give a window keyboard focus                                            |
| `dispatch_action(spec)`   | Pass an opaque string to the compositor                                 |

`name` is a class attribute and becomes the `backend` field in every envelope.

## Rules

**All compositor IPC stays here.** The core and the hosts may not name your
binary, your socket, or your protocol. `tests/test_layout.py` enforces this by
scanning shipped modules for banned tokens — add yours to `_BANNED` when you
add the backend, so the boundary is checked and not merely intended.

**Map to the generic vocabulary, do not leak yours.** Whatever your compositor
calls a grouping — tags, workspaces, desktops — it becomes `groups` and
`active_groups`. Coordinates become global logical pixels, the same space
`grim -g` uses. Anything genuinely compositor-specific that a host might still
want goes in `extras`, which nothing is allowed to depend on.

**`dispatch_action` does not parse.** It hands the string through. Compositor
bindings are the user's business, not a syntax mangouse validates.

**Fail with structured errors.** `IpcFailed` when the compositor does not
answer, `UnknownWindow` for a missing id. Never let a transport exception reach
the host — the envelope is the contract.

## Adding one

1. Write `src/mangouse/backends/<name>.py`.
2. Register it in `session.REGISTRY`.
3. Record real IPC responses into `tests/testdata/<name>/*.json`. The default
   suite must pass with no compositor running, so fixtures are not optional.
4. Add a test module that parses those fixtures into the model types.
5. Add your IPC binary to `_BANNED` in `tests/test_layout.py`.
6. Document the mapping in `docs/backends/<name>.md`, following
   [mango.md](mango.md): which IPC calls you make, how fields map, and which
   coordinate space you return.

Auto-detection picks the first registered backend whose `available()` is true.
Users can always force one with `--backend NAME`, `MANGOUSE_BACKEND`, or
`backend` in [the config file](../configuration.md).
