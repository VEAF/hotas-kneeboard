import zipfile

import pytest
from fastapi.testclient import TestClient

from hotas_kneeboard.app import create_app
from hotas_kneeboard.dcs_config import BackupStore, DcsConfigError, guarded_write, restore
from hotas_kneeboard.settings import Settings, SettingsStore
from hotas_kneeboard.templates import TemplateLibrary


def snapshot(folder):
    """Every file and folder under ``folder`` with its bytes (None for a folder)."""
    return {
        p.relative_to(folder).as_posix(): (None if p.is_dir() else p.read_bytes()) for p in folder.rglob("*")
    }


@pytest.fixture
def saved(tmp_path):
    saved = tmp_path / "Saved Games" / "DCS"
    joystick = saved / "Config" / "Input" / "A-10C II" / "joystick"
    joystick.mkdir(parents=True)
    (joystick / "Stick {1}.diff.lua").write_bytes(b"local diff = {}\nreturn diff")
    (saved / "Config" / "Input" / "disabled.lua").write_text("return {}", encoding="utf-8")
    (saved / "Config" / "Input" / "Empty profile").mkdir()
    return saved


def closed():
    return False


def test_a_restore_gives_the_backup_back_byte_for_byte(saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    input_dir = saved / "Config" / "Input"
    before = snapshot(input_dir)
    first = backups.create(input_dir, "avant essai")
    assert first.reason == "avant essai" and first.files == 2

    (input_dir / "A-10C II" / "joystick" / "Stick {1}.diff.lua").write_bytes(b"changed")
    (input_dir / "F-16C_50").mkdir()
    (input_dir / "F-16C_50" / "new.diff.lua").write_bytes(b"new")
    changed = snapshot(input_dir)

    taken = restore(saved, backups, first.id, closed)
    assert snapshot(input_dir) == before
    assert "restauration" in taken.reason
    # the state before the restore was backed up first
    restore(saved, backups, taken.id, closed)
    assert snapshot(input_dir) == changed
    assert not list(input_dir.parent.glob(".Input.*"))


def test_nothing_is_written_while_dcs_runs(saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    calls = []
    with pytest.raises(DcsConfigError, match="DCS est lancé"):
        guarded_write(saved, backups, "essai", calls.append, is_running=lambda: True)
    assert calls == [] and backups.list() == []


def test_a_change_is_preceded_by_a_backup(saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    seen = []

    def change(input_dir):
        seen.append(len(backups.list()))
        (input_dir / "disabled.lua").write_text("changed", encoding="utf-8")

    backup, _ = guarded_write(saved, backups, "essai", change, is_running=closed)
    assert seen == [1]
    with zipfile.ZipFile(backups.folder / f"config-input-{backup.id}.zip") as archive:
        assert archive.read("disabled.lua") == b"return {}"


def test_only_the_last_backups_are_kept(saved, tmp_path):
    backups = BackupStore(tmp_path / "backups", keep=3)
    ids = [backups.create(saved / "Config" / "Input", f"n{i}").id for i in range(5)]
    assert [b.id for b in backups.list()] == ids[:1:-1]


def test_restoring_the_oldest_backup_keeps_it(saved, tmp_path):
    backups = BackupStore(tmp_path / "backups", keep=2)
    oldest = backups.create(saved / "Config" / "Input", "a").id
    backups.create(saved / "Config" / "Input", "b")
    restore(saved, backups, oldest, closed)
    assert oldest in {b.id for b in backups.list()}


def test_a_backup_cannot_write_outside_the_folder(saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    backup = backups.create(saved / "Config" / "Input", "a")
    path = backups.folder / f"config-input-{backup.id}.zip"
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("../evil.lua", "x")
    before = snapshot(saved / "Config" / "Input")
    with pytest.raises(DcsConfigError, match="invalide"):
        restore(saved, backups, backup.id, closed)
    assert snapshot(saved / "Config" / "Input") == before
    assert not (saved / "Config" / "evil.lua").exists()


def test_a_failed_swap_puts_the_current_state_back(saved, tmp_path, monkeypatch):
    backups = BackupStore(tmp_path / "backups")
    input_dir = saved / "Config" / "Input"
    backup = backups.create(input_dir, "a")
    (input_dir / "disabled.lua").write_text("changed", encoding="utf-8")
    before = snapshot(input_dir)
    real_replace = type(input_dir).replace

    def replace(self, target):
        if self.name.startswith(".Input.restore-"):
            raise OSError("locked")
        return real_replace(self, target)

    monkeypatch.setattr(type(input_dir), "replace", replace)
    with pytest.raises(DcsConfigError, match="n'ont pas changé"):
        restore(saved, backups, backup.id, closed)
    assert snapshot(input_dir) == before
    assert not list(input_dir.parent.glob(".Input.*"))


def test_a_backup_of_an_empty_folder_restores_an_empty_folder(saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    input_dir = saved / "Config" / "Input"
    other = tmp_path / "Other" / "Config" / "Input"
    other.mkdir(parents=True)
    backup = backups.create(other, "vide")
    restore(saved, backups, backup.id, closed)
    assert input_dir.is_dir() and snapshot(input_dir) == {}


def test_backups_made_at_the_same_instant_do_not_overwrite_each_other(saved, tmp_path, monkeypatch):
    from hotas_kneeboard import dcs_config

    instant = dcs_config.datetime(2026, 10, 19, 12, 0, 0)

    class Frozen(dcs_config.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant

    monkeypatch.setattr(dcs_config, "datetime", Frozen)
    backups = BackupStore(tmp_path / "backups")
    first = backups.create(saved / "Config" / "Input", "a")
    second = backups.create(saved / "Config" / "Input", "b")
    assert first.id != second.id
    assert {b.reason for b in backups.list()} == {"a", "b"}


def test_an_unknown_backup_id_is_refused(saved, tmp_path):
    with pytest.raises(DcsConfigError, match="introuvable"):
        restore(saved, BackupStore(tmp_path / "backups"), "../../x", closed)


@pytest.fixture
def make_client(saved, tmp_path):
    def make(running=False):
        store = SettingsStore(tmp_path / "data" / "settings.json")
        store.save(Settings(dcs_install_dir=str(tmp_path), saved_games_dir=str(saved)))
        app = create_app(
            store,
            TemplateLibrary([tmp_path / "templates"], user_dir=tmp_path / "user"),
            lua_interpreter="lua",
            backups=BackupStore(tmp_path / "backups"),
            is_dcs_running=lambda: running,
        )
        return TestClient(app, base_url="http://127.0.0.1:8642")

    return make


def test_the_api_backs_up_lists_and_restores(make_client, saved):
    client = make_client()
    created = client.post("/api/dcs-config/backups").json()
    listing = client.get("/api/dcs-config/backups").json()
    assert listing["dcs_running"] is False
    assert [b["id"] for b in listing["backups"]] == [created["id"]]

    (saved / "Config" / "Input" / "disabled.lua").write_text("changed", encoding="utf-8")
    response = client.post(f"/api/dcs-config/backups/{created['id']}/restore")
    assert response.status_code == 200
    assert (saved / "Config" / "Input" / "disabled.lua").read_text(encoding="utf-8") == "return {}"
    assert len(client.get("/api/dcs-config/backups").json()["backups"]) == 2
    assert client.post("/api/dcs-config/backups/20200101-000000-000000/restore").status_code == 404


def test_the_api_refuses_to_restore_while_dcs_runs(make_client, saved):
    client = make_client(running=True)
    created = client.post("/api/dcs-config/backups").json()
    (saved / "Config" / "Input" / "disabled.lua").write_text("changed", encoding="utf-8")
    response = client.post(f"/api/dcs-config/backups/{created['id']}/restore")
    assert response.status_code == 409
    assert "DCS est lancé" in response.json()["detail"]
    assert (saved / "Config" / "Input" / "disabled.lua").read_text(encoding="utf-8") == "changed"
