import json

import pytest

from hotas_kneeboard.templates import BUNDLED_DIR, TemplateError, TemplateLibrary, validate


def make_template(root, folder, **overrides):
    path = root / folder
    path.mkdir(parents=True)
    (path / "background.svg").write_text("<svg/>", encoding="utf-8")
    data = {
        "format": 1,
        "name": folder,
        "devices": [folder],
        "image": "background.svg",
        "size": [100, 200],
        "inputs": {"JOY_BTN1": {"box": [1, 2, 3, 4], "anchor": [5, 6]}},
    } | overrides
    (path / "template.json").write_text(json.dumps(data), encoding="utf-8")
    return path


def test_match_ignores_case(tmp_path):
    make_template(tmp_path, "Throttle - HOTAS Warthog")
    library = TemplateLibrary([tmp_path])
    assert library.match("throttle - hotas warthog").id == "Throttle - HOTAS Warthog"
    assert library.match("Unknown") is None


def test_user_template_wins_over_bundled_one(tmp_path):
    make_template(tmp_path / "bundled", "warthog", name="bundled")
    make_template(tmp_path / "user", "warthog", name="user")
    library = TemplateLibrary([tmp_path / "bundled", tmp_path / "user"])
    assert library.get("warthog").data["name"] == "user"


def test_invalid_template_is_skipped(tmp_path):
    make_template(tmp_path, "bad", inputs={"JOY_BTN1": {"box": [1, 2]}})
    make_template(tmp_path, "good")
    assert list(TemplateLibrary([tmp_path]).templates) == ["good"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"format": 2}, "format"),
        ({"image": "../x.svg"}, "file name"),
        ({"image": "x.gif"}, "image must be one of"),
        ({"image": "missing.svg"}, "not found"),
        ({"size": [1]}, "size"),
        ({"inputs": {"JOY_BTN1": {"box": [1, 2, 3, 4], "anchor": [1]}}}, "anchor"),
    ],
)
def test_validation(tmp_path, overrides, message):
    path = make_template(tmp_path, "t")
    data = json.loads((path / "template.json").read_text()) | overrides
    with pytest.raises(TemplateError, match=message):
        validate(data, path)


def test_bundled_library_is_valid():
    library = TemplateLibrary([BUNDLED_DIR])
    folders = [p for p in BUNDLED_DIR.iterdir() if p.is_dir()] if BUNDLED_DIR.is_dir() else []
    assert len(library.templates) == len(folders)


def test_user_templates_save_export_import_delete(tmp_path):
    make_template(tmp_path / "bundled", "warthog", devices=["Throttle - HOTAS Warthog"])
    library = TemplateLibrary([tmp_path / "bundled"], user_dir=tmp_path / "user")
    data = {
        "name": "My ICP",
        "devices": ["WINWING ICP"],
        "size": [100, 50],
        "inputs": {"JOY_BTN1": {"box": [1, 2, 3, 4], "anchor": [9, 9]}},
    }
    saved = library.save("my-icp", data, "photo.PNG", b"\x89PNG data")
    assert saved.user
    assert saved.data["image"] == "background.png"
    assert library.match("winwing icp").id == "my-icp"
    assert library.get("warthog").user is False

    # replacing keeps one folder, with the new content
    library.save("my-icp", data | {"name": "My ICP v2"}, "photo.jpg", b"jpeg")
    assert [p.name for p in (tmp_path / "user").iterdir()] == ["my-icp"]
    assert library.get("my-icp").data["image"] == "background.jpg"

    shared = library.export_file("my-icp")
    imported = library.import_file(shared)
    assert imported.id == "my-icp-v2"
    assert imported.data["inputs"] == data["inputs"]

    library.delete("my-icp")
    assert library.get("my-icp") is None
    with pytest.raises(TemplateError):
        library.delete("warthog")  # bundled


def test_user_template_wins_the_automatic_match(tmp_path):
    make_template(tmp_path / "bundled", "warthog", devices=["Stick"])
    make_template(tmp_path / "user", "mine", devices=["Stick"])
    library = TemplateLibrary([tmp_path / "bundled"], user_dir=tmp_path / "user")
    assert library.match("Stick").id == "mine"


@pytest.mark.parametrize(
    ("template_id", "image_name", "message"),
    [("../evil", "a.png", "identifiant"), ("ok", "a.exe", "image"), ("Bad Id", "a.png", "identifiant")],
)
def test_save_refuses_bad_input(tmp_path, template_id, image_name, message):
    library = TemplateLibrary([], user_dir=tmp_path / "user")
    data = {"name": "x", "size": [1, 1], "inputs": {}}
    with pytest.raises(TemplateError, match=message):
        library.save(template_id, data, image_name, b"x")


def test_invalid_template_is_not_saved(tmp_path):
    library = TemplateLibrary([], user_dir=tmp_path / "user")
    with pytest.raises(TemplateError):
        library.save("t", {"name": "x", "size": [1], "inputs": {}}, "a.png", b"x")
    assert not list((tmp_path / "user").iterdir())


def test_import_refuses_other_files(tmp_path):
    library = TemplateLibrary([], user_dir=tmp_path / "user")
    with pytest.raises(TemplateError, match="invalide"):
        library.import_file(b"not a zip")
