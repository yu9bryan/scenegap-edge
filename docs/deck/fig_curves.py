"""Figure: how the length rule reads the model's scores. CLIP similarity to the SH-05 query over time for three
rule-check cases (real footage with a known answer), the frozen threshold, the true pour, SceneGap's 1 fps samples
and its verdict.

  python fig_curves.py <repo> <rule_check_cases_dir> <out.png>
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO, CASES, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, REPO)
from scenegap.backends.cpu_clip import ClipReference  # noqa: E402

FF = os.environ.get("FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
TAU = json.load(open(os.path.join(REPO, "eval", "results", "calibration.json"), encoding="utf8"))["chosen"]["tau"]
RC = {r["case"]: r for r in json.load(open(os.path.join(REPO, "eval", "results", "rule_check.json"), encoding="utf8"))["rows"]}
Q = json.load(open(os.path.join(REPO, "eval", "requirements.json"), encoding="utf8"))[4]["query_en"]
# case, title, true pour interval (s), what the footage shows there
PANELS = [("pour_4s", "4 s latte-art pour (rule: 3 s)", (3.0, 7.0), "pour"),
          ("pour_2s", "2 s pour", (3.0, 5.0), "pour"),
          ("cup_no_pour", "finished latte, nothing poured", (3.0, 8.0), "cup, no pour")]
FPS = 4
INK, CARD, TEXT, MUTED, GRID, VIOLET, CYAN, OK, BAD = (11, 11, 18), (24, 24, 34), (240, 240, 248), (160, 164, 180), (52, 52, 70), (139, 120, 255), (34, 211, 238), (34, 197, 94), (240, 68, 90)
F = lambda s, b=False: ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if b else "C:/Windows/Fonts/arial.ttf", s)


def frames(path, fps):
    d = tempfile.mkdtemp()
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", path, "-vf", f"fps={fps}", "-q:v", "2", os.path.join(d, "f%04d.jpg")], check=True)
    fs = sorted(os.listdir(d))
    return [Image.open(os.path.join(d, f)).convert("RGB") for f in fs]


be = ClipReference(device="cuda")
qv = be.encode_texts([Q])[0]
W, PH, STRIP = 2400, 330, 110
H = 110 + len(PANELS) * (PH + STRIP + 60)
img = Image.new("RGB", (W, H), INK)
d = ImageDraw.Draw(img)
d.text((30, 24), "How the length rule reads the model's scores", font=F(36, True), fill=TEXT)
d.text((30, 70), f"CLIP similarity to “{Q}” (SH-05), {FPS} frames/s; dashed line = threshold τ {TAU}; dots = the 1 frame/s samples SceneGap uses",
       font=F(22), fill=MUTED)
for p, (case, title, (ta, tb), what) in enumerate(PANELS):
    path = os.path.join(CASES, case, f"{case}_1.mp4")
    ims = frames(path, FPS)
    sims = be.encode_images(ims) @ qv
    T = len(sims) / FPS
    y0 = 110 + p * (PH + STRIP + 60)
    d.rounded_rectangle((20, y0, W - 20, y0 + PH + STRIP + 40), 18, fill=CARD)
    r = RC[case]
    verdict = ("pass" if r["passed"] else "not pass") + (f" ({', '.join(x.lower() for x in r['reasons'])})" if r["reasons"] else "")
    right = r["correct"]
    d.text((44, y0 + 18), title, font=F(28, True), fill=TEXT)
    tag = f"SceneGap: {verdict} · measured run {r['best_candidate_s'] or 0:.1f} s · " + ("right" if right else "WRONG")
    d.text((W - 44, y0 + 22), tag, font=F(24, True), fill=OK if right else BAD, anchor="ra")
    # plot area
    x0, x1, py0, py1 = 120, W - 60, y0 + 70, y0 + PH
    lo, hi = 0.10, 0.34
    X = lambda t: x0 + (x1 - x0) * t / T
    Y = lambda v: py1 - (py1 - py0) * (min(max(v, lo), hi) - lo) / (hi - lo)
    shade = (40, 60, 52) if what == "pour" else (64, 40, 48)
    d.rectangle((X(ta), py0, X(tb), py1), fill=shade)
    d.text((X(ta) + 8, py1 - 30), what, font=F(20, True), fill=OK if what == "pour" else BAD)
    for v in (0.15, 0.20, 0.25, 0.30):
        d.line((x0, Y(v), x1, Y(v)), fill=GRID, width=1)
        d.text((x0 - 12, Y(v)), f"{v:.2f}", font=F(18), fill=MUTED, anchor="rm")
    for xx in range(x0, x1, 18):
        d.line((xx, Y(TAU), xx + 9, Y(TAU)), fill=CYAN, width=3)
    pts = [(X((i + 0.5) / FPS), Y(v)) for i, v in enumerate(sims)]
    d.line(pts, fill=VIOLET, width=5, joint="curve")
    for sec in range(int(T)):                                     # SceneGap's 1 frame/s samples
        i = min(len(sims) - 1, sec * FPS + FPS // 2)
        v = sims[i]
        c = CYAN if v >= TAU else MUTED
        d.ellipse((X(sec + 0.5) - 9, Y(v) - 9, X(sec + 0.5) + 9, Y(v) + 9), fill=c, outline=INK, width=2)
    for sec in range(int(T) + 1):
        d.text((X(sec), py1 + 8), f"{sec} s", font=F(18), fill=MUTED, anchor="ma")
    # filmstrip, one frame per second
    n = int(T)
    tw = (x1 - x0) / n
    for sec in range(n):
        im = ims[min(len(ims) - 1, sec * FPS + FPS // 2)]
        th = STRIP - 8
        s = max(tw / im.width, th / im.height)
        im2 = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
        cx, cy = (im2.width - int(tw - 4)) // 2, (im2.height - th) // 2
        img.paste(im2.crop((cx, cy, cx + int(tw - 4), cy + th)), (int(x0 + sec * tw + 2), py1 + 34))
img.save(OUT)
print(OUT, img.size, "tau", TAU)
