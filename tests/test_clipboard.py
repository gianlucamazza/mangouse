from __future__ import annotations

from mangouse.clipboard import read_clipboard
from mangouse.errors import Denied


def test_clipboard_denied_by_default() -> None:
    try:
        read_clipboard(allow=False)
    except Denied as exc:
        assert exc.code == "denied"
        return
    raise AssertionError("expected Denied")


def test_clipboard_reads_via_runner() -> None:
    def runner(cmd: list[str]) -> bytes:
        assert cmd[-1] == "text"
        return b"hello"

    out = read_clipboard(allow=True, runner=runner)
    assert out["text"] == "hello"
    assert out["bytes"] == 5
    assert out["mime"] == "text/plain"
