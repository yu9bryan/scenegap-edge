"""1-frame-per-second contact sheets with timestamps, for human/AI annotators (eval/PROTOCOL.md).

  python scripts/contact_sheets.py <mp4_dir> <out_dir>
Writes <out_dir>/<clip>.png and <out_dir>/index.json (clip -> duration, shots, sample times).
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from scenegap.media.probe import probe  # noqa: E402
from scenegap.shots.analyze import analyze  # noqa: E402

COLS, TW = 6, 256


def sheet(path, out_png):
    pr = probe(path)
    shots, frames, _ = analyze(path, pr.rotation, 1000, keep_px=200)
    thumbs = []
    for f in frames:
        im = f.image.copy()
        im.thumbnail((TW, TW))
        thumbs.append((f.t_ms, f.shot_index, im))
    th = max(t[2].size[1] for t in thumbs)
    rows = (len(thumbs) + COLS - 1) // COLS
    W, H = COLS * (TW + 8) + 8, rows * (th + 30) + 40
    canvas = Image.new("RGB", (W, H), (24, 24, 30))
    d = ImageDraw.Draw(canvas)
    d.text((8, 10), f"{os.path.basename(path)}  duration {pr.duration_ms/1000:.1f}s  shots {[(round(a/1000,1), round(b/1000,1)) for a, b in shots]}", fill=(230, 230, 230))
    for i, (t, sh, im) in enumerate(thumbs):
        x, y = 8 + (i % COLS) * (TW + 8), 40 + (i // COLS) * (th + 30)
        canvas.paste(im, (x, y))
        d.text((x, y + th + 4), f"t={t/1000:.1f}s  shot {sh}", fill=(255, 220, 120))
    canvas.save(out_png)
    return {"duration_s": pr.duration_ms / 1000, "shots_s": [(a / 1000, b / 1000) for a, b in shots], "samples_s": [t / 1000 for t, _, _ in thumbs]}


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    ip = os.path.join(out, "index.json")
    index = json.load(open(ip, encoding="utf8")) if os.path.exists(ip) else {}   # resume: decoding has crashed mid-run
    for fn in sorted(os.listdir(src)):
        if fn.endswith(".mp4") and fn not in index:
            index[fn] = sheet(os.path.join(src, fn), os.path.join(out, fn.replace(".mp4", ".png")))
            print(fn, index[fn]["duration_s"], len(index[fn]["samples_s"]), flush=True)
            json.dump(index, open(ip, "w", encoding="utf8"), indent=1)
