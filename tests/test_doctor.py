from __future__ import annotations

from mangouse.backends.mango import MangoBackend
from mangouse.doctor import run_doctor


def test_doctor_report_shape(backend: MangoBackend) -> None:
    report = run_doctor(backend)
    assert report["input_implemented"] is True
    assert report["backend"] == "mango"
    ids = {c["id"] for c in report["checks"]}
    assert "wayland" in ids
    assert "bin_grim" in ids
    assert "backend" in ids
    assert "devtools" in ids
    devtools = next(c for c in report["checks"] if c["id"] == "devtools")
    assert "detail" in devtools
