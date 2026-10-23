"""The changelog carries an open `[Unreleased]` section, and the version has its release entry.

A pull request adds its entry at the end of `## [Unreleased]` and does not touch the version; the
release commit (`.claude/commands/release.md`) turns the heading into the version and re-opens an
empty one. VEAF-Mission-Creation-Tools lost the section with a release that forgot to re-open it,
and every pull request then minted its own version heading. These checks bite where that process
rots: no section to write in, a version with no release entry, version files that disagree (which
`release.yml` only finds when publishing).
"""

import re
import tomllib
from pathlib import Path

import hotas_kneeboard

ROOT = Path(__file__).parents[1]
UNRELEASED = "## [Unreleased]"
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_an_unreleased_section_is_open():
    assert UNRELEASED in CHANGELOG, "no `## [Unreleased]` in CHANGELOG.md: a release must re-open one"


def test_unreleased_comes_before_every_version():
    first_version = re.search(r"(?m)^## \[\d+\.\d+\.\d+\]", CHANGELOG)
    assert first_version, "no version heading in CHANGELOG.md"
    assert CHANGELOG.index(UNRELEASED) < first_version.start(), "`## [Unreleased]` must come first"


def test_the_version_has_its_release_entry():
    assert re.search(rf"(?m)^## \[{re.escape(VERSION)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", CHANGELOG), (
        f"no `## [{VERSION}] - YYYY-MM-DD` heading for the version of pyproject.toml"
    )


def test_the_version_files_agree():
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = next(p["version"] for p in lock["package"] if p["name"] == "hotas-kneeboard")
    assert hotas_kneeboard.__version__ == VERSION, "hotas_kneeboard/__init__.py and pyproject.toml disagree"
    assert locked == VERSION, "uv.lock is not up to date with pyproject.toml: run `uv lock`"
