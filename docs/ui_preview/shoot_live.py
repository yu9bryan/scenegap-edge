"""Full-resolution screenshots of the live SceneGap app on the real Commons demo project."""
import json, sys, time
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]; PID = json.load(open("F:/sg_data/_demo/demo_project.json"))["pid"]
W, H = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1440, 900)
suf = "" if W == 1440 else f"_{W}"
SHOTS = [("01_home", "#/home", 0), ("02_shotlist", "#/requirements/SH-05", 0), ("03_assets", "#/assets", 0), ("04_coverage", "#/coverage", 0),
         ("05_evidence", "#/evidence/SH-05/1", 0), ("05b_evidence_history", "#/evidence/SH-05/1", "決定紀錄"), ("06_reshoots", "#/board", 0), ("07_device", "#/device", 0)]
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto("http://127.0.0.1:8765/")
    pg.evaluate(f"localStorage.setItem('sg.pid', JSON.stringify('{PID}'))")
    pg.reload(); pg.wait_for_load_state('networkidle'); time.sleep(3)
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    for name, route, scroll in SHOTS:
        pg.goto("http://127.0.0.1:8765/" + route)
        pg.wait_for_load_state("networkidle")
        time.sleep(2.5)
        if scroll:                                    # scroll the decision history panel into view
            pg.get_by_text(scroll).first.evaluate("e => e.scrollIntoView({block: 'center'})"); time.sleep(0.8)
        pg.screenshot(path=f"{OUT}/{name}{suf}.png")
        ov = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        print(name, "overflow" if ov else "ok")
    print("console errors:", errs[:6])
    b.close()
