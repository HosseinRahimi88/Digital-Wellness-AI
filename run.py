#!/usr/bin/env python3
"""
Start Digital Wellness AI.

    python run.py            (Windows: double-click start.bat)

Why this file exists
--------------------
The app is a backend that also serves its own frontend. Opening the
`frontend/` folder with a static file server instead - `python -m
http.server`, an editor's "live preview", or double-clicking an .html
file - looks like it works, because the pages are plain HTML and a
static server happily serves them with GET.

Then sign-in fails with `501 Unsupported method ('POST')`, because a
static file server implements GET and nothing else, and every real
action in this app is a POST. Nothing about that error points at the
cause, and a user has no reason to suspect the way they opened the app
rather than the app itself. It cost a real user a working evening.

So: one command, no arguments needed, no way to start the wrong half. It
picks a free port, starts the API (which serves the frontend from the
same origin), and opens the browser at the right address.

The flags are for the cases that are not a person at a laptop -
containers, CI, a fixed port behind a proxy - and every one of them is
optional. `python run.py` on its own must keep working exactly as it
always has, because that is the command in every instruction anyone has
been given.

    python run.py                     what a person runs
    python run.py --port 9000         a fixed port, no probing
    python run.py --no-browser        containers and CI
    python run.py --host 0.0.0.0      reachable off this machine
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8000
HOST = "127.0.0.1"


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((HOST, port))
            return True
        except OSError:
            return False


def _this_app_is_on(port: int) -> bool:
    """Is the thing already listening on `port` a copy of THIS app?

    Asked with the same GET /health the frontend's own guard uses, so
    "it answers" is not mistaken for "it is us" - some other local
    server on 8000 will answer something, just not this.
    """
    import json as _json
    import urllib.error
    import urllib.request

    try:
        # No proxy: this is a loopback address, and a configured
        # HTTP(S)_PROXY would otherwise be asked to fetch localhost.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://{HOST}:{port}/health", timeout=2) as response:
            body = _json.loads(response.read().decode())
        return isinstance(body, dict) and body.get("status") == "ok" \
            and "Digital Wellness" in str(body.get("app_name", ""))
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _pick_port() -> tuple[int, bool]:
    """Returns (port, already_running).

    The important case is the second one. Starting this script twice
    used to silently bring up a SECOND copy of the app on the next free
    port, which is a genuinely confusing thing to do quietly: the two
    instances then have separate in-memory state, and if they were
    started from different folders they have separate storage/
    directories too - so an account created in the browser pointed at
    the first simply does not exist for the second. Reported as "I
    registered in Chrome, and in Edge it makes me sign up again", and
    reproduced exactly that way.

    So if this app is already listening on the default port, this does
    not start a rival. It points the browser at the copy that is
    already running, which is what the person double-clicking the
    launcher a second time actually wanted.
    """
    if not _port_is_free(DEFAULT_PORT) and _this_app_is_on(DEFAULT_PORT):
        return DEFAULT_PORT, True

    for candidate in range(DEFAULT_PORT, DEFAULT_PORT + 20):
        if _port_is_free(candidate):
            return candidate, False
    raise SystemExit(
        f"No free port between {DEFAULT_PORT} and {DEFAULT_PORT + 19}. "
        f"Close whatever is using them and try again."
    )


def _check_dependencies() -> None:
    missing = []
    for module, install_name in (
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sklearn", "scikit-learn"),
        ("pandas", "pandas"),
    ):
        try:
            __import__(module)
        except ImportError:
            missing.append(install_name)
    if missing:
        raise SystemExit(
            "Missing dependencies: " + ", ".join(missing) + "\n\n"
            "Install them first:\n\n"
            "    pip install -r requirements.txt\n"
        )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Start Digital Wellness AI (API + frontend, one origin).",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help=f"listen on this exact port instead of probing from {DEFAULT_PORT}. "
             f"Fails loudly if it is taken, rather than silently landing "
             f"somewhere a proxy is not pointed at.",
    )
    parser.add_argument(
        "--host", default=HOST,
        help=f"interface to bind (default {HOST}). Use 0.0.0.0 inside a "
             f"container. Binding beyond loopback exposes an app whose "
             f"storage is a JSON file, so mean it.",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="do not open a browser. Implied wherever there is no display.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    global HOST
    HOST = args.host

    if not (PROJECT_ROOT / "api" / "main.py").exists():
        raise SystemExit(
            f"This script must stay in the project root. Expected to find "
            f"api/main.py next to it, in {PROJECT_ROOT}."
        )

    _check_dependencies()
    # Imported after the dependency check so a missing package produces
    # the instruction above rather than a raw ImportError traceback.
    import uvicorn

    if args.port is not None:
        # An explicit port is a promise made to something else - a proxy,
        # a compose file, a tunnel. Quietly moving to another one would
        # leave that thing pointed at nothing, so this refuses instead.
        if not _port_is_free(args.port) and not _this_app_is_on(args.port):
            raise SystemExit(
                f"Port {args.port} is taken by something that is not this app. "
                f"Free it, or leave --port off and let a free one be picked."
            )
        port, already_running = args.port, _this_app_is_on(args.port)
    else:
        port, already_running = _pick_port()
    url = f"http://{HOST}:{port}"

    if already_running:
        # Deliberately does NOT start a second copy - see _pick_port.
        print()
        print("  Digital Wellness AI is already running.")
        print("  " + "-" * 40)
        print(f"  Open:  {url}")
        print()
        print("  Opening that one rather than starting a second copy:")
        print("  two copies keep separate accounts, so an account made")
        print("  in one is missing from the other.")
        print()
        if not args.no_browser:
            webbrowser.open(url)
        return

    print()
    print("  Digital Wellness AI")
    print("  " + "-" * 40)
    print(f"  Open:  {url}")
    print("  Stop:  press Ctrl+C in this window")
    print()
    if port != DEFAULT_PORT:
        print(f"  (port {DEFAULT_PORT} was busy, and whatever is on it is not")
        print(f"   this app, so this copy is on {port} instead)")
        print()

    # Opened from a timer so the browser lands after the server is up;
    # a browser that arrives first shows a connection error and the user
    # has to know to refresh.
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    try:
        uvicorn.run("api.main:app", host=HOST, port=port, log_level="warning")
    except KeyboardInterrupt:
        print("\n  Stopped.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
