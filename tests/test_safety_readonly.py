from __future__ import annotations

from mangouse.errors import Readonly
from mangouse.models import Window
from mangouse.policy import is_denied
from mangouse.safety import require_input


def _window(app_id: str) -> Window:
    return Window(
        id=1,
        pid=1,
        app_id=app_id,
        title="",
        output="out",
        groups=[1],
        x=0,
        y=0,
        width=100,
        height=100,
        focused=False,
        visible=True,
    )


def test_require_input_default() -> None:
    try:
        require_input(False)
    except Readonly as exc:
        assert exc.code == "readonly"
    else:
        raise AssertionError("expected Readonly")


def test_allow_input_from_config(tmp_path, monkeypatch) -> None:
    cfg = tmp_path / "cfg.toml"
    cfg.write_text("allow_input = true\n")
    monkeypatch.setenv("MANGOUSE_CONFIG", str(cfg))
    require_input(False)


def test_deny_uses_caller_tokens_only() -> None:
    tokens = ("vault",)
    assert is_denied(_window("com.example.vault"), tokens=tokens)
    assert not is_denied(_window("term"), tokens=tokens)


def test_lock_scan_continues_past_a_slow_probe(monkeypatch) -> None:
    """One pgrep timeout must not abandon the remaining lock clients."""
    import subprocess

    from mangouse import config, safety
    from mangouse.config import Config

    monkeypatch.setattr(config, "load_config", lambda: Config(lock_procs=("slow", "reallock")))

    calls: list[str] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd[-1])
        if cmd[-1] == "slow":
            raise subprocess.TimeoutExpired(cmd, 2)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert safety.session_locked() is True
    assert calls == ["slow", "reallock"]


def test_lock_scan_gives_up_without_pgrep(monkeypatch) -> None:
    import subprocess

    from mangouse import config, safety
    from mangouse.config import Config

    monkeypatch.setattr(config, "load_config", lambda: Config(lock_procs=("swaylock",)))

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("pgrep")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert safety.session_locked() is False
