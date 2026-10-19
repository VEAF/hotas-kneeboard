"""Writes the PNG pages into ``Saved Games/DCS/Kneeboard/<unit type>/``.

DCS shows every image of that folder in the kneeboard of that aircraft, in file name order. Our
pages are named ``HOTAS - <profile> - <nn> <title>.png``: an export replaces the pages of the same
profile (pages of a device no longer exported disappear) and touches nothing else, neither the
user's own pages nor those of another seat of the same aircraft (AH-64D pilot and AI menu
profiles share the unit type AH-64D_BLK_II).
"""

import base64
import binascii
import re
import uuid
from pathlib import Path

from .i18n import t

PREFIX = "HOTAS - "
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# a unit type is a folder name, never a path
_UNIT_TYPE = re.compile(r"^[^<>:\"/\\|?*\x00-\x1f]+$")


class KneeboardError(ValueError):
    pass


def _safe(text: str) -> str:
    return _UNSAFE.sub("_", text).strip(" .") or "page"


def page_file_name(profile: str, index: int, title: str) -> str:
    return f"{PREFIX}{_safe(profile)} - {index:02d} {_safe(title)}.png"


def is_page_of(file_name: str, profile: str) -> bool:
    """A page this app wrote for this profile, by the exact shape of its name"""
    pattern = rf"{re.escape(PREFIX + _safe(profile))} - \d{{2,}} .+\.png"
    return re.fullmatch(pattern, file_name) is not None


def _decode(pages: list[dict]) -> list[tuple[str, bytes]]:
    images = []
    for page in pages:
        try:
            data = base64.b64decode(page["png"], validate=True)
        except (KeyError, TypeError, binascii.Error) as error:
            raise KneeboardError(t("kneeboard.bad_base64", page=repr(page.get("title")))) from error
        if not data.startswith(PNG_SIGNATURE):
            raise KneeboardError(t("kneeboard.not_png", page=repr(page.get("title"))))
        images.append((str(page.get("title") or "page"), data))
    return images


def write_pages(saved_games_dir: Path, unit_type: str, profile: str, pages: list[dict]) -> dict:
    """``pages``: ``[{"title": str, "png": base64}]``, in kneeboard order.

    All or nothing: the new pages are written under temporary names, the previous ones are moved
    aside, then the new ones take their names. Any failure (disk full, a page open in another
    program) puts the previous pages back and removes the temporary files."""
    if not _UNIT_TYPE.match(unit_type) or unit_type.strip(" .") == "":
        raise KneeboardError(f"type d'avion invalide : {unit_type!r}")
    images = _decode(pages)
    folder = Path(saved_games_dir) / "Kneeboard" / unit_type
    folder.mkdir(parents=True, exist_ok=True)

    def temporary_name() -> Path:
        return folder / f".hotas-{uuid.uuid4().hex}.tmp"

    staged: list[tuple[Path, Path]] = []  # (temporary, final)
    aside: list[tuple[Path, Path]] = []  # (temporary, previous page)
    placed: list[Path] = []
    try:
        for index, (title, data) in enumerate(images, start=1):
            temporary = temporary_name()
            staged.append((temporary, folder / page_file_name(profile, index, title)))
            temporary.write_bytes(data)
        for path in [p for p in folder.iterdir() if p.is_file() and is_page_of(p.name, profile)]:
            temporary = temporary_name()
            path.replace(temporary)
            aside.append((temporary, path))
        for temporary, final in staged:
            temporary.replace(final)
            placed.append(final)
    except OSError:
        for final in placed:
            final.unlink(missing_ok=True)
        for temporary, previous in aside:
            temporary.replace(previous)
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        raise
    for temporary, _ in aside:
        temporary.unlink(missing_ok=True)
    written = [final.name for _, final in staged]
    removed = sorted({previous.name for _, previous in aside} - set(written))
    return {"folder": str(folder), "written": written, "removed": removed}
