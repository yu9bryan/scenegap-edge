"""Assemble the SceneGap Edge demo video (docs/video/VIDEO_SCRIPT.md) with ffmpeg.

  python make_video.py <work_dir> <out.mp4>

Inputs in <work_dir>: rec/*.mp4 (live UI recordings), vo/NN.mp3 + vo/timing.json (narration), and the Commons
clips in F:/sg_data/commons/mp4. Cards and captions are drawn with Pillow; everything is 1920x1080, 30 fps.
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WORK, OUT = sys.argv[1], sys.argv[2]
FF = r"F:\cg_lora\venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
CLIPS = "F:/sg_data/commons/mp4"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H, FPS = 1920, 1080, 30
LEAD = 0.35
TMP = os.path.join(WORK, "build")
os.makedirs(TMP, exist_ok=True)
BG, VIOLET, VIOLET2, CYAN, TEXT, MUTED = (11, 11, 18), (108, 76, 245), (139, 120, 255), (34, 211, 238), (243, 241, 255), (156, 163, 175)
F_REG, F_BOLD = "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"
TIMING = {t["id"]: t["sentences"] for t in json.load(open(os.path.join(WORK, "vo", "timing.json"), encoding="utf8"))}


def font(size, bold=False):
    return ImageFont.truetype(F_BOLD if bold else F_REG, size)


def clip(name_prefix):
    return os.path.join(CLIPS, next(f for f in os.listdir(CLIPS) if f.startswith(name_prefix)))


def ff(*args):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def dur(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    h, m, s = out.split("Duration: ")[1].split(",")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


# ---------------- drawing ----------------
def background():
    y, x = np.mgrid[0:H, 0:W]
    g = np.exp(-(((x - W * 0.8) / (W * 0.45)) ** 2 + ((y - H * 0.9) / (H * 0.6)) ** 2))
    c = np.exp(-(((x - W * 0.05) / (W * 0.35)) ** 2 + ((y + H * 0.1) / (H * 0.5)) ** 2))
    img = np.zeros((H, W, 3), float) + BG
    img += g[..., None] * (np.array(VIOLET) - BG) * 0.45 + c[..., None] * (np.array(CYAN) - BG) * 0.12
    im = Image.fromarray(img.clip(0, 255).astype("uint8")).convert("RGBA")
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(grid)
    for gx in range(0, W, 80):
        d.line([(gx, 0), (gx, H)], fill=(255, 255, 255, 12), width=1)
    for gy in range(0, H, 80):
        d.line([(0, gy), (W, gy)], fill=(255, 255, 255, 12), width=1)
    return Image.alpha_composite(im, grid).convert("RGB")


BGIMG = background()


def text_w(d, s, f):
    return d.textlength(s, font=f)


def wrap(d, s, f, maxw):
    lines, cur = [], ""
    for w_ in s.split():
        t = (cur + " " + w_).strip()
        if text_w(d, t, f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def overline(d, s, x, y):
    d.text((x, y), s.upper(), font=font(24, True), fill=CYAN)


def save(im, name):
    p = os.path.join(TMP, name)
    im.save(p)
    return p


def card_problem():
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    overline(d, "Problem", 120, 120)
    d.text((120, 170), "The gap shows up in the edit", font=font(64, True), fill=TEXT)
    for i, (t, lab, col) in enumerate((("17:40", "Crew wraps on location", VIOLET2), ("23:00", "Editor finds the 3-second pour is missing", CYAN))):
        y = 360 + i * 230
        d.ellipse((128, y + 20, 160, y + 52), fill=col)
        if i == 0:
            d.line((144, y + 52, 144, y + 230 + 20), fill=(60, 60, 80), width=4)
        d.text((200, y), t, font=font(78, True), fill=col)
        d.text((200, y + 100), lab, font=font(34), fill=TEXT)
    return save(im, "card_problem.png")


def card_tools():
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    overline(d, "What exists", 120, 120)
    d.text((120, 170), "Search finds a cup. Nobody checks the shot list.", font=font(56, True), fill=TEXT)
    cols = [(120, "Tool"), (900, "Searches footage"), (1400, "Checks the shot list")]
    y0 = 300
    for x, h_ in cols:
        d.text((x, y0), h_.upper(), font=font(24, True), fill=MUTED)
    d.line((120, y0 + 44, 1800, y0 + 44), fill=VIOLET, width=3)
    rows = [("Adobe Premiere Pro", "Yes", "No"), ("DaVinci Resolve", "Yes", "No"), ("Final Cut Pro", "Yes", "No"), ("SceneGap Edge", "Yes", "Length · takes · same frame")]
    for i, (a, b, c) in enumerate(rows):
        y = y0 + 76 + i * 100
        last = i == len(rows) - 1
        if last:
            d.rounded_rectangle((100, y - 22, 1820, y + 70), 16, fill=(40, 30, 90))
        d.text((120, y), a, font=font(40, last), fill=TEXT)
        d.text((900, y), b, font=font(40, last), fill=(120, 230, 160))
        d.text((1400, y), c, font=font(40 if not last else 34, last), fill=(255, 120, 130) if c == "No" else CYAN)
        if not last:
            d.line((120, y + 82, 1800, y + 82), fill=(45, 45, 60), width=1)
    d.text((120, 800), "Vendor pages, accessed 2026-10-26 (docs/research/BUSINESS_FACTS.md)", font=font(22), fill=MUTED)
    return save(im, "card_tools.png")


def card_title(frame_png):
    base = Image.open(frame_png).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(14))
    base = Image.blend(base, Image.new("RGB", (W, H), BG), 0.62)
    d = ImageDraw.Draw(base)
    overline(d, "Creator AI · Lightning track · ASUS UGen300", 140, 360)
    d.text((140, 410), "SceneGap Edge", font=font(140, True), fill=(255, 255, 255))
    d.text((146, 600), "Checks your shot list against your footage, on your own computer.", font=font(42), fill=TEXT)
    return save(base, "card_title.png")


def card_results():
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    rep = json.load(open(os.path.join(REPO, "eval", "results", "test_metrics.json"), encoding="utf8"))
    agr = json.load(open(os.path.join(REPO, "eval", "labels", "agreement.json"), encoding="utf8"))
    man = json.load(open(os.path.join(REPO, "datasets", "manifests", "commons_manifest.json"), encoding="utf8"))
    r5 = rep["retrieval"]["full"]["recall_at_5"]
    rl = rep["review_load"]
    mins = sum(c.get("duration_s_metadata") or 0 for c in man["clips"]) / 60
    overline(d, "Evidence", 120, 110)
    d.text((120, 160), "Tested on real, openly licensed footage", font=font(60, True), fill=TEXT)
    stats = [(f"{len(man['clips'])}", f"Wikimedia Commons clips · {mins:.0f} min"),
             (f"κ {agr['sample_level']['cohen_kappa']:.2f}", "two independent annotators"),
             (f"{r5['k']} / {r5['n']}", "shots with the right clip in the top 5 (held-out test, scored once)"),
             (f"{rl['candidate_seconds_to_review']:.0f} s", f"of clips to check, instead of {rl['library_seconds']:.0f} s of footage")]
    for i, (big, lab) in enumerate(stats):
        x, y = 120 + (i % 2) * 860, 270 + (i // 2) * 270
        d.rounded_rectangle((x, y, x + 820, y + 240), 24, fill=(21, 21, 31), outline=(42, 42, 58), width=2)
        d.text((x + 40, y + 26), big, font=font(92, True), fill=VIOLET2 if i % 2 == 0 else CYAN)
        for j, ln in enumerate(wrap(d, lab, font(30), 740)):
            d.text((x + 40, y + 150 + j * 38), ln, font=font(30), fill=TEXT)
    return save(im, "card_results.png")


def card_arch():
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    overline(d, "Hardware", 120, 90)
    d.text((120, 135), "Next: the CLIP image encoder on the ASUS UGen300", font=font(54, True), fill=TEXT)
    a = Image.open(os.path.join(os.path.dirname(REPO), "decks", "scenegap", "img", "architecture.png")).convert("RGB")
    a.thumbnail((1500, 610))
    im.paste(a, ((W - a.width) // 2, 230))
    return save(im, "card_arch.png")


def card_end(credits):
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    d.text((120, 170), "SceneGap Edge", font=font(110, True), fill=(255, 255, 255))
    d.text((126, 310), "Fewer surprises in the edit.", font=font(44), fill=CYAN)
    d.text((126, 380), "[Team name] · github.com/[team]/scenegap-edge", font=font(30), fill=TEXT)
    d.text((126, 470), "FOOTAGE (Wikimedia Commons, used under each licence)", font=font(24, True), fill=MUTED)
    y = 515
    for title, author, lic in credits:
        d.text((126, y), f"{title} — {author} — {lic}", font=font(24), fill=TEXT)
        y += 36
    d.text((126, y + 16), "Live app recordings: SceneGap Edge on a desktop GPU (cuda-reference). Narration: synthetic voice.", font=font(22), fill=MUTED)
    return save(im, "card_end.png")


def caption_png(text, tag, name):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if tag:
        f = font(24, True); tw = text_w(d, tag, f)
        d.rounded_rectangle((40, 36, 40 + tw + 36, 84), 24, fill=(11, 11, 18, 200), outline=(108, 76, 245, 255), width=2)
        d.text((58, 46), tag, font=f, fill=(255, 255, 255, 255))
    if text:
        f = font(40)
        lines = wrap(d, text, f, 1500)
        lh = 54; bh = len(lines) * lh + 34
        y0 = H - 60 - bh
        d.rounded_rectangle(((W - 1580) // 2, y0, (W + 1580) // 2, y0 + bh), 18, fill=(0, 0, 0, 175))
        for i, ln in enumerate(lines):
            d.text(((W - text_w(d, ln, f)) / 2, y0 + 17 + i * lh), ln, font=f, fill=(255, 255, 255, 255))
    p = os.path.join(TMP, name)
    im.save(p)
    return p


# ---------------- scenes ----------------
def video_src(scene):
    """Return an ffmpeg input list + filter that yields [v] of the scene's base picture, D seconds long."""
    k, D = scene["kind"], scene["D"]
    if k == "footage":
        ins, parts = [], []
        for i, (pre, ss, t) in enumerate(scene["clips"]):
            ins += ["-ss", str(ss), "-t", str(t), "-i", clip(pre)]
            parts.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},"
                         f"fade=t=in:st=0:d=0.3,fade=t=out:st={t - 0.3}:d=0.3[c{i}]")
        n = len(scene["clips"])
        filt = ";".join(parts) + ";" + "".join(f"[c{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,tpad=stop_mode=clone:stop_duration=10,trim=0:{D},setpts=PTS-STARTPTS[v]"
        return ins, filt
    if k == "still":
        ins = ["-loop", "1", "-t", str(D), "-i", scene["png"]]
        z = scene.get("zoom", 0)
        if z:
            filt = (f"[0:v]scale={int(W * 1.1)}:{int(H * 1.1)},zoompan=z='min(1+{z}*on/{int(D * FPS)},1+{z})':x='iw/2-(iw/zoom/2)':"
                    f"y='ih/2-(ih/zoom/2)':d={int(D * FPS)}:s={W}x{H}:fps={FPS},setsar=1[v]")
        else:
            filt = f"[0:v]scale={W}:{H},fps={FPS},setsar=1[v]"
        if scene.get("inset"):
            pre, ss, t, box = scene["inset"]
            ins += ["-ss", str(ss), "-t", str(D), "-i", clip(pre)]
            x, y, w, h = box
            filt = filt.replace("[v]", "[b]") + (f";[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},"
                                                 f"loop=loop=-1:size=9999,trim=0:{D},setpts=PTS-STARTPTS[i];[b][i]overlay={x}:{y}[v]")
        return ins, filt
    if k == "rec":
        src = os.path.join(WORK, "rec", scene["rec"])
        ins = ["-i", src]
        pieces = scene["pieces"]                  # [(start, end, speed)]
        parts = []
        for i, (a, b, sp) in enumerate(pieces):
            parts.append(f"[0:v]trim={a}:{b},setpts=(PTS-STARTPTS)/{sp}[p{i}]")
        n = len(pieces)
        filt = (";".join(parts) + ";" + "".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[r];"
                f"[r]scale=-2:990,fps={FPS},pad={W}:{H}:(ow-iw)/2:78:color=0x0B0B12,tpad=stop_mode=clone:stop_duration=30,"
                f"trim=0:{D},setpts=PTS-STARTPTS,setsar=1[v]")
        return ins, filt
    raise ValueError(k)


def build_scene(i, scene):
    sid = scene["id"]
    D = scene["D"]
    ins, filt = video_src(scene)
    n_in = sum(1 for x in ins if x == "-i")
    # captions: one PNG per sentence, shown from its start until the next sentence starts
    sents = TIMING.get(sid, [])
    caps = []
    for j, s in enumerate(sents):
        start = LEAD + s["start"]
        end = LEAD + (sents[j + 1]["start"] if j + 1 < len(sents) else s["end"] + 0.4)
        caps.append((caption_png(s["text"], scene.get("tag"), f"cap_{sid}_{j}.png"), start, min(end, D)))
    if not caps and scene.get("tag"):
        caps.append((caption_png("", scene["tag"], f"cap_{sid}_tag.png"), 0, D))
    for p, _, _ in caps:
        ins += ["-i", p]
    chain, last = filt, "v"
    for j, (_, a, b) in enumerate(caps):
        chain += f";[{last}][{n_in + j}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[o{j}]"
        last = f"o{j}"
    if scene.get("tag") and sents:                 # keep the tag visible before the first sentence too
        tagp = caption_png("", scene["tag"], f"cap_{sid}_tagonly.png")
        ins += ["-i", tagp]
        chain += f";[{last}][{n_in + len(caps)}:v]overlay=0:0:enable='lt(t,{LEAD + sents[0]['start']:.2f})+gte(t,{caps[-1][2]:.2f})'[ot]"
        last = "ot"
    chain += f";[{last}]fade=t=in:st=0:d=0.25,fade=t=out:st={D - 0.3}:d=0.3,format=yuv420p[vout]"
    vo = os.path.join(WORK, "vo", f"{sid}.mp3")
    ins += ["-i", vo]
    a_idx = sum(1 for x in ins if x == "-i") - 1
    chain += f";[{a_idx}:a]adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad,atrim=0:{D},aresample=48000[aout]"
    out = os.path.join(TMP, f"scene_{sid}.mp4")
    ff(*ins, "-filter_complex", chain, "-map", "[vout]", "-map", "[aout]", "-t", str(D), "-r", str(FPS),
       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ac", "2", out)
    return out


def main():
    man = json.load(open(os.path.join(REPO, "datasets", "manifests", "commons_manifest.json"), encoding="utf8"))
    used = ["001_", "007_", "012_", "016_", "020_", "022_", "026_", "032_", "041_"]
    credits = [((c["title"] or "").replace("File:", "").rsplit(".", 1)[0][:58], (c.get("artist") or c.get("credit") or "unknown")[:40], c.get("license") or "")
               for c in man["clips"] if any(c["clip"].startswith(u) for u in used)]
    frame = os.path.join(TMP, "frame_title.png")
    ff("-ss", "55", "-i", clip("007_"), "-frames:v", "1", frame)
    vo_len = {t: dur(os.path.join(WORK, "vo", f"{t}.mp3")) for t in TIMING}
    S = [
        {"id": "01", "kind": "footage", "clips": [("007_", 53.0, 2.6), ("026_", 3.0, 2.4), ("001_", 1.0, 2.2)], "tag": "Real footage · Wikimedia Commons"},
        {"id": "02", "kind": "still", "png": card_problem(), "inset": ("020_", 36.0, 0, (1080, 360, 720, 405))},
        {"id": "03", "kind": "still", "png": card_tools()},
        {"id": "04", "kind": "still", "png": card_title(frame), "zoom": 0.04},
        {"id": "05", "kind": "rec", "rec": "05_shotlist.mp4", "pieces": [(0, 13.2, 1.05)], "tag": "Live app · Shot list"},
        {"id": "06", "kind": "rec", "rec": "06_import.mp4", "pieces": [(0, 15.5, 2.0), (15.5, 42.5, 12.0), (42.5, 45.7, 1.0)], "tag": "Live app · analysis sped up"},
        {"id": "07", "kind": "rec", "rec": "07_coverage.mp4", "pieces": [(0, 14.0, 1.75)], "tag": "Live app · Coverage"},
        {"id": "08", "kind": "rec", "rec": "08_sh05.mp4", "pieces": [(0, 29.8, 1.75)], "tag": "Live app · review (×1.75)"},
        {"id": "09", "kind": "rec", "rec": "09_reshoot.mp4", "pieces": [(0, 32.8, 2.2)], "tag": "Live app · reshoot list (×2.2)"},
        {"id": "10", "kind": "rec", "rec": "10_new_clip.mp4", "pieces": [(0, 12.0, 3.0), (12.0, 17.5, 2.0), (17.5, 28.0, 1.5), (28.0, 32.7, 1.6)], "tag": "Live app · new clip (sped up)"},
        {"id": "11", "kind": "still", "png": card_results()},
        {"id": "12", "kind": "still", "png": card_arch(), "zoom": 0.05},
        {"id": "13", "kind": "still", "png": card_end(credits)},
    ]
    vis = {"05": 13.2 / 1.05, "06": 15.5 / 2 + 27 / 12 + 3.2, "07": 14 / 1.75, "08": 29.8 / 1.75, "09": 32.8 / 2.2,
           "10": 12 / 3 + 5.5 / 2 + 10.5 / 1.5 + 4.7 / 1.6, "13": 9.0}
    files = []
    for i, s in enumerate(S):
        s["D"] = round(max(vo_len[s["id"]] + LEAD + 0.55, vis.get(s["id"], 0)), 2)
        files.append(build_scene(i, s))
        print(s["id"], s["D"])
    lst = os.path.join(TMP, "concat.txt")
    open(lst, "w", encoding="utf8").write("".join(f"file '{f}'\n" for f in files))
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
       "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-movflags", "+faststart", OUT)
    print("total", round(sum(s["D"] for s in S), 1), "s ->", OUT)


if __name__ == "__main__":
    main()
