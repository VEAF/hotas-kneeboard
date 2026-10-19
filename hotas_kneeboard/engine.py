"""Effective DCS World bindings, computed by DCS's own Lua interpreter.

A ``.diff.lua`` file only holds the user's changes against the module's defaults. The
effective bindings come from the module's default profile (a Lua program, not data) with the
diff applied. ``lua/effective_bindings.lua`` reproduces what DCS does
(``Scripts/Input/Data.lua``); it runs with ``bin/luae.exe``, the standalone Lua 5.1 interpreter
shipped with DCS, so nothing else is needed and commands are hashed exactly as in the game.

Comes from VEAF/joystick-diagrams-dcs-world-plugin (branch feat/effective-dcs-bindings), where it
was checked identical to DCS's MAKE HTML export on A-10C II and F-16C_50.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

_logger = logging.getLogger(__name__)

LUA_SCRIPT = Path(__file__).parent / "lua" / "effective_bindings.lua"
DCS_INTERPRETER = Path("bin") / "luae.exe"
REGISTRY_ROOT = r"Software\Eagle Dynamics"
TIMEOUT_SECONDS = 120
# Windows' MAX_PATH, terminating null included: luae.exe cannot open a longer path
MAX_PATH = 260
PATH_TOO_LONG = "path too long"
# Command line of the interpreter, ASCII only: reads the script's length, the script, and runs it
BOOTSTRAP = "local n = tonumber(io.read('*l')) assert(loadstring(io.read(n), '=effective_bindings.lua'))()"


class EffectiveBindingsError(Exception):
    """The Lua loader could not run or returned unusable output."""


def detect_dcs_install_dir() -> Path | None:
    """DCS install directory from HKCU\\Software\\Eagle Dynamics\\DCS World*\\Path, or None.

    The release ("DCS World") is preferred over other variants (e.g. "DCS World OpenBeta").
    """
    if sys.platform != "win32":
        return None
    import winreg

    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_ROOT)
    except OSError:
        return None
    with root:
        names = []
        index = 0
        while True:
            try:
                names.append(winreg.EnumKey(root, index))
            except OSError:
                break
            index += 1
        for name in sorted(
            (n for n in names if n.startswith("DCS World")),
            key=lambda n: (n != "DCS World", n),
        ):
            try:
                with winreg.OpenKey(root, name) as key:
                    path = Path(winreg.QueryValueEx(key, "Path")[0])
            except OSError:
                continue
            if path.joinpath(DCS_INTERPRETER).is_file():
                return path
    return None


def _directory_listings(install: str, saved_games: str) -> dict[str, list[str]]:
    """Entries of every directory the Lua loader looks into (Lua 5.1 cannot list one).

    Modules and their Input/<profile>/joystick|keyboard folders, the install's Config/Input
    tree (built-in profiles, the Default unit) and the user's Config/Input/<profile> folders.
    """
    listings: dict[str, list[str]] = {}

    def add(directory: str) -> list[str]:
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            return []
        listings[directory] = entries
        return [e for e in entries if os.path.isdir(f"{directory}/{e}")]

    for root in (
        f"{install}/Mods/aircraft",
        f"{install}/CoreMods/aircraft",
        f"{install}/Mods/tech",
        f"{saved_games}/Mods/aircraft",
    ):
        for module in add(root):
            for profile in add(f"{root}/{module}/Input"):
                for device_type in ("joystick", "keyboard"):
                    add(f"{root}/{module}/Input/{profile}/{device_type}")
    for directory, _, _ in os.walk(f"{install}/Config/Input"):
        add(Path(directory).as_posix())
    for profile in add(f"{saved_games}/Config/Input"):
        for device_type in ("joystick", "keyboard"):
            add(f"{saved_games}/Config/Input/{profile}/{device_type}")
    return listings


def _loader_input(
    install: str, saved_games: str, profiles: list[str], removals: list[dict] | None = None
) -> bytes:
    """stdin of the interpreter: the script, then the records it reads (see its header)"""
    # Lua reads stdin in text mode on Windows: a CR would shift the script length
    script = LUA_SCRIPT.read_bytes().replace(b"\r\n", b"\n")
    records = [
        f"install\t{install}",
        f"saved\t{saved_games}",
        f"casefold\t{1 if sys.platform == 'win32' else 0}",
    ]
    records += [f"profile\t{profile}" for profile in profiles]
    for r in removals or []:
        fields = [r["profile"], r["device"], r["hash"], r["key"]]
        reformers = list(r.get("reformers") or [])
        # tab-separated record, reformers comma-joined: only they may not hold a comma
        if any(c in field for field in fields + reformers for c in "\t\n") or any(
            "," in x for x in reformers
        ):
            raise EffectiveBindingsError(f"liaison à retirer illisible : {r}")
        records.append("remove\t" + "\t".join([*fields, ",".join(reformers)]))
    for directory, entries in _directory_listings(install, saved_games).items():
        records.append(f"dir\t{directory}")
        records += [f"entry\t{entry}" for entry in entries if "\n" not in entry]
    data = "\n".join(records).encode("utf-8", errors="replace") + b"\n"
    return str(len(script)).encode() + b"\n" + script + data


def load_effective_bindings(
    install_dir: Path,
    saved_games_dir: Path,
    profiles: list[str],
    lua_interpreter: Path | str | None = None,
    removals: list[dict] | None = None,
) -> dict:
    """Runs the Lua loader and returns its JSON output.

    ``lua_interpreter`` defaults to the install's ``bin/luae.exe``; any Lua 5.1 works (tests).
    The result maps each requested profile name to ``{"found": bool, "unit_type": str | None,
    "devices": [...]}`` under ``"profiles"``; ``found`` is false when the module is not in the
    install, and its devices then only hold what their diffs add (``"source": "diff"``).

    Everything but the interpreter goes through stdin in UTF-8: luae.exe reads its command
    line in the ANSI code page but opens files in UTF-8, so a non-ASCII path (a Windows user
    name, the plugin folder) would not survive as an argument.
    """
    interpreter = (
        lua_interpreter if lua_interpreter is not None else Path(install_dir).joinpath(DCS_INTERPRETER)
    )
    install = Path(install_dir).as_posix()
    saved_games = Path(saved_games_dir).as_posix()
    command = [str(interpreter), "-e", BOOTSTRAP]
    _logger.debug(f"DCS: running {interpreter} for {profiles}")
    try:
        completed = subprocess.run(
            command,
            input=_loader_input(install, saved_games, profiles, removals),
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
            # never a console window of its own for luae.exe
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EffectiveBindingsError(f"cannot run {interpreter}: {error}") from error

    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    for line in stderr.splitlines():
        _logger.warning(f"DCS Lua: {line}")
    if completed.returncode != 0:
        raise EffectiveBindingsError(f"{interpreter} exited with code {completed.returncode}: {stderr}")
    try:
        result = json.loads(completed.stdout.decode("utf-8", errors="replace"))
    except ValueError as error:
        raise EffectiveBindingsError(f"invalid output from the Lua loader: {error}") from error
    if not isinstance(result.get("profiles"), dict):
        raise EffectiveBindingsError("invalid output from the Lua loader: no profiles")
    _flag_long_paths(result, Path(saved_games_dir))
    return result


def _flag_long_paths(result: dict, saved_games_dir: Path) -> None:
    """luae.exe opens files through the C library, limited to MAX_PATH on Windows: a diff whose path
    is longer is not read, and its device shows the module's defaults. Such a device is marked
    ``error = PATH_TOO_LONG`` rather than shown as if nothing were wrong."""
    if sys.platform != "win32":
        return
    for profile, entry in result["profiles"].items():
        for device in entry.get("devices", []):
            path = saved_games_dir / "Config" / "Input" / profile / "joystick" / f"{device['name']}.diff.lua"
            if len(str(path)) >= MAX_PATH:
                _logger.warning(f"DCS: {path} is too long for DCS's Lua interpreter, not read")
                device["error"] = PATH_TOO_LONG


def list_user_profiles(saved_games_dir: Path) -> list[str]:
    """Profiles with at least one joystick diff in ``Saved Games/DCS/Config/Input``: those the
    user configured a device for, the only ones with something to draw."""
    root = Path(saved_games_dir) / "Config" / "Input"
    try:
        profiles = sorted(p.name for p in root.iterdir() if p.is_dir())
    except OSError:
        return []
    return [p for p in profiles if any((root / p / "joystick").glob("*.diff.lua"))]
