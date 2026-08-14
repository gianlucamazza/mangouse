from __future__ import annotations

from mangouse.backends.mango import MangoBackend
from mangouse.doctor import run_doctor
from mangouse.hosts.cli import main


def test_doctor_report_shape(backend: MangoBackend) -> None:
    report = run_doctor(backend)
    assert "ready" in report
    assert "checks" in report
    assert "blockers" in report
    assert report["input_implemented"] is True
    assert report["backend"] == "mango"
    ids = {c["id"] for c in report["checks"]}
    assert "wayland" in ids
    assert "bin_grim" in ids
    assert "backend" in ids
    assert "1password" not in str(report).lower()


def test_doctor_json_cli() -> None:
    rc = main(["--json", "doctor"])
    assert rc == 0
