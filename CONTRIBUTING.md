# Contributing

Thanks for looking. mangouse is small on purpose — a stdlib-only core, one
adapter per compositor, and two thin hosts — so most changes are small too.

## Dev loop

```bash
git clone https://github.com/gianlucamazza/mangouse
cd mangouse
uv sync --group dev

uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run ty check src
uv run mangouse --json doctor
```

`./install.sh` deploys the checkout as a `uv` tool when you want to try it
against a live desktop. It is idempotent and safe to re-run.

## Tests

The default suite is hermetic. It runs on recorded fixtures in
`tests/testdata/<backend>/`, mocks `wtype` and `ydotool`, and never touches a
live compositor, a live browser, or your seat. Keep it that way — a test that
opens the developer's browser is a bug, not a stronger test.

Anything that needs a real compositor is gated on `MANGO_INSTANCE_SIGNATURE`.

Two groups deserve a note because they fail in ways that look unrelated to what
you changed:

- **`tests/test_layout.py`** enforces the architectural boundaries: no
  compositor IPC binary named outside `backends/`, no application or host names
  anywhere in shipped code. A failure here means the change leaked across a
  layer, not that the test is fussy.
- **`tests/test_docs_alignment.py`** compares the docs to the code:
  every parser flag against `docs/cli-reference.md`, every error code in
  `errors.py` against the table in `docs/json-contract.md`, the `@server.tool`
  set against every file that lists the MCP tools, and `run_doctor()`'s keys
  against the documented `doctor` row. **Adding a flag, an error code, or an
  MCP tool will fail CI until you document it.** That is deliberate: the docs
  drifted badly once, and the tests exist so it stays expensive to repeat.

## Layout rules

- `src/mangouse/hosts/` — CLI and MCP. Thin. They format envelopes; they do not
  contain logic.
- `src/mangouse/` — the compositor-agnostic core. Zero third-party
  dependencies. Knows windows, outputs, groups, cursors, shots. Does not know
  application names, agent hosts, or compositor jargon.
- `src/mangouse/backends/<name>.py` — one module per compositor, registered in
  `session.REGISTRY`. All IPC lives here. See
  [docs/backends/README.md](docs/backends/README.md).

The core ships no application deny list. Policy tokens come from the user's
config, always.

Do not add mutate tools to the MCP extra. MCP is observe-only, by design.

## Style

- Code, comments, and docs in English.
- Small modules, no framework. `ruff` with the repo's settings is the
  formatter and the linter; line length is 100. `ty` type-checks `src/`.
- Type hints on public functions. `from __future__ import annotations` at the
  top of every module.
- Errors are `MangouseError` subclasses with a stable `code`, because agents
  branch on `error`, not on `message`. A new code needs a row in
  `docs/json-contract.md` — the test will remind you.

## Commits and pull requests

Commit subjects follow [Conventional Commits](https://www.conventionalcommits.org):
`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`. Write the body in
prose explaining _why_, not a bullet list of what the diff already shows.

Before opening a PR: `uv run pytest`, `uv run ruff check src tests`,
`uv run ruff format --check src tests`, and `uv run ty check src` all
clean, and a `CHANGELOG.md` entry under a new heading if the change is
user-visible.

Releases are a separate, maintainer-only process:
[docs/releasing.md](docs/releasing.md).

## Reporting a security issue

Do not open a public issue. See [SECURITY.md](SECURITY.md).
