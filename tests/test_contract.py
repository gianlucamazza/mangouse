from __future__ import annotations

import json

from mangouse.contract import SCHEMA
from mangouse.hosts.cli import main
from mangouse.screen import fit_scale


def test_cli_json_includes_schema(capsys) -> None:
    rc = main(["--json", "type", "hello"])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == SCHEMA
    assert payload["error"] == "readonly"


def test_fit_scale_shrinks_and_preserves_ratio() -> None:
    factor, w, h = fit_scale(1920, 1200, 1568)
    assert factor == 1568 / 1920
    assert w == 1568
    assert h == round(1200 * factor)


def test_fit_disabled() -> None:
    factor, w, h = fit_scale(1920, 1200, 0)
    assert factor == 1.0
    assert (w, h) == (1920, 1200)
