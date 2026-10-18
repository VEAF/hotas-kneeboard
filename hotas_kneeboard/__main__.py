"""Starts the server on 127.0.0.1 and opens the browser on it."""

import argparse
import logging
import socket
import sys
import threading
import webbrowser

import uvicorn

from .app import create_app
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="hotas-kneeboard")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args()

    log_dir = data_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.FileHandler(log_dir / "hotas-kneeboard.log", encoding="utf-8")]
    # the windowed .exe has no console: sys.stderr is None there
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers
    )

    port = free_port(args.port)
    url = f"http://127.0.0.1:{port}/"
    logging.getLogger(__name__).info(f"HOTAS Kneeboard on {url}")
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_config=None)


if __name__ == "__main__":
    main()
