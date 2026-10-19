"""MkDocs hook: the README is the site's home page, in both languages.

The README stays the single source (GitHub shows it on the repository's page). It holds the
English text, then the French one from ``<a id="fr"></a>``, as VEAF-Mission-Creation-Tools does: the
English part becomes ``docs/index.en.md``, the French one ``docs/index.md`` (mkdocs-static-i18n,
suffix structure). The line that jumps to the other language goes, the site has its own language
switcher; the links into ``docs/`` are rewritten for the site, the links to files outside the site
point to GitHub.

The two pages are written into ``docs/`` (ignored by git) when the build starts, before the files
are gathered: mkdocs-static-i18n only sorts by language the files that come from there. A page is
written only when it changes, so that ``mkdocs serve`` does not rebuild in a loop.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOB = "https://github.com/VEAF/hotas-kneeboard/blob/develop"
_LINK = re.compile(r"\]\((?!https?://|#)([^)]+)\)")
_FRENCH = '<a id="fr"></a>'
# the anchors and the "read it in the other language" lines, for GitHub only
_GITHUB_ONLY = re.compile(r'^(<a id="(en|fr)"></a>|> 🇫🇷 .*|> 🇬🇧 .*)\n', re.MULTILINE)


def _site_link(match: re.Match) -> str:
    target = match[1]
    if target.startswith("docs/"):
        return f"]({target.removeprefix('docs/')})"
    return f"]({BLOB}/{target})"


def split_readme(readme: str) -> dict[str, str]:
    """``{"index.en.md": English part, "index.md": French part}``, ready for the site"""
    english, french = readme.split(_FRENCH, 1)
    # the rule between the two languages, not any other one
    english = english.rstrip().removesuffix("---")
    return {
        name: _LINK.sub(_site_link, _GITHUB_ONLY.sub("", text)).strip() + "\n"
        for name, text in (("index.en.md", english), ("index.md", french))
    }


def on_config(config):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name, content in split_readme(readme).items():
        page = Path(config.docs_dir) / name
        if not page.is_file() or page.read_text(encoding="utf-8") != content:
            page.write_text(content, encoding="utf-8")
    return config
