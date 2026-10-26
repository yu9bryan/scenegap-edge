"""Figure: what the model returns. Top-5 candidates for four shots in the live demo project, real frames,
ranking score, the rule check, and whether the clip matches the gold labels.

  python fig_top5.py <demo_cands.json> <commons_mp4_dir> <out.png>

demo_cands.json comes from the demo project's coverage API (candidates per shot, with a gold check: at least 0.5 s
of overlap with eval/labels/gold.json).
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

CANDS, CLIPS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
FF = os.environ.get("FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
ROWS = [("SH-05", "Coffee or latte art poured into a cup, 3 s", "3 of 5 right; #1 is an espresso stream with no cup"),
        ("SH-08", "Two people in the café, same frame, 2 s", "4 of 5 right"),
        ("SH-04", "Grinding beans, 2 s", "the right clip (blender grinding) is ranked 4th"),
        ("SH-07", "Someone drinking from a cup, 2 s", "not in the footage, yet all 5 pass the rules")]
TW, TH, GAP, LW = 400, 225, 18, 600
INK, CARD, TEXT, MUTED, OK, BAD, VIOLET = (11, 11, 18), (24, 24, 34), (240, 240, 248), (160, 164, 180), (34, 197, 94), (240, 68, 90), (139, 120, 255)
F = lambda s, b=False: ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if b else "C:/Windows/Fonts/arial.ttf", s)
MONO = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 22)
cands = json.load(open(CANDS, encoding="utf8"))
names = os.listdir(CLIPS)


def frame(clip, t):
    tmp = os.path.join(os.environ.get("TEMP", "."), "sg_fig_frame.png")
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", os.path.join(CLIPS, clip), "-frames:v", "1", tmp], check=True)
    im = Image.open(tmp).convert("RGB")
    s = max(TW / im.width, TH / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - TW) // 2, (im.height - TH) // 2
    return im.crop((x, y, x + TW, y + TH))


RH = TH + 70
W, H = LW + 5 * (TW + GAP) + 20, 90 + len(ROWS) * (RH + 24)
img = Image.new("RGB", (W, H), INK)
d = ImageDraw.Draw(img)
d.text((30, 26), "Top 5 the model returns, per shot", font=F(34, True), fill=TEXT)
d.text((W - 30, 34), "frame from the middle of each candidate · green = matches the gold labels, red = does not", font=F(22), fill=MUTED, anchor="ra")
for r, (rid, text, verdict) in enumerate(ROWS):
    y0 = 90 + r * (RH + 24)
    d.rounded_rectangle((20, y0, W - 20, y0 + RH), 18, fill=CARD)
    d.text((40, y0 + 22), rid, font=F(32, True), fill=VIOLET)
    yy = y0 + 70
    words, line, lines = text.split(), "", []
    for w_ in words:
        if d.textlength((line + " " + w_).strip(), font=F(26)) > LW - 70:
            lines.append(line); line = w_
        else:
            line = (line + " " + w_).strip()
    lines.append(line)
    for ln in lines:
        d.text((40, yy), ln, font=F(26), fill=TEXT); yy += 34
    vlines, line = [], ""
    for w_ in verdict.split():
        if d.textlength((line + " " + w_).strip(), font=F(22, True)) > LW - 70:
            vlines.append(line); line = w_
        else:
            line = (line + " " + w_).strip()
    vlines.append(line)
    yy += 10
    for ln in vlines:
        d.text((40, yy), ln, font=F(22, True), fill=MUTED); yy += 28
    for k, c in enumerate(cands[rid]["cands"][:5]):
        x = LW + k * (TW + GAP)
        t = (c["start"] + c["end"]) / 2
        img.paste(frame(c["clip"], t), (x, y0 + 16))
        badge = OK if c["gold"] else BAD
        d.rounded_rectangle((x + 10, y0 + 26, x + 64, y0 + 80), 12, fill=badge)
        d.text((x + 37, y0 + 53), "✓" if c["gold"] else "✗", font=ImageFont.truetype("C:/Windows/Fonts/seguisym.ttf", 34), fill="white", anchor="mm")
        d.rounded_rectangle((x + TW - 70, y0 + 26, x + TW - 10, y0 + 66), 10, fill=(0, 0, 0))
        d.text((x + TW - 40, y0 + 46), f"#{k + 1}", font=F(24, True), fill="white", anchor="mm")
        rule = {"pass": "rules pass", "fail": "rule fails", "unknown": "can't tell"}.get(c["overall"], c["overall"])
        d.text((x, y0 + TH + 26), f"score {c['score']:.3f} · {rule}", font=F(22, True), fill=TEXT)
        d.text((x, y0 + TH + 52), f"{c['clip'][:3]}  {c['start']:.1f}–{c['end']:.1f} s", font=MONO, fill=MUTED)
img.save(OUT)
print(OUT, img.size)
