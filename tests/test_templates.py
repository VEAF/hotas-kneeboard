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
