"""Record the live SceneGap app for the demo video (docs/video/VIDEO_SCRIPT.md), one WebM per scene.

  python record_demo.py <out_dir> [segment ...]      # server on http://127.0.0.1:8766, project id in F:/sg_data/_rec/project.json

Every action goes through the real UI. A drawn cursor shows where the clicks land.
"""
import json
import os
import sys
import time
import urllib.request
import re

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8766/"
OUT = sys.argv[1]
ONLY = set(sys.argv[2:])
PID = json.load(open("F:/sg_data/_rec/project.json"))["pid"]
W, H = 1440, 900

CURSOR = """
(() => {
  const add = () => {
    if (document.getElementById('demo-cursor')) return;
    const c = document.createElement('div'); c.id = 'demo-cursor';
    c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;'
      + 'background:rgba(255,255,255,.92);box-shadow:0 0 0 3px rgba(108,76,245,.65),0 2px 8px rgba(0,0,0,.5);'
      + 'z-index:2147483647;pointer-events:none;transition:transform .12s ease;';
    document.body.appendChild(c);
    addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', () => { c.style.transform = 'scale(.7)'; }, true);
    addEventListener('mouseup', () => { c.style.transform = 'scale(1)'; }, true);
  };
  if (document.body) add(); else addEventListener('DOMContentLoaded', add);
})();
"""


def api(path):
    page = urllib.request.urlopen(BASE).read().decode()
    tok = re.search(r'name="sg-token" content="([^"]+)"', page).group(1)
    return json.loads(urllib.request.urlopen(urllib.request.Request(BASE + "api/v1" + path, headers={"X-SG-Token": tok})).read())


class Rec:
    def __init__(self, pw, name):
        self.name = name
        self.browser = pw.chromium.launch(channel="msedge")
        self.ctx = self.browser.new_context(viewport={"width": W, "height": H}, record_video_dir=OUT, record_video_size={"width": W, "height": H})
        self.ctx.add_init_script(CURSOR)
        self.ctx.add_init_script(f"localStorage.setItem('sg.pid', JSON.stringify('{PID}'))")
        self.pg = self.ctx.new_page()
        self.x, self.y = W / 2, H / 2

    def go(self, route, wait=2.5):
        self.pg.goto(BASE + route)
        self.pg.wait_for_load_state("networkidle")
        self.pg.mouse.move(self.x, self.y)
        time.sleep(wait)

    def move_to(self, loc, steps=22):
        loc.scroll_into_view_if_needed()
        b = loc.bounding_box()
        tx, ty = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        self.pg.mouse.move(tx, ty, steps=steps)
        self.x, self.y = tx, ty
        time.sleep(0.25)

    def click(self, loc, wait=1.2):
        self.move_to(loc)
        self.pg.mouse.down(); time.sleep(0.08); self.pg.mouse.up()
        time.sleep(wait)

    def type(self, loc, text, wait=0.6):
        self.click(loc, 0.3)
        self.pg.keyboard.type(text, delay=45)
        time.sleep(wait)

    def scroll(self, dy, steps=6, pause=0.35):
        for _ in range(steps):
            self.pg.mouse.wheel(0, dy / steps); time.sleep(pause)

    def close(self):
        dst = os.path.join(OUT, self.name + ".webm")
        video = self.pg.video
        self.ctx.close()                                # finishes the recording
        if os.path.exists(dst):
            os.remove(dst)
        video.save_as(dst)                              # waits until the file is completely written
        video.delete()
        self.browser.close()
        print("saved", dst)


