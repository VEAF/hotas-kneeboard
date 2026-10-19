"""MkDocs hook: the README is the site's home page.

The README stays the single source (GitHub shows it on the repository's page): its links into
``docs/`` are rewritten for the site, and its links to files outside the site point to GitHub.
"""

import re
from pathlib import Path

from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parent.parent
BLOB = "https://github.com/VEAF/hotas-kneeboard/blob/develop"
_LINK = re.compile(r"\]\((?!https?://|#)([^)]+)\)")


def _site_link(match: re.Match) -> str:
    target = match[1]
    if target.startswith("docs/"):
        return f"]({target.removeprefix('docs/')})"
    return f"]({BLOB}/{target})"


def on_files(files, config):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    files.append(File.generated(config, "index.md", content=_LINK.sub(_site_link, readme)))
    return files
