<!-- User-visible change? Add a CHANGELOG.md heading. Surface change
     (flag, error code, MCP tool, doctor key)? The docs-alignment test
     will fail until the docs match. -->

- [ ] `uv run pytest`
- [ ] `uv run ruff check src tests`
- [ ] `uv run ruff format --check src tests`
- [ ] `uv run ty check src`
