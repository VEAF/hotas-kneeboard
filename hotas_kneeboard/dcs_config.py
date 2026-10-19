"""Changes to DCS's own input files (``Saved Games/DCS/Config/Input``) and their backups.

Every change goes through ``guarded_write``: refused while DCS runs (it rewrites these files when
it saves its controls, and would overwrite ours), preceded by a zip of the whole folder, which the
app lists and restores. Error messages reach the user as they are: they are in French."""

import logging
import re
import shutil
import subprocess
import sys
import threading
import uuid
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath

from .engine import EffectiveBindingsError, load_effective_bindings
from .lua_tables import LuaTableError, read_table, write_table

_logger = logging.getLogger(__name__)

# the game and the dedicated server: both save their controls into Config/Input
DCS_PROCESSES = ("dcs.exe", "dcs_server.exe")
KEEP_BACKUPS = 20
BACKUP_PREFIX = "config-input-"
# one change at a time: each reads a file, changes it and writes it back
_WRITE_LOCK = threading.Lock()
TIME_FORMAT = "%Y%m%d-%H%M%S-%f"


class DcsConfigError(Exception):
    pass


class BackupNotFoundError(DcsConfigError):
    pass


def dcs_running() -> bool:
    """True when the game or the dedicated server runs. Raises when it cannot be known on Windows:
    writing blind could lose the user's changes."""
    if sys.platform != "win32":
        return False
    try:
        completed = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            timeout=15,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise DcsConfigError(
            f"Impossible de savoir si DCS est lancé ({error}) : rien n'a été modifié"
        ) from error
    # one line per process, its image name first: "DCS.exe","1234",…
    output = completed.stdout.decode("mbcs", errors="replace").lower()
    return any(f'"{name}"' in output for name in DCS_PROCESSES)


@dataclass
class Backup:
    id: str
    created: datetime
    reason: str
    size: int
    files: int

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "created": self.created.isoformat(timespec="seconds"),
            "reason": self.reason,
            "size": self.size,
            "files": self.files,
        }


class BackupStore:
    """Zips of ``Config/Input``, one per change, the last ``keep`` kept. The reason of a backup is
    the zip's comment; its date is in its name."""

    def __init__(self, folder: Path, keep: int = KEEP_BACKUPS):
        self.folder = folder
        self.keep = keep

    def _path(self, backup_id: str) -> Path:
        try:
            datetime.strptime(backup_id, TIME_FORMAT)
        except ValueError as error:
            raise BackupNotFoundError("sauvegarde introuvable") from error
        return self.folder / f"{BACKUP_PREFIX}{backup_id}.zip"

    def list(self) -> list[Backup]:
        backups = []
        for path in self.folder.glob(f"{BACKUP_PREFIX}*.zip"):
            backup_id = path.stem.removeprefix(BACKUP_PREFIX)
            try:
                created = datetime.strptime(backup_id, TIME_FORMAT)
                with zipfile.ZipFile(path) as archive:
                    files = sum(1 for info in archive.infolist() if not info.is_dir())
                    reason = archive.comment.decode("utf-8", errors="replace")
            except (ValueError, OSError, zipfile.BadZipFile) as error:
                _logger.warning(f"backup {path.name} skipped: {error}")
                continue
            backups.append(Backup(backup_id, created, reason, path.stat().st_size, files))
        return sorted(backups, key=lambda b: b.created, reverse=True)

    def create(self, input_dir: Path, reason: str, protect: str | None = None) -> Backup:
        """Zips ``input_dir`` (folders included, so that a restore gives it back as it was), then
        drops the oldest backups but ``protect``."""
        if not input_dir.is_dir():
            raise DcsConfigError(f"Dossier des commandes de DCS introuvable : {input_dir}")
        self.folder.mkdir(parents=True, exist_ok=True)
        # two backups within the clock's resolution would get the same name
        created = datetime.now()
        while (path := self._path(created.strftime(TIME_FORMAT))).exists():
            created += timedelta(microseconds=1)
        backup_id = created.strftime(TIME_FORMAT)
        tmp = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
        files = 0
        try:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.comment = reason.encode("utf-8")
                for item in sorted(input_dir.rglob("*")):
                    archive.write(item, item.relative_to(input_dir).as_posix())
                    files += item.is_file()
            tmp.replace(path)
        except OSError as error:
            tmp.unlink(missing_ok=True)
            raise DcsConfigError(f"Sauvegarde impossible, rien n'a été modifié : {error}") from error
        self._prune(protect)
        return Backup(backup_id, created, reason, path.stat().st_size, files)

    def _prune(self, protect: str | None) -> None:
        for backup in self.list()[self.keep :]:
            if backup.id != protect:
                self._path(backup.id).unlink(missing_ok=True)

    def extract(self, backup_id: str, target: Path) -> None:
        """Unzips a backup into ``target``, refusing any entry that would land outside it."""
        path = self._path(backup_id)
        if not path.is_file():
            raise BackupNotFoundError("sauvegarde introuvable")
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    name = PurePosixPath(info.filename)
                    if name.is_absolute() or ".." in name.parts or ":" in info.filename:
                        raise DcsConfigError(f"sauvegarde invalide : {info.filename}")
                archive.extractall(target)
        except (OSError, zipfile.BadZipFile) as error:
            raise DcsConfigError(f"Sauvegarde illisible : {error}") from error


