# Releasing

1. Bump `__version__` in `src/mangouse/__init__.py`.
2. Add a `## [X.Y.Z] — YYYY-MM-DD` section to [`CHANGELOG.md`](../CHANGELOG.md).
3. `uv run pytest`, `uv run ruff check src tests`, and
   `uv run ruff format --check src tests` — the same three CI runs.
4. Commit on `main`: `chore: release X.Y.Z`.
5. Tag annotated: `git tag -a vX.Y.Z -m "mangouse X.Y.Z"`.
6. `./install.sh` so the local `uv tool` matches the tag.
7. `git push origin main --tags`.

`install.sh` never registers an MCP server or edits an agent host's config;
keep it that way.
