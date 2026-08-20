from __future__ import annotations

import shutil

from mangouse.backends.mango import MangoBackend
from mangouse.doctor import run_doctor


def test_doctor_report_shape(backend: MangoBackend) -> None:
    report = run_doctor(backend)
    assert report["input_implemented"] is True
    assert report["backend"] == "mango"
    assert "shot_ready" in report
    assert "click_ready" in report
    ids = {c["id"] for c in report["checks"]}
    assert "wayland" in ids
    assert "bin_grim" in ids
    assert "backend" in ids
    assert "devtools" in ids
    devtools = next(c for c in report["checks"] if c["id"] == "devtools")
    assert "detail" in devtools


def test_missing_grim_is_not_an_observe_blocker(backend: MangoBackend, monkeypatch) -> None:
    real = shutil.which

    monkeypatch.setattr(
        shutil, "which", lambda name, *a, **kw: None if name == "grim" else real(name)
    )
    report = run_doctor(backend)
    grim = next(c for c in report["checks"] if c["id"] == "bin_grim")
    assert grim["ok"] is False
    assert grim["blocker"] is False
    assert "bin_grim" not in report["blockers"]
    assert report["shot_ready"] is False


def test_doctor_ydotool_socket_honours_env(backend: MangoBackend, tmp_path, monkeypatch) -> None:
    sock = tmp_path / "custom.sock"
    sock.touch()
    monkeypatch.setenv("YDOTOOL_SOCKET", str(sock))
    report = run_doctor(backend)
    row = next(c for c in report["checks"] if c["id"] == "ydotool_socket")
    assert row["ok"] is True
    assert str(sock) in row["detail"]
