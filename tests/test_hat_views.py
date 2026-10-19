import shutil

import pytest

from hotas_kneeboard import hat_views
from hotas_kneeboard.dcs_config import BackupStore, DcsConfigError, remove_bindings
from hotas_kneeboard.hat_views import HAT_VIEWS, plan, remove_hat_views
from hotas_kneeboard.lua_tables import read_table, write_table

from .test_engine import INSTALL, SAVED_GAMES, find_lua51

PEDALS = "Test Pedals {11111111-0000-11ef-8001-444553540000}"
STICK = "Test Stick {22222222-0000-11ef-8001-444553540000}"
# seen by DCS, configured nowhere: it only has the module's defaults
BOX = "Test Box {33333333-0000-11ef-8001-444553540000}"
TRIM_UP = "d3201pnilunilcd40vd1vpnilvunil"
VIEW_DOWN = HAT_VIEWS["JOY_BTN_POV1_D"]


@pytest.fixture(scope="module")
def lua():
    interpreter = find_lua51()
    if not interpreter:
        pytest.skip("no Lua 5.1 interpreter (set DCS_TEST_LUA)")
    return interpreter


@pytest.fixture
def saved(tmp_path):
    copy = tmp_path / "Saved Games" / "DCS"
    shutil.copytree(SAVED_GAMES, copy)
    (copy / "Logs").mkdir()
    (copy / "Logs" / "dcs.log").write_text(
        "".join(
            f"2026-10-19 09:50:50.632 INFO    INPUT (Main): created [{d.split(' {')[0]}] with full id [{d}],JOYSTICK|STANDARD\n"
            for d in (PEDALS, STICK, BOX)
        ),
        encoding="utf-8",
    )
    return copy


def diff_path(saved, device, profile="ViewPlane"):
    return saved / "Config" / "Input" / profile / "joystick" / f"{device}.diff.lua"


@pytest.fixture
def configured(saved, lua):
    """ViewPlane configured: the pedals got a button, the stick its hat (a trim on its top, and the
    view down placed by the user although the defaults have it)"""
    diff_path(saved, PEDALS).parent.mkdir(parents=True)
    write_table(
        INSTALL,
        diff_path(saved, PEDALS),
        "diff",
        {"keyDiffs": {TRIM_UP: {"name": "Trim Up", "added": [{"key": "JOY_BTN2"}]}}},
        lua,
    )
    write_table(
        INSTALL,
        diff_path(saved, STICK),
        "diff",
        {
            "keyDiffs": {
                TRIM_UP: {"name": "Trim Up", "added": [{"key": "JOY_BTN_POV1_U"}]},
                VIEW_DOWN: {"name": "View Down slow", "added": [{"key": "JOY_BTN_POV1_D"}]},
            }
        },
        lua,
    )
    return saved


def closed():
    return False


def by_device(devices):
    return {d["device"]: d for d in devices}


def key_bindings(saved, lua, device, profile="ViewPlane"):
    from hotas_kneeboard.engine import load_effective_bindings

    result = load_effective_bindings(INSTALL, saved, [profile], lua, extra_devices=[device])
    found = next(d for d in result["profiles"][profile]["devices"] if d["name"] == device)
    return {(b["hash"], b["key"]) for b in found["bindings"] if b["kind"] == "key"}


def test_the_default_selection_is_the_devices_whose_hat_the_user_left_alone(lua, configured):
    devices = by_device(plan(INSTALL, configured, lua_interpreter=lua))
    assert set(devices) == {PEDALS, STICK, BOX}
    assert devices[PEDALS]["hat_only_views"] and devices[BOX]["hat_only_views"]
    assert not devices[STICK]["hat_only_views"]
    assert {(b["key"], b["command"]) for b in devices[STICK]["own_hat"]} == {
        ("JOY_BTN_POV1_U", "Trim Up"),
        ("JOY_BTN_POV1_D", "View Down slow"),
    }
    [pedals] = devices[PEDALS]["modules"]
    assert pedals["profile"] == "ViewPlane" and pedals["unit_type"] == "ViewPlane"
    assert pedals["views"] == sorted(HAT_VIEWS) and not pedals["new_file"]
    assert devices[BOX]["modules"][0]["new_file"]
    # DCS keeps the view under the trim the user added on the same key; the view down is the user's
    assert set(devices[STICK]["modules"][0]["views"]) == set(HAT_VIEWS) - {"JOY_BTN_POV1_D"}


