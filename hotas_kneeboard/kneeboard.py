"""Writes the PNG pages into ``Saved Games/DCS/Kneeboard/<unit type>/``.

DCS shows every image of that folder in the kneeboard of that aircraft, in file name order. Our
pages all start with ``PREFIX``: an export replaces the previous one (pages of a device no
longer exported disappear) without touching the user's other pages.
"""

import base64
import binascii
import re
from pathlib import Path

PREFIX = "HOTAS - "
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# a unit type is a folder name, never a path
_UNIT_TYPE = re.compile(r"^[^<>:\"/\\|?*\x00-\x1f]+$")


class KneeboardError(ValueError):
    pass


def page_file_name(index: int, title: str) -> str:
    safe = _UNSAFE.sub("_", title).strip(" .") or "page"
    return f"{PREFIX}{index:02d} {safe}.png"


def write_pages(saved_games_dir: Path, unit_type: str, pages: list[dict]) -> dict:
    """``pages``: ``[{"title": str, "png": base64}]``, in kneeboard order."""
    if not _UNIT_TYPE.match(unit_type) or unit_type in (".", ".."):
        raise KneeboardError(f"invalid unit type {unit_type!r}")
    images = []
    for page in pages:
        try:
            data = base64.b64decode(page["png"], validate=True)
        except (KeyError, TypeError, binascii.Error) as error:
            raise KneeboardError(f"page {page.get('title')!r}: not base64 PNG data") from error
        if not data.startswith(PNG_SIGNATURE):
            raise KneeboardError(f"page {page.get('title')!r}: not a PNG image")
        images.append((str(page.get("title") or "page"), data))

    folder = Path(saved_games_dir) / "Kneeboard" / unit_type
    folder.mkdir(parents=True, exist_ok=True)
    removed = []
    for old in folder.glob(f"{PREFIX}*.png"):
        old.unlink()
        removed.append(old.name)
    written = []
    for index, (title, data) in enumerate(images, start=1):
        path = folder / page_file_name(index, title)
        path.write_bytes(data)
        written.append(path.name)
    return {"folder": str(folder), "written": written, "removed": sorted(set(removed) - set(written))}
