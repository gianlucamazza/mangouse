"""mangouse CLI. --json is the agent contract (see docs/headless.md)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from mangouse import __version__
from mangouse import input as input_mod
from mangouse.contract import DEFAULT_FIT
from mangouse.contract import envelope as _envelope
from mangouse.errors import MangouseError
from mangouse.models import to_dict
from mangouse.session import resolve_backend


def _then_window_id(args: argparse.Namespace) -> int | None:
    if getattr(args, "window", None) is not None:
        return int(args.window)
    if getattr(args, "window_id", None) is not None:
        return int(args.window_id)
    return None


def _attach_then(
    payload: dict[str, Any],
    args: argparse.Namespace,
    *,
    at: tuple[float, float] | None = None,
    backend: Any = None,
) -> dict[str, Any]:
    then = getattr(args, "then", "none") or "none"
    if then == "none":
        return payload
    if backend is None:
        backend = resolve_backend(args.backend)
    if then == "desktop":
        payload["desktop"] = to_dict(backend.desktop())
    elif then == "shot":
        from mangouse.screen import capture, then_capture_kwargs

        kwargs = then_capture_kwargs(
            window_id=_then_window_id(args),
            at=at,
            outputs=backend.outputs(),
        )
        payload["shot"] = to_dict(
            capture(
                backend,
                lossless=False,
                fit=getattr(args, "fit", DEFAULT_FIT),
                **kwargs,
            )
        )
    return payload


def _print(payload: dict[str, Any], *, as_json: bool, human: str | None = None) -> int:
    if as_json:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif human is not None:
        sys.stdout.write(human)
        if not human.endswith("\n"):
            sys.stdout.write("\n")
    else:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0 if payload.get("ok") else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    from mangouse.doctor import run_doctor

    report = run_doctor(name=args.backend)
    payload = _envelope(ok=True, action="doctor", data=report)
    lines = [
        f"ready={report['ready']} observe={report['observe_ready']} "
        f"input_implemented={report['input_implemented']}",
    ]
    if report["blockers"]:
        lines.append("blockers: " + ", ".join(report["blockers"]))
    for check in report["checks"]:
        mark = "ok" if check["ok"] else "FAIL"
        lines.append(f"  {check['id']}: {mark}  {check['detail']}")
    return _print(payload, as_json=args.json, human="\n".join(lines) + "\n")


def cmd_desktop(args: argparse.Namespace) -> int:
    desktop = resolve_backend(args.backend).desktop()
    payload = _envelope(ok=True, action="desktop", data={"desktop": to_dict(desktop)})
    lines = [f"{desktop.backend} {desktop.version}  windows={len(desktop.windows)}"]
    for item in desktop.outputs:
        star = "*" if item.active else " "
        geom = f"{item.width}x{item.height}@{item.scale}"
        lines.append(f"{star} {item.name} {geom} groups={item.active_groups}")
    for window in desktop.windows:
        mark = ">" if window.focused else " "
        vis = "vis" if window.visible else "hid"
        title = window.title[:60]
        geom = f"{window.width}x{window.height}"
        lines.append(f"{mark} #{window.id} {window.app_id:24} {vis} {geom}  {title}")
    return _print(payload, as_json=args.json, human="\n".join(lines) + "\n")


def cmd_shot(args: argparse.Namespace) -> int:
    from mangouse.screen import capture

    shot = capture(
        resolve_backend(args.backend),
        output=args.output,
        window_id=args.window,
        full=args.full,
        lossless=args.lossless,
        fit=args.fit,
    )
    payload = _envelope(ok=True, action="shot", data={"shot": to_dict(shot)})
    return _print(payload, as_json=args.json, human=shot.path + "\n")


def cmd_focus(args: argparse.Namespace) -> int:
    data = input_mod.focus(args.window_id, allow_input=args.allow_input)
    payload = _attach_then(_envelope(ok=True, action="focus", data=data), args)
    return _print(payload, as_json=args.json, human=f"focused {args.window_id}\n")


def cmd_type(args: argparse.Namespace) -> int:
    data = input_mod.type_text(args.text, allow_input=args.allow_input, window_id=args.window)
    payload = _attach_then(_envelope(ok=True, action="type", data=data), args)
    return _print(payload, as_json=args.json, human=f"typed {data['typed']} chars\n")


def cmd_key(args: argparse.Namespace) -> int:
    data = input_mod.press_key(args.combo, allow_input=args.allow_input, window_id=args.window)
    payload = _attach_then(_envelope(ok=True, action="key", data=data), args)
    return _print(payload, as_json=args.json, human=f"key {args.combo}\n")


def cmd_click(args: argparse.Namespace) -> int:
    before: str | None = None
    backend = None
    # One backend for the whole command: each resolve re-reads config and
    # re-shells the compositor IPC.
    if getattr(args, "then", "none") != "none":
        backend = resolve_backend(args.backend)
    if getattr(args, "then", "none") == "shot":
        from mangouse.screen import region_digest

        before = region_digest(backend, args.x, args.y)
    data = input_mod.click(
        args.x,
        args.y,
        button=args.button,
        allow_input=args.allow_input,
        window_id=args.window,
        backend=backend,
    )
    payload = _attach_then(
        _envelope(ok=True, action="click", data=data),
        args,
        at=(args.x, args.y),
        backend=backend,
    )
    if getattr(args, "then", "none") == "shot":
        from mangouse.screen import classify_hit, region_digest

        after = region_digest(backend, args.x, args.y)
        payload["hit"] = classify_hit(before, after)
    human = f"click {args.button} {int(args.x)},{int(args.y)}\n"
    return _print(payload, as_json=args.json, human=human)


def cmd_dispatch(args: argparse.Namespace) -> int:
    data = input_mod.dispatch(args.spec, allow_input=args.allow_input)
    payload = _attach_then(_envelope(ok=True, action="dispatch", data=data), args)
    return _print(payload, as_json=args.json, human=f"dispatch {args.spec}\n")


def cmd_zoom(args: argparse.Namespace) -> int:
    from mangouse.screen import zoom

    shot = zoom(
        resolve_backend(args.backend),
        args.x,
        args.y,
        size=args.size,
        lossless=args.lossless,
        fit=args.fit,
    )
    payload = _envelope(ok=True, action="zoom", data={"shot": to_dict(shot)})
    return _print(payload, as_json=args.json, human=shot.path + "\n")


def cmd_target(args: argparse.Namespace) -> int:
    from mangouse.screen import target_snapshot

    data = target_snapshot(resolve_backend(args.backend))
    payload = _envelope(ok=True, action="target", data=data)
    kb = (data.get("keyboard") or {}).get("id")
    pt = (data.get("pointer") or {}).get("id")
    return _print(payload, as_json=args.json, human=f"keyboard={kb} pointer={pt}\n")


def cmd_clipboard(args: argparse.Namespace) -> int:
    from mangouse.clipboard import read_clipboard

    data = read_clipboard(allow=bool(getattr(args, "allow_clipboard", False)))
    payload = _envelope(ok=True, action="clipboard", data=data)
    return _print(payload, as_json=args.json, human=str(data.get("text") or ""))


def cmd_devtools(args: argparse.Namespace) -> int:
    from mangouse import devtools_hold
    from mangouse.devtools import probe

    if getattr(args, "stop", False):
        stopped = devtools_hold.stop()
        payload = _envelope(ok=True, action="devtools", data={"stopped": stopped, "holder": False})
        return _print(payload, as_json=args.json, human="devtools holder stopped\n")
    if getattr(args, "hold", False):
        return devtools_hold.run_holder()

    data = probe()
    # probe.ok must not overwrite envelope ok (schema: command health ≠ endpoint).
    payload = _envelope(
        ok=True,
        action="devtools",
        data={k: v for k, v in data.items() if k != "ok"},
    )
    human = (
        f"devtools state={data.get('state')} via={data.get('via')} "
        f"pages={data.get('pages')} url={data.get('url')}\n"
    )
    return _print(payload, as_json=args.json, human=human)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mangouse",
        description="Observe (and later drive) a Wayland desktop. Backends are pluggable.",
    )
    p.add_argument("--json", action="store_true", help="machine-readable envelope")
    p.add_argument(
        "--backend",
        default=None,
        help="force a backend (default: auto-detect; only 'mango' is shipped)",
    )
    p.add_argument(
        "--allow-input",
        action="store_true",
        help="allow mutating commands (type/key/click/focus/dispatch)",
    )
    p.add_argument(
        "--allow-clipboard",
        action="store_true",
        help="allow reading the seat clipboard (opt-in; often holds secrets)",
    )
    p.add_argument("--version", action="version", version=f"mangouse {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="session and dependency readiness").set_defaults(func=cmd_doctor)
    sub.add_parser("desktop", help="semantic snapshot of outputs and windows").set_defaults(
        func=cmd_desktop
    )

    shot = sub.add_parser("shot", help="capture via grim; prints the image path")
    shot.add_argument("--output", "--monitor", dest="output", help="output name")
    shot.add_argument("--window", type=int, metavar="ID", help="window id from desktop")
    shot.add_argument("--full", action="store_true", help="all outputs in one image")
    shot.add_argument("--lossless", action="store_true", help="PNG instead of JPEG q90")
    shot.add_argument(
        "--fit",
        type=int,
        default=DEFAULT_FIT,
        metavar="PX",
        help=f"cap long edge in pixels (default {DEFAULT_FIT}; 0 disables)",
    )
    shot.set_defaults(func=cmd_shot)

    then = dict(
        default="none",
        choices=("none", "desktop", "shot"),
        help="attach a fresh desktop or shot after the action",
    )

    focus = sub.add_parser("focus", help="focus a window by id")
    focus.add_argument("window_id", type=int)
    focus.add_argument("--then", **then)
    focus.set_defaults(func=cmd_focus)

    typ = sub.add_parser("type", help="type unicode text into the focused window")
    typ.add_argument("text")
    typ.add_argument("--window", type=int, help="focus this window first")
    typ.add_argument("--then", **then)
    typ.set_defaults(func=cmd_type)

    key = sub.add_parser("key", help="press a combo such as ctrl+c (not Super+)")
    key.add_argument("combo")
    key.add_argument("--window", type=int, help="focus this window first")
    key.add_argument("--then", **then)
    key.set_defaults(func=cmd_key)

    click = sub.add_parser("click", help="click at global logical coordinates")
    click.add_argument("x", type=float)
    click.add_argument("y", type=float)
    click.add_argument("--button", choices=("left", "right", "middle"), default="left")
    click.add_argument("--window", type=int, help="focus this window first")
    click.add_argument("--then", **then)
    click.set_defaults(func=cmd_click)

    disp = sub.add_parser("dispatch", help="backend-specific compositor action")
    disp.add_argument("spec", help="opaque string the active backend understands")
    disp.add_argument("--then", **then)
    disp.set_defaults(func=cmd_dispatch)

    zm = sub.add_parser("zoom", help="native-resolution crop around a global point")
    zm.add_argument("x", type=float)
    zm.add_argument("y", type=float)
    zm.add_argument("--size", type=int, default=400)
    zm.add_argument("--lossless", action="store_true")
    zm.add_argument("--fit", type=int, default=DEFAULT_FIT)
    zm.set_defaults(func=cmd_zoom)

    sub.add_parser(
        "target",
        help="who receives keys vs who is under the pointer",
    ).set_defaults(func=cmd_target)

    sub.add_parser(
        "clipboard",
        help="read text/plain from the seat clipboard (requires --allow-clipboard)",
    ).set_defaults(func=cmd_clipboard)

    dt = sub.add_parser(
        "devtools",
        help="probe an optional DevTools Protocol endpoint (observe)",
    )
    dt.add_argument(
        "--hold",
        action="store_true",
        help="keep one engine client (Allow once); CLI commands reuse it",
    )
    dt.add_argument(
        "--stop",
        action="store_true",
        help="stop the local protocol holder",
    )
    dt.set_defaults(func=cmd_devtools)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    as_json = bool(getattr(args, "json", False))
    try:
        return args.func(args)
    except MangouseError as exc:
        payload = _envelope(ok=False, action=args.cmd, error=exc.code, message=exc.message)
        rc = (
            2
            if exc.code
            in {
                "readonly",
                "not_implemented",
                "denied",
                "input_blocked",
                "bad_key",
                "bad_arg",
            }
            else 1
        )
        if as_json:
            json.dump(payload, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            sys.stderr.write(f"mangouse: {exc.code}: {exc.message}\n")
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
