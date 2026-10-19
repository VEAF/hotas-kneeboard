import ast
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from hotas_kneeboard import i18n
from hotas_kneeboard.app import create_app
from hotas_kneeboard.i18n import LanguageMiddleware, language, normalize, t
from hotas_kneeboard.settings import Settings, SettingsStore
from hotas_kneeboard.templates import TemplateLibrary

PACKAGE = Path(i18n.__file__).parent
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def test_catalogs_have_the_same_keys_and_placeholders():
    fr, en = i18n.catalog("fr"), i18n.catalog("en")
    assert set(fr) == set(en)
    different = [k for k in en if sorted(PLACEHOLDER.findall(en[k])) != sorted(PLACEHOLDER.findall(fr[k]))]
    assert different == []
    assert all(text.strip() for text in [*fr.values(), *en.values()])


def test_every_key_the_code_asks_for_is_in_the_catalog():
    used = set()
    for path in PACKAGE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t"):
                continue
            for arg in node.args[:1]:
                # t("a" if x else "b") as well as t("a")
                for leaf in ast.walk(arg):
                    if isinstance(leaf, ast.Constant) and isinstance(leaf.value, str):
                        used.add(leaf.value)
    srs = {f"srs.{section}" for section in __import__("hotas_kneeboard.programs").programs.SRS_ACTIONS}
    catalog = i18n.catalog("en")
    assert sorted(k for k in used if k not in catalog and not k.startswith("srs.")) == []
    assert sorted(k for k in srs if k not in catalog) == []
    assert len(used) > 100


def test_the_language_of_a_request_is_its_accept_language():
    assert normalize("fr-FR,fr;q=0.9,en;q=0.8") == "fr"
    assert normalize("en-GB") == "en"
    assert normalize("de-DE") is None
    assert normalize("") is None


def test_a_message_falls_back_to_english_then_to_its_key():
    with language("fr"):
        assert t("backup.missing") == "sauvegarde introuvable"
        assert t("no.such.key") == "no.such.key"
    with language("en"):
        assert t("backup.missing") == "backup not found"
        assert t("forget.nothing", device="Stick") == "No saved controls for Stick"
    # a placeholder missing gives the text as it is rather than an error on the way to one
    with language("en"):
        assert t("forget.nothing") == "No saved controls for {device}"


def test_out_of_a_request_the_environment_then_english(monkeypatch):
    monkeypatch.setenv("HOTAS_KNEEBOARD_LANG", "fr")
    assert t("backup.missing") == "sauvegarde introuvable"
    monkeypatch.delenv("HOTAS_KNEEBOARD_LANG")
    assert t("backup.missing") == "backup not found"


def test_a_route_answers_in_the_language_asked_sync_routes_included():
    app = FastAPI()
    app.add_middleware(LanguageMiddleware)

    @app.get("/sync")
    def sync_route():  # run in a thread: the language must follow it there
        raise HTTPException(404, t("backup.missing"))

    @app.get("/async")
    async def async_route():
        raise HTTPException(404, t("backup.missing"))

    client = TestClient(app)
    for path in ("/sync", "/async"):
        assert client.get(path, headers={"Accept-Language": "en"}).json()["detail"] == "backup not found"
        assert (
            client.get(path, headers={"Accept-Language": "fr-FR"}).json()["detail"]
            == "sauvegarde introuvable"
        )


def test_the_app_refuses_another_site_in_the_language_asked(tmp_path, monkeypatch):
    monkeypatch.delenv("HOTAS_KNEEBOARD_LANG")
    store = SettingsStore(tmp_path / "settings.json")
    store.save(Settings())
    client = TestClient(
        create_app(store, TemplateLibrary([], user_dir=tmp_path / "user")), base_url="http://127.0.0.1:8642"
    )
    origin = {"Origin": "http://example.com"}
    english = client.post("/api/dcs-config/backups", headers={**origin, "Accept-Language": "en"})
    french = client.post("/api/dcs-config/backups", headers={**origin, "Accept-Language": "fr"})
    assert english.status_code == french.status_code == 403
    assert english.json()["detail"] == "request from another site refused"
    assert french.json()["detail"] == "requête d'un autre site refusée"


def test_the_interface_language_is_a_setting():
    assert Settings.from_dict({"ui_language": "en"}).ui_language == "en"
    assert Settings.from_dict({}).ui_language is None
    try:
        Settings.from_dict({"ui_language": "de"})
    except ValueError as error:
        assert "fr" in str(error)
    else:
        raise AssertionError("an interface language the app does not speak must be refused")
