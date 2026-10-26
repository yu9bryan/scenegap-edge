"""Render docs/ui_preview/preview.html with Playwright (Edge) and save one PNG per screen.

Usage (run from a short working directory because of Windows MAX_PATH):
    python <abs path>/docs/ui_preview/shoot.py [width] [height]
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
URL = HERE.joinpath("preview.html").as_uri()
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
H = int(sys.argv[2]) if len(sys.argv) > 2 else 900
SUFFIX = "" if (W, H) == (1440, 900) else f"_{W}"

SHOTS = [
    ("01_home", "", "#/home"),
    ("01b_home_outdated", "?variant=outdated", "#/home"),
    ("02_requirements", "", "#/requirements/R03"),
    ("03_assets", "?variant=job", "#/assets"),
    ("03b_assets_table", "?variant=job", "#/assets", 560),
    ("04_coverage", "", "#/coverage"),
    ("05_evidence", "", "#/evidence/R01/0"),
    ("05b_evidence_history", "", "#/evidence/R01/0", 520),
    ("06_board", "", "#/board"),
    ("07_device", "", "#/device"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    for name, query, route, *scroll in SHOTS:
        page.goto(URL + query + route)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        if scroll:
            page.evaluate("y => { document.querySelector('#main').scrollTop = y; }", scroll[0])
            page.wait_for_timeout(300)
        page.screenshot(path=str(HERE / f"{name}{SUFFIX}.png"))
        # overflow check: anything wider than the viewport?
        over = page.evaluate("""() => { const m = document.querySelector('#main');
            const inner = [...document.querySelectorAll('.table-wrap, .panel, .card')].map((e) => e.scrollWidth - e.clientWidth);
            return {docW: document.documentElement.scrollWidth, mainOverflowX: m.scrollWidth - m.clientWidth,
                    innerOverflowX: Math.max(0, ...inner)}; }""")
        print(name, over)
    browser.close()
    print("errors:", errors or "none")
