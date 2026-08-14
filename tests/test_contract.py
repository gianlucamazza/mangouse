from __future__ import annotations

import json

from mangouse.contract import SCHEMA, envelope
from mangouse.hosts.cli import main
from mangouse.screen import fit_scale


def test_envelope_has_schema() -> None:
    payload = envelope(ok=True, action="doctor", data={"ready": False})
    assert payload["schema"] == SCHEMA
    assert payload["ok"] is True
    assert payload["action"] == "doctor"
    assert payload["ready"] is False


def test_cli_json_includes_schema(capsys) -> None:
    rc = main(["--json", "type", "hello"])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == SCHEMA
    assert payload["error"] == "readonly"


def test_fit_scale_no_op() -> None:
    factor, w, h = fit_scale(800, 600, 1568)
    assert factor == 1.0
    assert (w, h) == (800, 600)


def test_fit_scale_shrinks_and_preserves_ratio() -> None:
    factor, w, h = fit_scale(1920, 1200, 1568)
    assert factor == 1568 / 1920
    assert w == 1568
    assert h == round(1200 * factor)


def test_fit_disabled() -> None:
    factor, w, h = fit_scale(1920, 1200, 0)
    assert factor == 1.0
    assert (w, h) == (1920, 1200)
