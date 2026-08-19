"""Structured errors for the CLI / MCP JSON envelope."""

from __future__ import annotations


class MangouseError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NoSession(MangouseError):
    def __init__(self, message: str = "no compositor session available") -> None:
        super().__init__("no_session", message)


class MissingDep(MangouseError):
    def __init__(self, name: str) -> None:
        super().__init__("missing_dep", f"missing dependency: {name}")
        self.name = name


class Readonly(MangouseError):
    def __init__(self, message: str = "input disabled (readonly)") -> None:
        super().__init__("readonly", message)


class NotImplementedYet(MangouseError):
    def __init__(self, name: str) -> None:
        super().__init__("not_implemented", f"{name} is not implemented yet")


class UnknownWindow(MangouseError):
    def __init__(self, window_id: int) -> None:
        super().__init__("unknown_window", f"window {window_id} not found")
        self.window_id = window_id



class GrimFailed(MangouseError):
    def __init__(self, detail: str) -> None:
        super().__init__("grim_failed", detail)


class IpcFailed(MangouseError):
    def __init__(self, detail: str) -> None:
        super().__init__("ipc_failed", detail)


class Denied(MangouseError):
    def __init__(self, detail: str) -> None:
        super().__init__("denied", detail)


class InputBlocked(MangouseError):
    def __init__(self, detail: str) -> None:
        super().__init__("input_blocked", detail)


class BadKey(MangouseError):
    def __init__(self, combo: str, reason: str | None = None) -> None:
        super().__init__(
            "bad_key",
            reason or f"compositor binds must use dispatch, not key ({combo})",
        )


class BadConfig(MangouseError):
    """config.toml is unreadable or holds a value of the wrong shape."""

    def __init__(self, detail: str) -> None:
        super().__init__("bad_config", detail)


class BadArg(MangouseError):
    """Caller passed a value the seat cannot map. Not a missing dependency."""

    def __init__(self, detail: str) -> None:
        super().__init__("bad_arg", detail)
