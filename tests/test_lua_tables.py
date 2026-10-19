import shutil
from pathlib import Path

import pytest

from hotas_kneeboard.dcs_config import (
    BackupStore,
    DcsConfigError,
    disabled_devices,
    read_disabled,
    seen_devices,
    set_device_disabled,
)
from hotas_kneeboard.lua_tables import read_table, to_lua, write_table

from .test_engine import INSTALL, SAVED_GAMES, find_lua51

DISABLED = SAVED_GAMES / "Config" / "Input" / "disabled.lua"
GHOST = "Ghost Pad {AAAA0000-0000-11ef-8001-444553540000}"
# a value shaped like a real diff: nested lists, numbers, booleans, a key needing escapes
SAMPLE = {
    "axisDiffs": {
        "a2001cdnil": {
            "changed": [
                {
                    "filter": {"curvature": [0.1], "deadzone": 0, "invert": False, "slider": True},
                    "key": "JOY_Y",
                }
            ],
            "name": 'Roll "fast" \\ é\n',
        }
    },
    "keyDiffs": {
        "d1054pnilu1054cd": {"name": "Gear", "removed": [{"key": "JOY_BTN21", "reformers": ["JOY_BTN4"]}]}
    },
}


@pytest.fixture(scope="module")
def lua():
    interpreter = find_lua51()
    if not interpreter:
        pytest.skip("no Lua 5.1 interpreter (set DCS_TEST_LUA)")
    return interpreter


def real_install(lua: str) -> Path | None:
    """The DCS install of DCS_TEST_LUA when it is bin/luae.exe of a real one"""
    install = Path(lua).parent.parent
    return install if (install / "Scripts" / "Serializer.lua").is_file() and install != INSTALL else None


def test_a_file_written_as_dcs_reads_back_identical(lua, tmp_path):
    out = tmp_path / "x.diff.lua"
    write_table(INSTALL, out, "diff", SAMPLE, lua)
    assert read_table(INSTALL, out, lua) == SAMPLE
    assert out.read_bytes().endswith(b"}\nreturn diff")
    assert b"\r" not in out.read_bytes()


def test_a_dcs_file_is_rewritten_byte_for_byte(lua, tmp_path):
    out = tmp_path / "disabled.lua"
    write_table(INSTALL, out, "disabled", read_table(INSTALL, DISABLED, lua), lua)
    assert out.read_bytes() == DISABLED.read_bytes()


def test_the_test_serializer_writes_what_dcs_writes(lua, tmp_path):
    install = real_install(lua)
    if not install:
        pytest.skip("no DCS install (DCS_TEST_LUA = <DCS>/bin/luae.exe)")
    write_table(install, tmp_path / "dcs.lua", "diff", SAMPLE, lua)
    write_table(INSTALL, tmp_path / "standin.lua", "diff", SAMPLE, lua)
    assert (tmp_path / "dcs.lua").read_bytes() == (tmp_path / "standin.lua").read_bytes()


def test_lua_source_is_plain_ascii():
    source = to_lua({"k": 'é\r\x1a"\\'})
    assert source.isascii()
    assert "\r" not in source and "\x1a" not in source


@pytest.fixture
def saved(tmp_path):
    copy = tmp_path / "Saved Games" / "DCS"
    shutil.copytree(SAVED_GAMES, copy)
    return copy


def closed():
    return False


def test_disable_and_enable_a_device(lua, saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    stick = "Fake Stick {84180FE0-BDD3-11ea-8001-444553540000}"
    set_device_disabled(INSTALL, saved, backups, stick, True, is_running=closed, lua_interpreter=lua)
    assert disabled_devices(INSTALL, saved, lua) == sorted([GHOST, stick])
    assert read_disabled(INSTALL, saved, lua)["pnp"] is False

    set_device_disabled(INSTALL, saved, backups, GHOST, False, is_running=closed, lua_interpreter=lua)
    assert disabled_devices(INSTALL, saved, lua) == [stick]
    assert [b.reason for b in backups.list()] == [
        f"avant la réactivation de {GHOST}",
        f"avant la désactivation de {stick}",
    ]


def test_the_device_takes_the_spelling_dcs_logged(lua, saved, tmp_path):
    (saved / "Logs").mkdir()
    logged = "Fake Stick {84180fe0-bdd3-11ea-8001-444553540000}"
    (saved / "Logs" / "dcs.log").write_text(
        f"2026-10-18 16:42:54.566 INFO    INPUT (Main): created [Fake Stick] with full id [{logged}],JOYSTICK|STANDARD\n",
        encoding="utf-8",
    )
    assert seen_devices(saved) == [logged]
    backups = BackupStore(tmp_path / "backups")
    set_device_disabled(INSTALL, saved, backups, logged.upper(), True, is_running=closed, lua_interpreter=lua)
    assert logged in disabled_devices(INSTALL, saved, lua)


def test_nothing_is_disabled_while_dcs_runs(lua, saved, tmp_path):
    before = DISABLED.read_bytes()
    with pytest.raises(DcsConfigError, match="DCS est lancé"):
        set_device_disabled(
            INSTALL,
            saved,
            BackupStore(tmp_path / "b"),
            GHOST,
            False,
            is_running=lambda: True,
            lua_interpreter=lua,
        )
    assert (saved / "Config" / "Input" / "disabled.lua").read_bytes() == before


def test_a_device_keeps_the_spelling_disabled_lua_uses(lua, saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    set_device_disabled(INSTALL, saved, backups, GHOST.upper(), True, is_running=closed, lua_interpreter=lua)
    assert disabled_devices(INSTALL, saved, lua) == [GHOST]


@pytest.fixture
def make_client(lua, saved, tmp_path):
    from fastapi.testclient import TestClient

    from hotas_kneeboard.app import create_app
    from hotas_kneeboard.settings import Settings, SettingsStore
    from hotas_kneeboard.templates import TemplateLibrary

    def make(running=False):
        store = SettingsStore(tmp_path / "data" / "settings.json")
        store.save(Settings(dcs_install_dir=str(INSTALL), saved_games_dir=str(saved)))
        app = create_app(
            store,
            TemplateLibrary([tmp_path / "templates"], user_dir=tmp_path / "user"),
            lua_interpreter=lua,
            backups=BackupStore(tmp_path / "backups"),
            is_dcs_running=lambda: running,
        )
        return TestClient(app, base_url="http://127.0.0.1:8642")

    return make


def test_the_api_disables_a_device_and_the_pages_say_so(make_client):
    client = make_client()
    stick = "Fake Stick {84180FE0-BDD3-11ea-8001-444553540000}"
    assert client.get("/api/dcs-config/devices").json()["disabled"] == [GHOST]
    client.get("/api/bindings")  # fills the cache, which the change must invalidate
    response = client.put("/api/dcs-config/devices/disabled", json={"device": stick, "disabled": True})
    assert response.status_code == 200
    assert client.get("/api/dcs-config/devices").json()["disabled"] == sorted([GHOST, stick])
    fake = next(p for p in client.get("/api/bindings").json()["profiles"] if p["name"] == "FakePlane")
    assert next(d for d in fake["devices"] if d["full_name"] == stick)["dcs_disabled"] is True


def test_the_api_refuses_to_disable_while_dcs_runs(make_client, saved):
    before = (saved / "Config" / "Input" / "disabled.lua").read_bytes()
    response = make_client(running=True).put(
        "/api/dcs-config/devices/disabled", json={"device": GHOST, "disabled": False}
    )
    assert response.status_code == 409
    assert (saved / "Config" / "Input" / "disabled.lua").read_bytes() == before
