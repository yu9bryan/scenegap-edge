import sys, time, os
from playwright.sync_api import sync_playwright
src, out, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=os.path.dirname(out), record_video_size={"width": 1920, "height": 1080})
    pg = ctx.new_page()
    pg.goto("file:///" + src.replace("\\", "/"))
    time.sleep(secs)
    v = pg.video; ctx.close()
    if os.path.exists(out): os.remove(out)
    v.save_as(out); v.delete(); b.close()
print("saved", out)