def input_dir_of(saved_games_dir: Path) -> Path:
    return Path(saved_games_dir) / "Config" / "Input"


def guarded_write(
    saved_games_dir: Path,
    backups: BackupStore,
    reason: str,
    change: Callable[[Path], object],
    *,
    is_running: Callable[[], bool] = dcs_running,
    protect: str | None = None,
):
    """Runs ``change(input_dir)`` once DCS is known to be closed and ``Config/Input`` is backed up;
    returns ``(backup, result of change)``."""
    with _WRITE_LOCK:
        if is_running():
            raise DcsConfigError(
                "DCS est lancé : ferme-le avant de modifier ses commandes (il réécrit ces fichiers)"
            )
        input_dir = input_dir_of(saved_games_dir)
        backup = backups.create(input_dir, reason, protect)
        return backup, change(input_dir)


def restore(
    saved_games_dir: Path,
    backups: BackupStore,
    backup_id: str,
    is_running: Callable[[], bool] = dcs_running,
) -> Backup:
    """Gives ``Config/Input`` back exactly as in the backup (files it did not hold are removed),
    after backing up the current state; returns that new backup."""
    input_dir = input_dir_of(saved_games_dir)
    stamp = uuid.uuid4().hex
    staged = input_dir.with_name(f".Input.restore-{stamp}")
    old = input_dir.with_name(f".Input.old-{stamp}")
    try:
        # unzipped before anything else: a damaged backup must not cost the current state
        backups.extract(backup_id, staged)
        staged.mkdir(exist_ok=True)  # a backup of an empty folder holds no entry
        created = datetime.strptime(backup_id, TIME_FORMAT)

        def swap(current: Path) -> None:
            current.replace(old)
            try:
                staged.replace(current)
            except OSError as error:
                try:
                    old.replace(current)
                except OSError as rollback_error:
                    raise DcsConfigError(
                        f"Restauration interrompue ({error}) : tes commandes d'avant sont dans {old}, "
                        f"à renommer en {current.name} à la main ({rollback_error})"
                    ) from rollback_error
                raise
            shutil.rmtree(old, ignore_errors=True)

        backup, _ = guarded_write(
            saved_games_dir,
            backups,
            f"avant la restauration du {created:%d/%m/%Y à %H:%M:%S}",
            swap,
            is_running=is_running,
            protect=backup_id,
        )
        return backup
    except OSError as error:
        raise DcsConfigError(
            f"Restauration impossible, les fichiers de DCS n'ont pas changé : {error}"
        ) from error
    finally:
        shutil.rmtree(staged, ignore_errors=True)


# --- devices DCS ignores: Config/Input/disabled.lua ----------------------------------------------

DISABLED_FILE = "disabled.lua"
# INPUT (Main): created [<name>] with full id [<name> {GUID}],JOYSTICK|STANDARD
CREATED_DEVICE = re.compile(r"INPUT \(Main\): created \[[^\]]*\] with full id \[([^\]]+)\]")


def seen_devices(saved_games_dir: Path) -> list[str]:
    """Full names (with GUID) of the devices DCS created in its last two sessions (``Logs/dcs.log``,
    then ``dcs.log.old``): the exact spelling DCS uses, whose GUID case may differ from a diff
    file's name."""
    names = []
    for log in ("dcs.log", "dcs.log.old"):
        try:
            text = (Path(saved_games_dir) / "Logs" / log).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        names += CREATED_DEVICE.findall(text)
    return list(dict.fromkeys(names))


