# AGENTS.md

Notes for coding agents working **on** this repository. To _use_ mangouse to
drive a desktop, read `skills/mangouse/SKILL.md` instead.

## Read first

- [CONTRIBUTING.md](CONTRIBUTING.md) — dev loop, test suite, layout rules,
  commit convention. Everything below is a summary of it.
- [docs/json-contract.md](docs/json-contract.md) — the `--json` envelope is the
  contract (`schema: 1`). Do not invent fields.
- [docs/architecture.md](docs/architecture.md) — the two invariants and why
  they exist.

## Hard rules

- Compositor IPC lives in `src/mangouse/backends/<name>.py`. The core and the
  hosts use the `Backend` protocol and never name a compositor binary.
- No application names, host names, or user-specific paths in shipped code.
  Policy tokens come from user config; the library ships an empty deny list.
- MCP stays observe-only. Do not add a mutate tool to it.
- Errors are `MangouseError` subclasses with a stable `code`. A new code needs
  a row in `docs/json-contract.md`, or `tests/test_docs_alignment.py` fails.
- The default test suite is hermetic: recorded fixtures, mocked `wtype` and
  `ydotool`, no live compositor, no live browser, no real seat. Gate anything
  else on `MANGO_INSTANCE_SIGNATURE`.
- Comments and documentation in English.

## Docs are tested

`tests/test_docs_alignment.py` compares the documentation to the code — parser
flags, error codes, MCP tools, `doctor` keys, environment variables, relative
links, and stray version strings. A change to the surface that skips the docs
will fail, by design.
