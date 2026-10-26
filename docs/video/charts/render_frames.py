"""Deterministic frame-by-frame render of a chart page that exposes window.renderAt(t).
  python render_frames.py page.html out.mp4 seconds [fps]
Every frame is drawn at exactly i/fps seconds, so motion is evenly timed (no dropped or doubled frames)."""
import subprocess, sys, time
from playwright.sync_api import sync_playwright
FF = r"F:\cg_lora\venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
src, out, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
fps = int(sys.argv[4]) if len(sys.argv) > 4 else 60
n = int(round(secs * fps))
enc = subprocess.Popen([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                       stdin=subprocess.PIPE)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto("file:///" + src.replace("\\", "/"))
    pg.wait_for_function("window.chartReady === true", timeout=60000)
    t0 = time.time()
    for i in range(n):
        pg.evaluate(f"window.renderAt({i / fps})")
        enc.stdin.write(pg.screenshot(type="png"))
    b.close()
enc.stdin.close(); enc.wait()
print(f"{n} frames at {fps} fps in {time.time() - t0:.0f} s -> {out}")
