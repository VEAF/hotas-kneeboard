"""Starts the server on 127.0.0.1 and opens the browser on it."""

import argparse
import json
import logging
import socket
import sys
import threading
import urllib.request
import webbrowser

import uvicorn

from .app import create_app
from .i18n import t
from .settings import data_dir

DEFAULT_PORT = 8642


def free_port(preferred: int) -> int:
    """The preferred port when free (a bookmark keeps working), else any free one."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return s.getsockname()[1]
    raise RuntimeError("no free port")


def already_running(port: int) -> bool:
    """An instance answers on this port: open the browser on it rather than start another one."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=1) as response:
            return response.status == 200 and "version" in json.load(response)
    except (OSError, ValueError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(prog="hotas-kneeboard")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args()

    log_dir = data_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.FileHandler(log_dir / "hotas-kneeboard.log", encoding="utf-8")]
    # no console (e.g. pythonw): sys.stderr is None there
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers
    )

    if already_running(args.port):
        print(t("main.already_running", url=f"http://127.0.0.1:{args.port}/"))
        if not args.no_browser:
            webbrowser.open(f"http://127.0.0.1:{args.port}/")
        return
    port = free_port(args.port)
    url = f"http://127.0.0.1:{port}/"
    logging.getLogger(__name__).info(f"HOTAS Kneeboard on {url}")
    if sys.stdout is not None:
        print(t("main.running", url=url), flush=True)
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_config=None)


if __name__ == "__main__":
    main()
