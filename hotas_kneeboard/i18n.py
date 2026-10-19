"""Messages in the user's language, the way VEAF-Mission-Creation-Tools does it (``veaf_libs/i18n.py``).

One flat JSON catalog per language in ``locales/<lang>.json``, dotted keys, ``{name}`` placeholders.
``en.json`` is the reference: a key missing from another catalog falls back to it, then to the key
itself.

The language is the one of the request being answered: the interface sends its own in
``Accept-Language`` (``LanguageMiddleware``), so a message from the server reads like the
interface around it. Out of a request (the command line, the tests), it is the one set by
``set_language``, else ``HOTAS_KNEEBOARD_LANG``, else English.
"""

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
LANGUAGES = ("fr", "en")
DEFAULT = "en"

_language: ContextVar[str | None] = ContextVar("language", default=None)


def normalize(value: str | None) -> str | None:
    """ "fr-FR,fr;q=0.9" -> "fr"; a language the app does not speak -> None"""
    if not value:
        return None
    code = value.split(",")[0].split(";")[0].strip()[:2].lower()
    return code if code in LANGUAGES else None


@cache
def catalog(language: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{language}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def current_language() -> str:
    return _language.get() or normalize(os.environ.get("HOTAS_KNEEBOARD_LANG")) or DEFAULT


def set_language(language: str | None) -> None:
    """The language of what follows, in this context (a request, a test)"""
    _language.set(normalize(language))


@contextmanager
def language(value: str | None):
    """Temporarily another language"""
    token = _language.set(normalize(value))
    try:
        yield
    finally:
        _language.reset(token)


def t(key: str, /, **kwargs: object) -> str:
    """The text of a key in the current language, its placeholders filled; a placeholder missing
    from ``kwargs`` leaves the text as it is rather than fail on the way to an error message"""
    text = catalog(current_language()).get(key) or catalog(DEFAULT).get(key, key)
    if not kwargs:
        return text
    try:
        return text.format_map(kwargs)
    except (KeyError, ValueError, IndexError):
        return text


class LanguageMiddleware:
    """Answers each request in the language of its ``Accept-Language`` (plain ASGI: the value set
    here is seen by the route, threads of sync routes included)"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        header = dict(scope.get("headers") or []).get(b"accept-language", b"").decode("latin-1")
        token = _language.set(normalize(header))
        try:
            await self.app(scope, receive, send)
        finally:
            _language.reset(token)
