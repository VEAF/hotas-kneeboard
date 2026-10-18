import base64

import pytest
from fastapi.testclient import TestClient

from hotas_kneeboard.app import create_app
from hotas_kneeboard.kneeboard import PNG_SIGNATURE
from hotas_kneeboard.settings import Settings, SettingsStore
from hotas_kneeboard.templates import TemplateLibrary

from .test_engine import INSTALL, SAVED_GAMES, STICK, find_lua51
from .test_templates import make_template


@pytest.fixture
def client(tmp_path):
    lua = find_lua51()
    if not lua:
        pytest.skip("no Lua 5.1 interpreter (set DCS_TEST_LUA)")
    store = SettingsStore(tmp_path / "data" / "settings.json")
    store.save(Settings(dcs_install_dir=str(INSTALL), saved_games_dir=str(SAVED_GAMES)))
    make_template(tmp_path / "templates", "fake-stick", devices=["Fake Stick"])
    app = create_app(
        store, TemplateLibrary([tmp_path / "templates"], user_dir=tmp_path / "user"), lua_interpreter=lua
    )
    return TestClient(app, base_url="http://127.0.0.1:8642")


def test_state_reports_the_folders(client):
    dcs = client.get("/api/state").json()["dcs"]
    assert dcs["problems"] == []
    assert dcs["install_detected"] is False


def test_bindings_give_pages_with_their_template(client):
    data = client.get("/api/bindings").json()
    assert data["error"] is None
    profiles = {p["name"]: p for p in data["profiles"]}
    assert set(profiles) == {"CommunityPlane", "FakePlane", "MissingPlane", "SecondPlane_pilot", "UiLayer"}
    fake = profiles["FakePlane"]
    assert fake["unit_type"] == "FakePlane"
    stick = next(d for d in fake["devices"] if d["full_name"] == STICK)
    assert stick["name"] == "Fake Stick"
    assert stick["auto_template_id"] == "fake-stick"
    assert stick["inputs"]["JOY_BTN8"][""]["text"] == "Gear Up / Down"
    assert stick["inputs"]["JOY_BTN4"]["JOY_BTN5"]["text"] == "Master Arm"


def test_hidden_devices_are_saved(client):
    response = client.put("/api/settings", json={"hidden_devices": ["vJoy Device"]})
    assert response.status_code == 200
    state = client.get("/api/state").json()
    assert state["settings"]["hidden_devices"] == ["vJoy Device"]
    assert state["settings_file"].endswith("settings.json")


def test_settings_are_validated_and_saved(client):
    response = client.put(
        "/api/settings", json={"layer_mode": "split", "exported": {"FakePlane": {"Fake Stick": False}}}
    )
    assert response.status_code == 200
    assert client.get("/api/state").json()["settings"]["layer_mode"] == "split"
    assert client.put("/api/settings", json={"layer_mode": "nope"}).status_code == 422


def test_missing_folders_are_reported(client):
    client.put("/api/settings", json={"saved_games_dir": "Z:/nowhere"})
    assert client.get("/api/bindings").json()["error"].startswith("Pas de Config/Input")


def test_template_and_image(client):
    assert client.get("/api/templates").json()[0]["id"] == "fake-stick"
    assert client.get("/api/templates/fake-stick").json()["inputs"]["JOY_BTN1"]["anchor"] == [5, 6]
    image = client.get("/api/templates/fake-stick/image")
    assert image.headers["content-type"] == "image/svg+xml"
    assert client.get("/api/templates/nope").status_code == 404


def test_kneeboard_export(client, tmp_path):
    saved = tmp_path / "saved"
    (saved / "Config" / "Input").mkdir(parents=True)
    client.put("/api/settings", json={"saved_games_dir": str(saved)})
    png = base64.b64encode(PNG_SIGNATURE + b"x").decode()
    response = client.post(
        "/api/kneeboard",
        json={
            "unit_type": "FakePlane",
            "profile": "FakePlane",
            "pages": [{"title": "Fake Stick", "png": png}],
        },
    )
    assert response.status_code == 200, response.text
    assert (saved / "Kneeboard" / "FakePlane" / "HOTAS - FakePlane - 01 Fake Stick.png").is_file()
    bad = client.post("/api/kneeboard", json={"unit_type": "../x", "profile": "FakePlane", "pages": []})
    assert bad.status_code == 422


def test_broken_settings_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert SettingsStore(path).load() == Settings()
    assert (tmp_path / "settings.broken.json").read_text(encoding="utf-8") == "{not json"


def test_requests_from_another_site_are_refused(client):
    # a domain name pointed at 127.0.0.1 (DNS rebinding)
    assert client.get("/api/state", headers={"host": "evil.example"}).status_code == 400
    refused = client.put(
        "/api/settings", json={"layer_mode": "split"}, headers={"origin": "http://evil.example"}
    )
    assert refused.status_code == 403
    allowed = client.put(
        "/api/settings", json={"layer_mode": "split"}, headers={"origin": "http://localhost:5173"}
    )
    assert allowed.status_code == 200


@pytest.mark.parametrize(
    "changes",
    [
        {"dcs_install_dir": r"\\attacker\share"},
        {"saved_games_dir": "//attacker/share"},
        {"exported": None},
        {"exported": {"FakePlane": {"Fake Stick": "yes"}}},
        {"device_order": {"FakePlane": "Fake Stick"}},
        {"device_templates": {"Fake Stick": 3}},
        {"language": "../../x"},
        {"page_height": "big"},
        {"hidden_devices": "vJoy Device"},
        {"hidden_devices": [3]},
    ],
)
def test_invalid_settings_are_refused(client, changes):
    assert client.put("/api/settings", json=changes).status_code == 422


def test_template_image_cannot_run_scripts(client):
    assert client.get("/api/templates/fake-stick/image").headers["content-security-policy"] == "sandbox"


def test_template_made_in_the_editor_is_matched_and_shared(client):
    body = {
        "template": {"name": "Fake Stick v2", "devices": ["Fake Stick"], "size": [10, 10], "inputs": {}},
        "image_name": "photo.png",
        "image": base64.b64encode(b"png").decode(),
    }
    saved = client.post("/api/templates", json=body).json()
    assert saved == saved | {"id": "fake-stick-v2", "user": True}
    devices = client.get("/api/bindings").json()["profiles"]
    stick = next(
        d for p in devices if p["name"] == "FakePlane" for d in p["devices"] if d["name"] == "Fake Stick"
    )
    assert stick["auto_template_id"] == "fake-stick-v2"  # the user's template wins
    # a second one with the same name gets its own id; replacing by id keeps it
    assert client.post("/api/templates", json=body).json()["id"] == "fake-stick-v2-2"
    assert client.post("/api/templates", json=body | {"id": "fake-stick-v2"}).json()["id"] == "fake-stick-v2"

    shared = client.get("/api/templates/fake-stick-v2/file")
    assert shared.headers["content-type"] == "application/zip"
    imported = client.post("/api/templates/import", json={"file": base64.b64encode(shared.content).decode()})
    assert imported.json()["id"] == "fake-stick-v2-3"

    client.put(
        "/api/settings", json={"device_templates": {"Fake Stick": "fake-stick-v2", "Other": "fake-stick"}}
    )
    assert client.delete("/api/templates/fake-stick-v2").status_code == 200
    # the device given the deleted template by hand goes back to the automatic match
    assert client.get("/api/state").json()["settings"]["device_templates"] == {"Other": "fake-stick"}
    assert client.delete("/api/templates/fake-stick").status_code == 422  # bundled
    bad = client.post("/api/templates", json=body | {"image_name": "x.exe"})
    assert bad.status_code == 422
