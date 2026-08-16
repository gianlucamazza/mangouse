from __future__ import annotations

import json
from pathlib import Path

import pytest

from mangouse.backends.mango import MangoBackend


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Unit tests must not pick up the user's allow_input seat grant."""
    monkeypatch.setenv("MANGOUSE_CONFIG", str(tmp_path / "mangouse-test.toml"))
    monkeypatch.delenv("MANGOUSE_ALLOW_INPUT", raising=False)


FIXTURES = Path(__file__).parent / "testdata" / "mango"


def fixture_runner(args: list[str]) -> str:
    key = " ".join(args)
    mapping = {
        "get version": "version.json",
        "get all-clients": "all-clients.json",
        "get all-monitors": "all-monitors.json",
        "get focusing-client": "focusing-client.json",
        "get cursorpos": "cursorpos.json",
    }
    if key.startswith("get client "):
        cid = int(key.rsplit(" ", 1)[1])
        clients = json.loads((FIXTURES / "all-clients.json").read_text())["clients"]
        for item in clients:
            if item["id"] == cid:
                return json.dumps(item)
        return json.dumps({"error": f"unknown client {cid}"})
    name = mapping.get(key)
    if not name:
        return json.dumps({"error": f"unknown command: {key}"})
    return (FIXTURES / name).read_text()


@pytest.fixture
def backend() -> MangoBackend:
    return MangoBackend(runner=fixture_runner)
