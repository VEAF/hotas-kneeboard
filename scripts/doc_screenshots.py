"""Retakes the screenshots of the documentation (docs/images/) from a running app.

Read-only: it opens screens and dialogs and clicks only what shows a preview ("Chercher"),
never a button that writes to DCS. The app must run with a throwaway HOTAS_KNEEBOARD_DATA
(ticking a buttonless device writes the app's settings):

    $env:HOTAS_KNEEBOARD_DATA = "$env:TEMP\\hk-shots"; uv run hotas-kneeboard --port 8654 --no-browser
    $env:HOTAS_KNEEBOARD_DATA = "$env:TEMP\\hk-shots"; uv run --with playwright python scripts/doc_screenshots.py

The pictures show the devices of the PC that takes them: the script picks the A-10C II, the
WinWing Orion stick and the T-Pendular rudder, change MODULE / STICK / RUDDER for other ones.
The Windows user name and the throwaway data folder are shown as those of an ordinary pilot.
Uses the installed Edge, no browser download.
"""

import argparse
import os
from pathlib import Path

from playwright.sync_api import Browser, Locator, Page, sync_playwright

MODULE = "A-10C II"
STICK = "Orion Joystick"
RUDDER = "T-Pendular-Rudder"
WIDTH, HEIGHT = 1440, 900

SCRUB = """
([pairs]) => {
  const fix = (t) => pairs.reduce((s, [a, b]) => s.replaceAll(a, b), t)
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  let n
  while ((n = w.nextNode())) { const t = fix(n.nodeValue); if (t !== n.nodeValue) n.nodeValue = t }
  for (const i of document.querySelectorAll('input')) {
    const t = fix(i.value); if (t !== i.value) i.value = t
    if (i.placeholder) i.placeholder = fix(i.placeholder)
  }
}
"""

# the biggest picture on the screen: the drawn page
PAGE_BOX = """() => {
  const r = [...document.querySelectorAll('img, canvas, svg')].map(e => e.getBoundingClientRect())
    .sort((a, b) => b.width * b.height - a.width * a.height)[0]
  return {x: r.x, y: r.y, width: r.width, height: r.height}
}"""


def scrub_pairs() -> list[tuple[str, str]]:
    pairs = []
    data = os.environ.get("HOTAS_KNEEBOARD_DATA")
    if data:
        pairs.append((str(Path(data).resolve()), "C:\\Users\\Pilote\\AppData\\Roaming\\HOTAS Kneeboard"))
    profile = os.environ.get("USERPROFILE")
    if profile:
        pairs.append((profile, "C:\\Users\\Pilote"))
    return pairs


class Shooter:
    def __init__(self, browser: Browser, url: str, out: Path) -> None:
        self.browser, self.url, self.out = browser, url, out
        self.pairs = scrub_pairs()
        self.page = self.new_page()

    def new_page(self, scale: int = 1) -> Page:
        page = self.browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=scale
        ).new_page()
        page.goto(self.url)
        page.wait_for_load_state("networkidle")
        for listbox, text in (("Modules", MODULE), ("Périphériques", STICK)):
            options = page.get_by_role("listbox", name=listbox).get_by_role("option")
            options.filter(has_text=text).first.click()
            page.wait_for_timeout(800)
        page.wait_for_timeout(1000)
        return page

    def shot(self, target: Page | Locator, name: str, page: Page | None = None, **kw) -> None:
        (page or self.page).evaluate(SCRUB, [self.pairs])
        target.screenshot(path=self.out / name, **kw)
        print(name)

    def dialog(self, button: str) -> Locator:
        self.page.get_by_role("button", name=button, exact=True).click()
        d = self.page.locator(".p-dialog").last
        d.wait_for()
        self.page.wait_for_timeout(500)
        return d

    def close(self) -> None:
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)

    def ecran(self) -> None:
        self.shot(self.page, "ecran-principal.png")

    def page_detail(self) -> None:
        # twice the resolution: the head of the stick, with a label of the Paddle layer
        hp = self.new_page(scale=2)
        box = hp.evaluate(PAGE_BOX)
        self.shot(hp, "page-detail.png", page=hp, clip={**box, "height": box["height"] * 0.387})
        hp.context.close()

    def export(self) -> None:
        self.page.get_by_role("button", name="Autres exports kneeboard").click()
        self.page.wait_for_timeout(400)
        menu = self.page.locator(".p-menu, .p-tieredmenu").last.bounding_box()
        x = menu["x"] - 16
        clip = {"x": x, "y": 0, "width": WIDTH - x, "height": menu["y"] + menu["height"] + 16}
        self.shot(self.page, "export-menu.png", clip=clip)
        self.close()

    def autres(self) -> None:
        self.shot(self.dialog("Autres logiciels"), "autres-logiciels.png")
        self.close()

    def liaisons(self) -> None:
        d = self.dialog("Liaisons")
        d.locator(".p-progressspinner").wait_for(state="detached")
        self.page.wait_for_timeout(400)
        self.shot(d, "liaisons.png")
        self.close()

    def reglages(self) -> None:
        self.shot(self.dialog("Réglages"), "reglages.png")
        self.close()

    def commandes(self) -> None:
        d = self.dialog("Commandes DCS : périphériques, vues du chapeau, sauvegardes")
        self.shot(d, "commandes-dcs.png")
        sections = (
            ("VUES DU CHAPEAU", "commandes-dcs-vues-du-chapeau"),
            ("PÉRIPHÉRIQUES SANS BOUTONS", "commandes-dcs-sans-boutons"),
        )
        for title, name in sections:
            s = d.locator("section").filter(has=self.page.locator("h3", has_text=title)).first
            s.scroll_into_view_if_needed()
            search = s.get_by_role("button", name="Chercher")
            if title == "PÉRIPHÉRIQUES SANS BOUTONS" and search.is_disabled():
                # no device ticked yet: the tick goes to the app's settings, DCS is untouched
                s.get_by_text(RUDDER, exact=True).click()
            search.click()  # the preview, read from the files
            s.get_by_role("button", name="Relire").wait_for()
            self.page.wait_for_timeout(500)
            s.scroll_into_view_if_needed()
            self.shot(s, f"{name}.png")
        self.close()

    def editeur(self) -> None:
        self.page.get_by_role("button", name="Modifier").click()
        self.page.wait_for_timeout(1500)
        self.shot(self.page, "editeur.png")
        self.page.get_by_role("button", name="Vérifier (V)").click()
        self.page.wait_for_timeout(800)
        self.shot(self.page, "editeur-verifier.png", clip={"x": 0, "y": 114, "width": 300, "height": 560})


# in this order: the editor leaves the main screen
SCREENS = ("ecran", "page_detail", "export", "autres", "liaisons", "reglages", "commandes", "editeur")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8654/")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "docs" / "images")
    parser.add_argument(
        "only", nargs="*", help=f"screens to retake, among {', '.join(SCREENS)} (default: all)"
    )
    args = parser.parse_args()
    if unknown := set(args.only) - set(SCREENS):
        parser.error(f"unknown screens: {', '.join(sorted(unknown))}")
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        shooter = Shooter(browser, args.url, args.out)
        for screen in SCREENS:
            if not args.only or screen in args.only:
                getattr(shooter, screen)()
        browser.close()


if __name__ == "__main__":
    main()
