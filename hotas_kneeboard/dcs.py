"""Where DCS is: the install (registry) and the user's Saved Games folder."""

import sys
import uuid
from pathlib import Path

from .engine import DCS_INTERPRETER, detect_dcs_install_dir

# FOLDERID_SavedGames
SAVED_GAMES_FOLDER_ID = "{4C5C32FF-BB9D-43B0-B5B4-2D72E54EAAA4}"
SAVED_GAMES_CANDIDATES = ("DCS", "DCS.openbeta")


def _known_saved_games_folder() -> Path | None:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    raw = uuid.UUID(SAVED_GAMES_FOLDER_ID).bytes_le
    guid = GUID.from_buffer_copy(raw)
    path = ctypes.c_wchar_p()
    shell32 = ctypes.windll.shell32
    if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path)) != 0:
        return None
    try:
        return Path(path.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path)


def detect_saved_games_dir() -> Path | None:
    """``Saved Games/DCS`` (or ``DCS.openbeta``) that holds a ``Config`` folder, or None."""
    roots = [p for p in (_known_saved_games_folder(), Path.home() / "Saved Games") if p]
    for root in roots:
        for name in SAVED_GAMES_CANDIDATES:
            candidate = root / name
            if (candidate / "Config").is_dir():
                return candidate
    return None


def resolve_dirs(
    install_override: str | None, saved_override: str | None, own_interpreter: bool = False
) -> dict:
    """The two folders to use, each from the settings or detected, and what is wrong with them.

    ``own_interpreter``: the engine runs with another Lua than the install's (tests).
    """
    install = Path(install_override) if install_override else detect_dcs_install_dir()
    saved = Path(saved_override) if saved_override else detect_saved_games_dir()
    problems = []
    if install is None:
        problems.append("DCS install not found: set it in the settings")
    elif not own_interpreter and not (install / DCS_INTERPRETER).is_file():
        problems.append(f"no {DCS_INTERPRETER.as_posix()} in {install}: not a DCS install")
    if saved is None:
        problems.append("Saved Games/DCS not found: set it in the settings")
    elif not (saved / "Config" / "Input").is_dir():
        problems.append(f"no Config/Input in {saved}: not a DCS Saved Games folder")
    return {
        "install_dir": str(install) if install else None,
        "install_detected": not install_override,
        "saved_games_dir": str(saved) if saved else None,
        "saved_games_detected": not saved_override,
        "problems": problems,
    }
