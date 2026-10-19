"""Reads and writes DCS's input files (``disabled.lua``, ``*.diff.lua``…) exactly as the game does.

Reading runs the file with DCS's Lua interpreter and returns its value as Python data; writing goes
through the game's own ``Scripts/Serializer.lua`` (``serialize_sorted``, LF line ends), so that a
file written here is byte for byte what DCS would have written. Checked by reading and rewriting
every file of a real ``Config/Input``: all identical.
"""

import json
import math
import subprocess
import uuid
from pathlib import Path

from .engine import DCS_INTERPRETER

LUA_SCRIPT = Path(__file__).parent / "lua" / "lua_tables.lua"
TIMEOUT_SECONDS = 30
BOOTSTRAP = "local n = tonumber(io.read('*l')) assert(loadstring(io.read(n), '=lua_tables.lua'))()"


class LuaTableError(Exception):
    pass


def to_lua(value) -> str:
    """Lua source of a value made of dicts (string keys), lists, strings, numbers and booleans.

    ASCII only and without control characters: it goes through the interpreter's stdin, which is
    in text mode on Windows (a CR or a Ctrl+Z there would corrupt it)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise LuaTableError(f"nombre non représentable : {value}")
        return repr(value)
    if isinstance(value, str):
        out = []
        for byte in value.encode("utf-8"):
            char = chr(byte)
            out.append(char if 0x20 <= byte < 0x7F and char not in '"\\' else f"\\{byte}")
        return '"' + "".join(out) + '"'
    if isinstance(value, list):
        return "{" + ",".join(to_lua(v) for v in value) + "}"
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise LuaTableError("clés de table : texte attendu")
        return "{" + ",".join(f"[{to_lua(k)}]={to_lua(v)}" for k, v in value.items()) + "}"
    raise LuaTableError(f"valeur non représentable en Lua : {type(value).__name__}")


def _run(install_dir: Path, records: str, lua_interpreter: Path | str | None) -> bytes:
    interpreter = lua_interpreter or Path(install_dir) / DCS_INTERPRETER
    script = LUA_SCRIPT.read_bytes().replace(b"\r\n", b"\n")
    stdin = str(len(script)).encode() + b"\n" + script
    stdin += f"scripts\t{(Path(install_dir) / 'Scripts').as_posix()}\n".encode() + records.encode("utf-8")
    try:
        completed = subprocess.run(
            [str(interpreter), "-e", BOOTSTRAP],
            input=stdin,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise LuaTableError(f"Interpréteur Lua de DCS impossible à lancer : {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise LuaTableError(f"Fichier Lua illisible ou impossible à écrire : {detail}")
    return completed.stdout


def read_table(install_dir: Path, path: Path, lua_interpreter: Path | str | None = None):
    """Value returned by a DCS Lua file (dicts, lists, strings, numbers, booleans)."""
    out = _run(install_dir, f"read\t{Path(path).as_posix()}\n", lua_interpreter)
    try:
        return json.loads(out.decode("utf-8"))
    except ValueError as error:  # UnicodeDecodeError included
        raise LuaTableError(f"{Path(path).name} : contenu illisible ({error})") from error


def write_table(
    install_dir: Path, path: Path, name: str, value, lua_interpreter: Path | str | None = None
) -> None:
    """Writes ``local <name> = {…}return <name>`` as DCS does; through a temporary file, so that a
    failure leaves the old file as it was."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    source = to_lua(value).encode("ascii")
    try:
        _run(
            install_dir,
            f"write\t{tmp.as_posix()}\t{name}\t{len(source)}\n" + source.decode("ascii"),
            lua_interpreter,
        )
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
