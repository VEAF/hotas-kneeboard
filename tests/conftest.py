import pytest


@pytest.fixture(autouse=True)
def french(monkeypatch):
    """The messages the tests read are the French ones, as the app speaks to a French interface;
    test_i18n.py checks the English ones and the choice of the language."""
    monkeypatch.setenv("HOTAS_KNEEBOARD_LANG", "fr")