def wait_assets(n, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if len(api(f"/projects/{PID}/assets")) >= n:
            return
        time.sleep(0.5)
    raise TimeoutError("import did not finish")


def wait_job_done(timeout=300):
    t0 = time.time()
    while not api(f"/projects/{PID}/jobs?active=1"):          # wait for the job to appear
        if time.time() - t0 > 15:
            raise RuntimeError("no analysis job started")
        time.sleep(0.3)
    t1 = time.time()
    while api(f"/projects/{PID}/jobs?active=1"):
        if time.time() - t1 > timeout:
            raise TimeoutError("analysis job did not finish")
        time.sleep(0.5)
    return time.time() - t1


def seg_shotlist(pw):
    r = Rec(pw, "05_shotlist")
    r.go("#/requirements", 2.0)
    r.scroll(500, 8, 0.3)
    r.click(r.pg.get_by_text("SH-05", exact=False).first, 3.5)
    r.scroll(300, 6, 0.4)
    time.sleep(1.5)
    r.close()


def seg_import(pw):
    r = Rec(pw, "06_import")
    r.go("#/assets", 2.0)
    r.type(r.pg.locator("#root-path"), "F:\\sg_data\\demo_card1")
    r.click(r.pg.get_by_role("button", name="授權資料夾"), 1.5)
    r.click(r.pg.get_by_role("button", name="匯入整個資料夾").last, 1.0)
    wait_assets(8)
    time.sleep(2.0)
    r.click(r.pg.get_by_role("button", name="開始分析").first, 0.5)
    took = wait_job_done()
    time.sleep(3.0)
    print("analysis took", round(took, 1), "s")
    r.close()
    return took


def seg_coverage(pw):
    r = Rec(pw, "07_coverage")
    r.go("#/coverage", 3.5)
    r.scroll(1400, 14, 0.45)
    time.sleep(1.0)
    r.close()


def seg_sh05(pw):
    r = Rec(pw, "08_sh05")
    r.go("#/evidence/SH-05/0", 3.0)
    r.click(r.pg.get_by_role("button", name=re.compile("播放")).first, 3.5)
    r.click(r.pg.locator(".bub-btn[aria-label='拒絕']"), 1.0)
    r.type(r.pg.locator("#dc-reason"), "No cup in frame")
    r.click(r.pg.get_by_role("button", name="確認拒絕"), 2.5)
    r.click(r.pg.locator("button.rchip").nth(1), 2.5)
    r.click(r.pg.get_by_role("button", name=re.compile("播放")).first, 3.0)
    r.click(r.pg.locator(".bub-btn[aria-label='接受']"), 3.0)
    r.close()


def seg_reshoot(pw):
    r = Rec(pw, "09_reshoot")
    r.go("#/evidence/SH-04/0", 3.0)
    r.click(r.pg.locator(".bub-btn[aria-label='要補拍']"), 1.0)
    r.type(r.pg.locator("#dc-reason"), "Tamping, not grinding. Need 2 s of grounds coming out")
    r.click(r.pg.get_by_role("button", name="加入補拍清單"), 2.5)
    r.go("#/evidence/SH-07/0", 2.5)
    r.click(r.pg.locator(".bub-btn[aria-label='要補拍']"), 1.0)
    r.type(r.pg.locator("#dc-reason"), "Nobody drinks from a cup in these clips")
    r.click(r.pg.get_by_role("button", name="加入補拍清單"), 3.0)
    r.scroll(600, 8, 0.4)
    time.sleep(1.5)
    r.close()


def seg_fix(pw):
    r = Rec(pw, "10_new_clip")
    r.go("#/assets", 2.0)
    r.type(r.pg.locator("#root-path"), "F:\\sg_data\\demo_card2")
    r.click(r.pg.get_by_role("button", name="授權資料夾"), 1.5)
    r.click(r.pg.get_by_role("button", name="匯入整個資料夾").last, 1.0)
    wait_assets(9)
    time.sleep(2.0)
    r.click(r.pg.get_by_role("button", name="開始分析").first, 0.5)
    took = wait_job_done()
    print("re-analysis took", round(took, 1), "s")
    time.sleep(2.0)
    cov = api(f"/projects/{PID}/coverage")
    row = next(x for x in cov["requirements"] if x["requirement"]["requirement_id"] == "SH-04")
    assets = {a["asset_id"]: a["locations"][0] for a in api(f"/projects/{PID}/assets")}
    idx = next(i for i, c in enumerate(row["auto"]["candidates"]) if assets[c["asset_id"]].startswith("022_"))
    r.go(f"#/evidence/SH-04/{idx}", 3.0)
    r.click(r.pg.get_by_role("button", name=re.compile("播放")).first, 4.0)
    r.click(r.pg.locator(".bub-btn[aria-label='接受']"), 2.5)
    r.go("#/board", 3.5)
    r.close()


SEGS = {"shotlist": seg_shotlist, "import": seg_import, "coverage": seg_coverage, "sh05": seg_sh05, "reshoot": seg_reshoot, "fix": seg_fix}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as pw:
        for name, fn in SEGS.items():
            if not ONLY or name in ONLY:
                fn(pw)
