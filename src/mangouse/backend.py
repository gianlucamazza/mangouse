"""Desktop backend protocol. Core never imports a compositor by name."""

from __future__ import annotations

from typing import Protocol

from mangouse.models import Check, Cursor, Desktop, Output, Window


class Backend(Protocol):
    name: str

    def available(self) -> bool:
        """True when this compositor session is reachable."""

    def checks(self) -> list[Check]:
        """Backend-specific doctor rows (socket, ipc binary, …)."""

    def version(self) -> str: ...

    def desktop(self) -> Desktop: ...

    def outputs(self) -> list[Output]: ...

    def windows(self) -> list[Window]: ...

    def window(self, window_id: int) -> Window: ...

    def focusing(self) -> Window | None: ...

    def cursor(self) -> Cursor | None: ...

    def focus_window(self, window_id: int) -> None: ...

    def dispatch_action(self, spec: str) -> object: ...
