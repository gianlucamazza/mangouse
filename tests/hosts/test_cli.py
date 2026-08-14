from __future__ import annotations

from mangouse.hosts.cli import main


def test_help_exits_zero() -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0


def test_version() -> None:
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