def read_disabled(install_dir: Path, saved_games_dir: Path, lua_interpreter=None) -> dict:
    """``disabled.lua`` as DCS wrote it: ``{"devices": {full name: true}, "pnp": bool}``; an absent
    file is an empty list."""
    path = input_dir_of(saved_games_dir) / DISABLED_FILE
    if not path.is_file():
        return {"devices": {}}
    try:
        value = read_table(install_dir, path, lua_interpreter)
    except LuaTableError as error:
        raise DcsConfigError(f"{DISABLED_FILE} illisible : {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("devices", {}), dict):
        raise DcsConfigError(f"{DISABLED_FILE} : contenu inattendu, rien n'a été modifié")
    value.setdefault("devices", {})
    return value


def disabled_devices(install_dir: Path, saved_games_dir: Path, lua_interpreter=None) -> list[str]:
    devices = read_disabled(install_dir, saved_games_dir, lua_interpreter)["devices"]
    return sorted(name for name, disabled in devices.items() if disabled is True)


def set_device_disabled(
    install_dir: Path,
    saved_games_dir: Path,
    backups: BackupStore,
    device: str,
    disabled: bool,
    *,
    is_running: Callable[[], bool] = dcs_running,
    lua_interpreter=None,
) -> Backup:
    """Disables or re-enables a device the way DCS's controls screen does (``pnp`` kept as is).
    The device is written under the name DCS gave it at its last start when the log has it, else
    under the spelling disabled.lua already uses: a diff file's name may differ in GUID case."""
    logged = next((d for d in seen_devices(saved_games_dir) if d.lower() == device.lower()), None)

    def change(input_dir: Path) -> None:
        value = read_disabled(install_dir, saved_games_dir, lua_interpreter)
        devices = value["devices"]
        known = [n for n in devices if n.lower() == device.lower()]
        for name in known:
            del devices[name]
        if disabled:
            devices[logged or (known[0] if known else device)] = True
        try:
            write_table(install_dir, input_dir / DISABLED_FILE, "disabled", value, lua_interpreter)
        except LuaTableError as error:
            raise DcsConfigError(f"{DISABLED_FILE} impossible à écrire : {error}") from error

    action = "désactivation" if disabled else "réactivation"
    backup, _ = guarded_write(
        saved_games_dir, backups, f"avant la {action} de {logged or device}", change, is_running=is_running
    )
    return backup


# --- devices DCS no longer sees: their diffs in every profile ------------------------------------


def dcs_log_date(saved_games_dir: Path) -> datetime | None:
    """When DCS last wrote its log (usually the end of its last session); None without a log"""
    try:
        return datetime.fromtimestamp((Path(saved_games_dir) / "Logs" / "dcs.log").stat().st_mtime)
    except OSError:
        return None


def device_diffs(saved_games_dir: Path) -> dict[str, list[Path]]:
    """Joystick diff files of every profile, by device full name in lower case"""
    found: dict[str, list[Path]] = {}
    for path in sorted(input_dir_of(saved_games_dir).glob("*/joystick/*.diff.lua")):
        found.setdefault(path.name.removesuffix(".diff.lua").lower(), []).append(path)
    return found


def absent_devices(saved_games_dir: Path, disabled: list[str]) -> list[dict]:
    """Devices with diffs that DCS did not create in its last two sessions: unplugged, renamed or gone.
    Empty when the log names no device at all: nothing to compare with. A disabled device is left
    out: DCS may not log it although it is plugged."""
    seen = {d.lower() for d in seen_devices(saved_games_dir)}
    if not seen:
        return []
    skip = seen | {d.lower() for d in disabled}
    return [
        {
            "device": paths[0].name.removesuffix(".diff.lua"),
            "profiles": [p.parent.parent.name for p in paths],
        }
        for key, paths in sorted(device_diffs(saved_games_dir).items())
        if key not in skip
    ]


def forget_device(
    saved_games_dir: Path,
    backups: BackupStore,
    device: str,
    disabled: list[str],
    *,
    is_running: Callable[[], bool] = dcs_running,
) -> tuple[Backup, list[str]]:
    """Deletes the device's diff in every profile, after a backup; returns the profiles touched.
    Refused for a device DCS created in its last two sessions (it is plugged, its settings are in
    use) and for a disabled one (``disabled``: it may be plugged without being logged)."""

    def targets() -> list[Path]:
        if device.lower() in {d.lower() for d in seen_devices(saved_games_dir)}:
            raise DcsConfigError(
                f"{device} est branché (vu par DCS lors de ses deux derniers lancements) : rien n'a été supprimé"
            )
        if device.lower() in {d.lower() for d in disabled}:
            raise DcsConfigError(
                f"{device} est désactivé dans DCS : réactive-le d'abord, rien n'a été supprimé"
            )
        paths = device_diffs(saved_games_dir).get(device.lower(), [])
        if not paths:
            raise DcsConfigError(f"Aucune commande enregistrée pour {device}")
        return paths

    targets()  # refused before any backup

    def change(_input_dir: Path) -> list[str]:
        paths = targets()  # again under the write lock: the files may have changed meanwhile
        try:
            for path in paths:
                path.unlink(missing_ok=True)
        except OSError as error:
            raise DcsConfigError(
                f"Suppression interrompue ({error}) : la sauvegarde d'avant est en tête de liste"
            ) from error
        return [p.parent.parent.name for p in paths]

    return guarded_write(saved_games_dir, backups, f"avant d'oublier {device}", change, is_running=is_running)


# --- removing key bindings: each device's diff rewritten as DCS saves it -------------------------


def new_diffs(
    install_dir: Path, saved_games_dir: Path, removals: list[dict], lua_interpreter=None
) -> list[dict]:
    """New diff of each (profile, device) concerned by ``removals`` (``profile``, ``device`` = the
    diff file's name without ``.diff.lua``, ``hash``, ``key``, ``reformers``), as DCS would save it:
    ``[{"profile", "device", "path", "diff"}]``, ``diff`` None when nothing differs from the
    module's defaults (DCS then deletes the file). Raises when one of them cannot be computed."""
    profiles = sorted({r["profile"] for r in removals})
    try:
        result = load_effective_bindings(install_dir, saved_games_dir, profiles, lua_interpreter, removals)
    except EffectiveBindingsError as error:
        raise DcsConfigError(f"Calcul impossible, rien n'a été modifié : {error}") from error
    out = []
    for rewrite in result.get("rewrites", []):
        where = f"{rewrite['device']} ({rewrite['profile']})"
        if rewrite.get("error"):
            raise DcsConfigError(f"{where} : {rewrite['error']} ; rien n'a été modifié")
        source = rewrite["diff"].get("source")
        input_dir = input_dir_of(saved_games_dir)
        path = input_dir / rewrite["profile"] / "joystick" / f"{rewrite['device']}.diff.lua"
        # luae.exe cannot open a path of 260 characters or more: a user diff it did not read would be
        # taken for no diff at all, and the user's bindings lost
        if path.is_file() and not (source and Path(source) == path):
            raise DcsConfigError(
                f"{where} : diff illisible par l'interpréteur de DCS (chemin de {len(str(path))} caractères ?) ;"
                " rien n'a été modifié"
            )
        try:
            old = read_table(install_dir, Path(source), lua_interpreter) if source else {}
        except LuaTableError as error:
            raise DcsConfigError(f"{where} : {error} ; rien n'a été modifié") from error
        if not isinstance(old, dict):
            raise DcsConfigError(f"{where} : diff inattendu ; rien n'a été modifié")
        # key and axis diffs recomputed as DCS does; the force feedback one is kept as it is
        diff = {
            "ffDiffs": old.get("ffDiffs"),
            "axisDiffs": rewrite["diff"]["axisDiffs"],
            "keyDiffs": rewrite["diff"]["keyDiffs"],
        }
        diff = {k: v for k, v in diff.items() if v}
        out.append(
            {"profile": rewrite["profile"], "device": rewrite["device"], "path": path, "diff": diff or None}
        )
    return out


def remove_bindings(
    install_dir: Path,
    saved_games_dir: Path,
    backups: BackupStore,
    removals: list[dict],
    reason: str,
    *,
    is_running: Callable[[], bool] = dcs_running,
    lua_interpreter=None,
) -> tuple[Backup, list[dict]]:
    """Removes key bindings (see ``new_diffs``) and writes each device's diff as DCS would: every
    diff is computed before the first is written, so that an error changes nothing."""

    def change(_input_dir: Path) -> list[dict]:
        rewrites = new_diffs(install_dir, saved_games_dir, removals, lua_interpreter)
        try:
            for r in rewrites:
                if r["diff"] is None:
                    r["path"].unlink(missing_ok=True)
                else:
                    r["path"].parent.mkdir(parents=True, exist_ok=True)
                    write_table(install_dir, r["path"], "diff", r["diff"], lua_interpreter)
        except (OSError, LuaTableError) as error:
            raise DcsConfigError(
                f"Écriture interrompue ({error}) : la sauvegarde d'avant est en tête de liste"
            ) from error
        return rewrites

    return guarded_write(saved_games_dir, backups, reason, change, is_running=is_running)
