"""Changes to DCS's own input files (``Saved Games/DCS/Config/Input``) and their backups.

Every change goes through ``guarded_write``: refused while DCS runs (it rewrites these files when
it saves its controls, and would overwrite ours), preceded by a zip of the whole folder, which the
app lists and restores. Error messages reach the user as they are: they are in French."""

import logging
import shutil
import subprocess
import sys
import uuid
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath

_logger = logging.getLogger(__name__)

# the game and the dedicated server: both save their controls into Config/Input
DCS_PROCESSES = ("dcs.exe", "dcs_server.exe")
KEEP_BACKUPS = 20
BACKUP_PREFIX = "config-input-"
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