def test_the_default_removal_leaves_a_used_hat_alone(lua, configured, tmp_path):
    stick = diff_path(configured, STICK).read_bytes()
    backups = BackupStore(tmp_path / "backups")
    result = remove_hat_views(
        INSTALL, configured, backups, [PEDALS, STICK, BOX], is_running=closed, lua_interpreter=lua
    )
    assert result["differences"] == []
    assert [b.reason for b in backups.list()] == ["avant le retrait des vues du chapeau (2 périphériques)"]
    assert {(w["device"], w["removed"], w["created"]) for w in result["written"]} == {
        (PEDALS, 8, False),
        (BOX, 8, True),
    }
    assert diff_path(configured, STICK).read_bytes() == stick
    pedals = read_table(INSTALL, diff_path(configured, PEDALS), lua)["keyDiffs"]
    assert pedals[HAT_VIEWS["JOY_BTN_POV1_U"]] == {
        "name": "View Up slow",
        "removed": [{"key": "JOY_BTN_POV1_U"}],
    }
    assert pedals[TRIM_UP] == {"name": "Trim Up", "added": [{"key": "JOY_BTN2"}]}
    for device in (PEDALS, BOX):
        assert not {(h, k) for k, h in HAT_VIEWS.items()} & key_bindings(configured, lua, device)


def test_every_device_keeps_the_hat_bindings_the_user_placed(lua, configured, tmp_path):
    result = remove_hat_views(
        INSTALL,
        configured,
        BackupStore(tmp_path / "backups"),
        [STICK],
        every_device=True,
        is_running=closed,
        lua_interpreter=lua,
    )
    assert result["differences"] == []
    assert [(w["device"], w["removed"]) for w in result["written"]] == [(STICK, 7)]
    left = key_bindings(configured, lua, STICK)
    assert {(TRIM_UP, "JOY_BTN_POV1_U"), (VIEW_DOWN, "JOY_BTN_POV1_D")} <= left
    assert not {(h, k) for k, h in HAT_VIEWS.items() if k not in ("JOY_BTN_POV1_D",)} & left


def test_all_installed_modules_covers_a_module_without_a_user_diff(lua, saved, tmp_path):
    assert all(
        m["profile"] != "ViewPlane" for d in plan(INSTALL, saved, lua_interpreter=lua) for m in d["modules"]
    )
    devices = by_device(plan(INSTALL, saved, all_modules=True, lua_interpreter=lua))
    assert set(devices) == {PEDALS, STICK, BOX}
    assert all(m["profile"] == "ViewPlane" and m["new_file"] for d in devices.values() for m in d["modules"])

    result = remove_hat_views(
        INSTALL,
        saved,
        BackupStore(tmp_path / "backups"),
        [PEDALS, STICK, BOX],
        all_modules=True,
        is_running=closed,
        lua_interpreter=lua,
    )
    assert result["differences"] == []
    assert sorted(w["device"] for w in result["written"] if w["created"]) == sorted([PEDALS, STICK, BOX])
    # DCS's spelling of each device names its new file
    for device in (PEDALS, STICK, BOX):
        assert diff_path(saved, device).is_file()


def test_a_device_dcs_did_not_see_gets_no_new_file(lua, saved):
    log = (saved / "Logs" / "dcs.log").read_text(encoding="utf-8")
    (saved / "Logs" / "dcs.log").write_text(log.splitlines(keepends=True)[2], encoding="utf-8")
    assert [d["device"] for d in plan(INSTALL, saved, all_modules=True, lua_interpreter=lua)] == [BOX]


def test_without_a_log_the_devices_with_a_diff_get_one(lua, saved):
    (saved / "Logs" / "dcs.log").unlink()
    devices = plan(INSTALL, saved, all_modules=True, lua_interpreter=lua)
    assert [d["device"] for d in devices] == [
        "Fake Stick {84180FE0-BDD3-11ea-8001-444553540000}",
        "Fake Throttle {84180FE0-BDD3-11ea-8002-444553540000}",
    ]


