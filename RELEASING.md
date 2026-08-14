# Releasing

1. Bump `__version__` in `src/mangouse/__init__.py`.
2. Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md`.
3. `uv run pytest` and `uv run ruff check src tests`.
4. Commit on `main`: `chore: release X.Y.Z`.
5. Tag annotated: `git tag -a vX.Y.Z -m "mangouse X.Y.Z"`.
6. `./install.sh` so the local `uv tool` matches the tag.
7. Push only when a remote exists: `git push origin main --tags`.

Do not register MCP or edit `~/.grok/config.toml` from this repo.
