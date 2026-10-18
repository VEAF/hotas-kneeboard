"""Where DCS is (the install, from the registry, and the user's Saved Games folder), and its language."""

import gettext
import sys
import uuid
from collections.abc import Callable
from pathlib import Path

from .engine import DCS_INTERPRETER, REGISTRY_ROOT, detect_dcs_install_dir

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
    install_override: str | None,
    saved_override: str | None,
    own_interpreter: bool = False,
    language_override: str | None = None,
) -> dict:
    """The two folders to use, each from the settings or detected, and what is wrong with them
    (``problems``, shown to the user as they are: in French, like the UI).

    ``own_interpreter``: the engine runs with another Lua than the install's (tests).
    """
    install = Path(install_override) if install_override else detect_dcs_install_dir()
    saved = Path(saved_override) if saved_override else detect_saved_games_dir()
    problems = []
    if install is None:
        problems.append("Installation de DCS introuvable : indique-la dans les réglages")
    elif not own_interpreter and not (install / DCS_INTERPRETER).is_file():
        problems.append(
            f"Pas de {DCS_INTERPRETER.as_posix()} dans {install} : ce n'est pas une installation de DCS"
        )
    if saved is None:
        problems.append("Dossier Saved Games de DCS introuvable : indique-le dans les réglages")
    elif not (saved / "Config" / "Input").is_dir():
        problems.append(f"Pas de Config/Input dans {saved} : ce n'est pas le dossier Saved Games de DCS")
    return {
        "install_dir": str(install) if install else None,
        "install_detected": not install_override,
        "saved_games_dir": str(saved) if saved else None,
        "saved_games_detected": not saved_override,
        "language": (language_override or detect_language() or "en").lower(),
        "problems": problems,
    }


def detect_language() -> str | None:
    r"""Language of the game (``HKCU\Software\Eagle Dynamics\DCS World*\Language``, e.g. "EN")."""
    if sys.platform != "win32":
        return None
    import winreg

    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_ROOT)
    except OSError:
        return None
    with root:
        index = 0
        names = []
        while True:
            try:
                names.append(winreg.EnumKey(root, index))
            except OSError:
                break
            index += 1
        for name in sorted(
            (n for n in names if n.startswith("DCS World")), key=lambda n: (n != "DCS World", n)
        ):
            try:
                with winreg.OpenKey(root, name) as key:
                    return str(winreg.QueryValueEx(key, "Language")[0]).lower()
            except OSError:
                continue
    return None


def command_translator(install_dir: Path, language: str | None) -> Callable[[str], str]:
    """Command names as the game shows them: profiles name commands in English source text
    (``_('Trim: Nose Up')``) that ``l10n/<language>/LC_MESSAGES/input.mo`` translates, English
    included ("Trim Hat - NOSE UP" in the A-10C II). Names without translation stay as they are."""
    path = Path(install_dir) / "l10n" / (language or "en").lower() / "LC_MESSAGES" / "input.mo"
    try:
        with path.open("rb") as file:
            return gettext.GNUTranslations(file).gettext
    except (OSError, ValueError):  # missing, or not a .mo file
        return lambda name: name