def test_nothing_to_remove_is_refused_before_any_backup(lua, configured, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    with pytest.raises(DcsConfigError, match="Aucune vue"):
        remove_hat_views(INSTALL, configured, backups, [STICK], is_running=closed, lua_interpreter=lua)
    assert backups.list() == []


def test_a_device_where_nothing_was_found_is_not_written(lua, saved, tmp_path):
    _, rewrites = remove_bindings(
        INSTALL,
        saved,
        BackupStore(tmp_path / "backups"),
        [{"profile": "ViewPlane", "device": BOX, "hash": TRIM_UP, "key": "JOY_BTN30"}],
        "essai",
        is_running=closed,
        lua_interpreter=lua,
    )
    assert [(r["removed"], r["written"]) for r in rewrites] == [(0, False)]
    assert not diff_path(saved, BOX).exists()


def test_a_view_still_there_after_the_write_is_reported(lua, configured, tmp_path, monkeypatch):
    def nothing_written(install, saved, backups, removals, reason, **kwargs):
        backup = backups.create(saved / "Config" / "Input", reason)
        devices = {(r["profile"], r["device"]) for r in removals}
        counts = {key: sum((r["profile"], r["device"]) == key for r in removals) for key in devices}
        return backup, [
            {"profile": p, "device": d, "removed": n, "written": True, "diff": {}}
            for (p, d), n in counts.items()
        ]

    monkeypatch.setattr(hat_views, "remove_bindings", nothing_written)
    result = remove_hat_views(
        INSTALL,
        configured,
        BackupStore(tmp_path / "backups"),
        [PEDALS],
        is_running=closed,
        lua_interpreter=lua,
    )
    assert len(result["differences"]) == 1
    assert result["differences"][0].startswith(f"{PEDALS} (ViewPlane) : encore ")


@pytest.fixture
def client(lua, configured, tmp_path):
    from fastapi.testclient import TestClient

    from hotas_kneeboard.app import create_app
    from hotas_kneeboard.settings import Settings, SettingsStore
    from hotas_kneeboard.templates import TemplateLibrary

    store = SettingsStore(tmp_path / "data" / "settings.json")
    store.save(Settings(dcs_install_dir=str(INSTALL), saved_games_dir=str(configured)))
    app = create_app(
        store,
        TemplateLibrary([tmp_path / "templates"], user_dir=tmp_path / "user"),
        lua_interpreter=lua,
        backups=BackupStore(tmp_path / "backups"),
        is_dcs_running=closed,
    )
    return TestClient(app, base_url="http://127.0.0.1:8642")


def test_the_api_previews_then_removes_and_the_pages_follow(client):
    def pedal_views():
        profiles = client.get("/api/bindings").json()["profiles"]
        pedals = next(
            d for p in profiles if p["name"] == "ViewPlane" for d in p["devices"] if d["full_name"] == PEDALS
        )
        return [key for key in pedals["inputs"] if "POV" in key]

    preview = client.get("/api/dcs-config/hat-views").json()
    assert {d["device"]: d["hat_only_views"] for d in preview["devices"]} == {
        PEDALS: True,
        STICK: False,
        BOX: True,
    }
    before = pedal_views()
    response = client.post("/api/dcs-config/hat-views", json={"devices": [PEDALS]})
    assert response.status_code == 200, response.text
    assert response.json()["differences"] == []
    assert before and pedal_views() == []
    assert [d["device"] for d in client.get("/api/dcs-config/hat-views").json()["devices"]] == [BOX, STICK]


def test_a_diff_shipped_with_the_module_is_not_the_users(lua, saved, tmp_path):
    install = tmp_path / "DCS World"
    shutil.copytree(INSTALL, install)
    write_table(
        install,
        install / "Mods/aircraft/ViewPlane/Input/ViewPlane/joystick/Test Box.diff.lua",
        "diff",
        {"keyDiffs": {TRIM_UP: {"name": "Trim Up", "added": [{"key": "JOY_BTN_POV1_L"}]}}},
        lua,
    )
    devices = by_device(plan(install, saved, all_modules=True, lua_interpreter=lua))
    assert devices[BOX]["hat_only_views"] and devices[BOX]["own_hat"] == []
