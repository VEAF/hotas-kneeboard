from pathlib import Path

import pytest

from hotas_kneeboard.programs import (
    SRS,
    VECTORXR,
    ProgramBinding,
    match_srs_profile,
    normalize_guid,
    read_programs,
    read_srs_profile,
    read_vectorxr,
    srs_action,
)
from hotas_kneeboard.settings import Settings

# reduced copies of the reference PC's files (SRS profiles, VectorXR settings)
FIXTURE = Path(__file__).parent / "programs_fixture"
SRS_DIR = FIXTURE / "SRS"
VECTORXR_FILE = FIXTURE / "LocalAppData" / "VectorXR" / "config" / "settings.json"
THROTTLE = "d281fb60-b9ad-11f0-8001-444553540000"
STICK = "84180fe0-bdd3-11ea-8001-444553540000"


def test_srs_buttons_count_from_zero():
    found = read_srs_profile(SRS_DIR / "Client" / "F-16.cfg")
    # the keyboard's PTT is not on any device page
    assert found == [
        ProgramBinding(SRS, THROTTLE, "JOY_BTN24", "Radio 1"),
        ProgramBinding(SRS, THROTTLE, "JOY_BTN22", "Radio 2"),
        ProgramBinding(SRS, STICK, "JOY_BTN_POV2_R", "Interphone (modificateur)"),
    ]


@pytest.mark.parametrize(
    ("section", "label"),
    [
        ("Ptt", "PTT radio"),
        ("Switch10", "Radio 10"),
        ("NextRadio", "Radio suivante"),
        ("SomethingNew", "Something New"),
    ],
)
def test_srs_action_names(section, label):
    assert srs_action(section) == label


@pytest.mark.parametrize(
    ("dcs", "srs"),
    [
        ("F-16C_50", "F-16"),
        ("A-10C II", "A-10C"),
        ("AH-64D_BLK_II_PLT", "AH-64D"),
        ("FA-18C_hornet", "FA-18C"),
        ("Mi-24P_pilot", "Mi-24P"),
        ("UiLayer", "default"),
    ],
)
def test_srs_profile_matched_by_name(dcs, srs):
    names = ["A-10C", "AH-64D", "default", "F-16", "F-15E", "FA-18C", "Mi-24P"]
    assert match_srs_profile(dcs, names) == srs


def test_no_srs_profile_without_default():
    assert match_srs_profile("UiLayer", ["F-16"]) is None


def test_vectorxr_reads_what_is_in_use_in_dcs():
    found = read_vectorxr(VECTORXR_FILE)
    # a profile of another program and a profile switched off are left out; a module saved off
    # (PivotXR on the reference PC, DepthXR switched by its own button) still has its buttons
    assert found == [
        ProgramBinding(VECTORXR, THROTTLE, "JOY_BTN55", "Overlay : afficher / masquer"),
        ProgramBinding(VECTORXR, THROTTLE, "JOY_BTN51", "PivotXR snapviews : recentrer"),
        ProgramBinding(VECTORXR, THROTTLE, "JOY_BTN54", "PivotXR snapviews : vue Right MFD"),
        ProgramBinding(VECTORXR, THROTTLE, "JOY_BTN52", "PivotXR snapviews : vue Left MFD"),
        ProgramBinding(VECTORXR, THROTTLE, "JOY_BTN53", "PivotXR enhanced motion : activer"),
        ProgramBinding(VECTORXR, THROTTLE, "JOY_BTN70", "DepthXR : activer / désactiver"),
    ]


def test_guid_written_either_way():
    assert normalize_guid("{D281FB60-B9AD-11F0-8001-444553540000}") == THROTTLE


def test_read_programs(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(FIXTURE / "LocalAppData"))
    result = read_programs(str(SRS_DIR), ["F-16C_50", "UiLayer"])
    assert result["problems"] == []
    assert result["srs"]["profiles"] == ["default", "F-16"]
    assert result["srs"]["matched"] == {"F-16C_50": "F-16", "UiLayer": "default"}
    assert result["srs"]["bindings"]["default"] == [
        {"program": SRS, "device_guid": THROTTLE, "input": "JOY_BTN56", "action": "Radio 3"}
    ]
    assert len(result["vectorxr"]["bindings"]) == 6


def test_missing_srs_folder_is_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    result = read_programs(str(tmp_path / "nowhere"), ["F-16C_50"])
    assert result["srs"]["folder"] is None
    assert result["vectorxr"]["file"] is None
    assert len(result["problems"]) == 1


def manual(**changes) -> dict:
    return {
        "program": "VoiceAttack",
        "device_guid": THROTTLE,
        "device_name": "Orion Throttle",
        "input": "JOY_BTN30",
        "action": "Écoute",
    } | changes


@pytest.mark.parametrize(
    "changes",
    [
        {"program_bindings": [manual(input="Button 30")]},
        {"program_bindings": [manual(program=" ")]},
        {"program_bindings": [{"program": "VoiceAttack"}]},
        {"program_colors": {"SRS": "blue"}},
        {"hidden_programs": "SRS"},
        {"srs_profiles": {"F-16C_50": 3}},
        {"srs_dir": "//server/share"},
    ],
)
def test_invalid_program_settings_are_refused(changes):
    with pytest.raises(ValueError):
        Settings.from_dict(changes)


def test_program_settings_are_kept():
    settings = Settings.from_dict(
        {
            "program_bindings": [manual()],
            "program_colors": {"SRS": "#1d5fbf"},
            "srs_profiles": {"UiLayer": ""},
        }
    )
    assert settings.program_bindings == [manual()]
