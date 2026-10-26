"""Assemble the SceneGap Edge demo video (docs/video/VIDEO_SCRIPT.md) with ffmpeg.

  python make_video.py <work_dir> <out.mp4>

Inputs in <work_dir>: rec/*.mp4 (live UI recordings), vo/NN.mp3 + vo/timing.json (narration), and the Commons
clips in F:/sg_data/commons/mp4. Cards and captions are drawn with Pillow; everything is 1920x1080, 30 fps.
"""
import json
import os
import subprocess
import sys
import wave

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
    # this ffmpeg build sometimes dies with 0xC000008F on Windows; the same command succeeds when run again
    for attempt in range(3):
        r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *args])
        if r.returncode == 0:
            return
        print("ffmpeg exit", r.returncode, "- retrying" if attempt < 2 else "- giving up", flush=True)
    raise subprocess.CalledProcessError(r.returncode, FF)


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
    d.text((120, 170), "Search finds a cup. Shot-list rules are not in their docs.", font=font(56, True), fill=TEXT)
    cols = [(120, "Tool"), (900, "Finds the moment"), (1400, "Length · takes · frame")]
    y0 = 300
    for x, h_ in cols:
        d.text((x, y0), h_.upper(), font=font(24, True), fill=MUTED)
    d.line((120, y0 + 44, 1800, y0 + 44), fill=VIOLET, width=3)
    rows = [("Adobe Premiere Pro", "Yes", "Not in docs"), ("DaVinci Resolve", "Whole clips", "Not in docs"), ("Final Cut Pro", "Yes", "Not in docs"), ("SceneGap Edge", "Yes", "Checked; a person decides")]
    for i, (a, b, c) in enumerate(rows):
        y = y0 + 76 + i * 100
        last = i == len(rows) - 1
        if last:
            d.rounded_rectangle((100, y - 22, 1820, y + 70), 16, fill=(40, 30, 90))
        d.text((120, y), a, font=font(40, last), fill=TEXT)
        d.text((900, y), b, font=font(40, last), fill=(120, 230, 160))
        d.text((1400, y), c, font=font(40 if not last else 34, last), fill=MUTED if c == "Not in docs" else CYAN)
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
    rc = json.load(open(os.path.join(REPO, "eval", "results", "rule_check.json"), encoding="utf8"))
    mins = sum(c.get("duration_s_metadata") or 0 for c in man["clips"]) / 60
    overline(d, "Evidence", 120, 110)
    d.text((120, 160), "Tested on real, openly licensed footage", font=font(60, True), fill=TEXT)
    stats = [(f"{len(man['clips'])}", f"Wikimedia Commons clips · {mins:.0f} min"),
             (f"κ {agr['sample_level']['cohen_kappa']:.2f}", "agreement between two AI annotators (1 = perfect)"),
             (f"{r5['k']} / {r5['n']}", "shots with the right clip in the top 5 (held-out test, scored once)"),
             (f"{rc['correct']} / {rc['cases']}", "controlled rule cases judged right (length, same frame, takes)")]
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
    d.text((120, 135), "Next: the image half of CLIP on the ASUS UGen300", font=font(54, True), fill=TEXT)
    a = Image.open(os.path.join(os.path.dirname(REPO), "decks", "scenegap", "img", "architecture.png")).convert("RGB")
    a.thumbnail((1500, 610))
    im.paste(a, ((W - a.width) // 2, 230))
    return save(im, "card_arch.png")


def card_end(credits):
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    d.text((120, 170), "SceneGap Edge", font=font(110, True), fill=(255, 255, 255))
    d.text((126, 310), "Fewer surprises in the edit.", font=font(44), fill=CYAN)
    d.text((126, 380), "[Team name] · github.com/[team]/scenegap-edge", font=font(30), fill=TEXT)
    d.text((126, 450), "FOOTAGE · Wikimedia Commons, used under each licence; cropped, scaled and sped up for this video", font=font(24, True), fill=MUTED)
    y = 494
    for title, author, lic in credits:
        f = font(24)
        line = f"{title} — {author} — {lic}"
        while text_w(d, line, f) > 1680 and f.size > 18:
            f = font(f.size - 1)
        d.text((126, y), line, font=f, fill=TEXT)
        y += 36
    d.text((126, y + 14), "Full credits with links: datasets/manifests/commons_manifest.json in the repository.", font=font(22), fill=MUTED)
    d.text((126, y + 48), "Live app recorded on a desktop GPU (RTX 4080). Narration: Microsoft en-US-AndrewNeural (edge-tts).", font=font(22), fill=MUTED)
    d.text((126, y + 82), "This video adapts CC BY-SA footage and is released under CC BY-SA 4.0.", font=font(22), fill=MUTED)
    return save(im, "card_end.png")


def tag_png(tag, name):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = font(24, True); tw = text_w(d, tag, f)
    d.rounded_rectangle((40, 36, 40 + tw + 36, 84), 24, fill=(11, 11, 18, 215), outline=(108, 76, 245, 255), width=2)
    d.text((58, 46), tag, font=f, fill=(255, 255, 255, 255))
    p = os.path.join(TMP, name)
    im.save(p)
    return p


def balanced(d, text, f, maxw):
    """Wrap into as few lines as fit, then even out the line lengths so no line is a lone word."""
    lines = wrap(d, text, f, maxw)
    if len(lines) < 2:
        return lines
    words = text.split()
    best, best_cost = lines, None
    for w_ in range(int(maxw * 0.55), maxw + 1, 20):
        ls = wrap(d, text, f, w_)
        if len(ls) != len(lines):
            continue
        cost = max(text_w(d, ln, f) for ln in ls) - min(text_w(d, ln, f) for ln in ls)
        if best_cost is None or cost < best_cost:
            best, best_cost = ls, cost
    return best


def caption_png(text, name):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = font(40)
    lines = balanced(d, text, f, 1640)
    lh = 54; bh = len(lines) * lh + 30
    bw = max(text_w(d, ln, f) for ln in lines) + 80
    y0 = H - 24 - bh                               # sits in the band under the screen recordings
    d.rounded_rectangle(((W - bw) // 2, y0, (W + bw) // 2, y0 + bh), 18, fill=(0, 0, 0, 215))
    for i, ln in enumerate(lines):
        d.text(((W - text_w(d, ln, f)) / 2, y0 + 15 + i * lh), ln, font=f, fill=(255, 255, 255, 255))
    p = os.path.join(TMP, name)
    im.save(p)
    return p


def piece(p):
    """(start, end, speed) or (start, end, speed, (cx, cy, zoom)) in recording seconds and 1440x900 page pixels."""
    return (p[0], p[1], p[2], p[3] if len(p) > 3 else None)


def rec_to_out(pieces, t):
    """Where recording time t lands in the edited scene."""
    out = 0.0
    for a, b, sp, _ in map(piece, pieces):
        if t <= a:
            break
        out += (min(t, b) - a) / sp
    return out


def piece_windows(pieces):
    t, win = 0.0, []
    for a, b, sp, _ in map(piece, pieces):
        win.append((t, t + (b - a) / sp))
        t += (b - a) / sp
    return win


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
            fx, fy = scene.get("zoom_to", (0.5, 0.5))   # push in towards this point (share of the frame)
            filt = (f"[0:v]scale={int(W * 2)}:{int(H * 2)},zoompan=z='1+{z}*(1-cos(PI*min(on/{int(D * FPS)},1)))/2':x='(iw-iw/zoom)*{fx}':"
                    f"y='(ih-ih/zoom)*{fy}':d={int(D * FPS)}:s={W}x{H}:fps={FPS},setsar=1[v]")
        else:
            filt = f"[0:v]scale={W}:{H},fps={FPS},setsar=1[v]"
        if scene.get("inset"):
            pre, ss, t, box = scene["inset"]
            ins += ["-ss", str(ss), "-t", str(D), "-i", clip(pre)]
            x, y, w, h = box
            filt = filt.replace("[v]", "[b]") + (f";[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},"
                                                 f"loop=loop=-1:size=9999,trim=0:{D},setpts=PTS-STARTPTS[i];[b][i]overlay={x}:{y}[v]")
        return ins, filt
    if k == "seq":                                 # a still card, then a rendered clip, joined with a short cross-fade
        png, card_s, mp4 = scene["png"], scene["card_s"], os.path.join(WORK, "rec", scene["clip"])
        ins = ["-loop", "1", "-t", str(card_s + 0.5), "-i", png, "-i", mp4]
        filt = (f"[0:v]scale={W}:{H},setsar=1,format=yuv420p,settb=AVTB,fps={FPS}[s0];"
                f"[1:v]scale={W}:{H},setsar=1,format=yuv420p,setpts=PTS-STARTPTS,settb=AVTB,fps={FPS}[s1];"
                f"[s0][s1]xfade=transition=fade:duration=0.5:offset={card_s},tpad=stop_mode=clone:stop_duration=10,"
                f"trim=0:{D},setpts=PTS-STARTPTS[v]")
        return ins, filt
    if k == "rec":
        src = os.path.join(WORK, "rec", scene["rec"])
        ins = ["-i", src]
        pieces = [piece(p) for p in scene["pieces"]]
        n = len(pieces)
        parts = [f"[0:v]split={n}" + "".join(f"[s{i}]" for i in range(n))]
        for i, (a, b, sp, z) in enumerate(pieces):
            crop = ""
            if z:                                  # punch-in on the action, same output size
                cx, cy, k = z
                cw, ch = int(1440 / k) // 2 * 2, int(900 / k) // 2 * 2
                x, y = int(min(max(cx - cw / 2, 0), 1440 - cw)), int(min(max(cy - ch / 2, 0), 900 - ch))
                crop = f",crop={cw}:{ch}:{x}:{y},scale=1440:900:flags=lanczos"
            parts.append(f"[s{i}]trim={a}:{b},setpts=(PTS-STARTPTS)/{sp}{crop},setsar=1[p{i}]")
        # the recording sits above a caption band: 1408x880 at the top, captions below it
        filt = (";".join(parts) + ";" + "".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[r];"
                f"[r]scale=1408:880:flags=lanczos,fps={FPS},pad={W}:{H}:(ow-iw)/2:12:color=0x0B0B12,tpad=stop_mode=clone:stop_duration=30,"
                f"trim=0:{D},setpts=PTS-STARTPTS,setsar=1[v]")
        return ins, filt
    raise ValueError(k)


def place_sentences(scene, vo_len):
    """Each sentence: (source start, source end, time in the scene). A sentence goes at its cue (a recorded click,
    mapped through the scene's speed changes) but never before the previous sentence has finished."""
    sents = TIMING.get(scene["id"], [])
    cues = scene.get("cues") or [None] * len(sents)
    out, free = [], LEAD
    for j, s in enumerate(sents):
        a = 0.0 if j == 0 else s["start"]
        b = sents[j + 1]["start"] if j + 1 < len(sents) else vo_len
        want = LEAD + s["start"] if cues[j] is None else cues[j]
        t = max(want, free)
        out.append((a, b, t, s["text"]))
        free = t + (b - a) + 0.15
    return out


def scene_audio(sid, placed, D, sr=48000):
    """The scene's narration as a WAV: each sentence cut from the TTS file and placed at its time in the scene."""
    raw = os.path.join(TMP, f"vo_{sid}.f32")
    ff("-i", os.path.join(WORK, "vo", f"{sid}.mp3"), "-ac", "1", "-ar", str(sr), "-f", "f32le", raw)
    src = np.fromfile(raw, dtype="<f4")
    out = np.zeros(int(D * sr), dtype="<f4")
    for a, b, t, _ in placed:
        seg = src[int(a * sr):int(b * sr)]
        i0 = int(t * sr)
        seg = seg[:max(0, len(out) - i0)]
        out[i0:i0 + len(seg)] += seg
    wav = os.path.join(TMP, f"vo_{sid}.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype("<i2").tobytes())
    return wav


def build_scene(i, scene):
    sid = scene["id"]
    D = scene["D"]
    ins, filt = video_src(scene)
    n_in = sum(1 for x in ins if x == "-i")
    placed = scene["placed"]
    # captions: one PNG per sentence, shown while it is spoken (and until the next one if the gap is short)
    layers = []
    for j, (a, b, t, text) in enumerate(placed):
        end = t + (b - a) + 0.3
        if j + 1 < len(placed) and placed[j + 1][2] - end < 0.8:
            end = placed[j + 1][2]
        layers.append((caption_png(text, f"cap_{sid}_{j}.png"), t, min(end, D)))
    # tags: one per recording piece (speed shown honestly), or one for the whole scene
    tags = scene.get("tags")
    if tags:
        for j, ((a, b), tg) in enumerate(zip(piece_windows(scene["pieces"]), tags)):
            if tg:
                last_piece = j == len(tags) - 1
                layers.append((tag_png(tg, f"tag_{sid}_{j}.png"), a, D if last_piece else b))
    elif scene.get("tag"):
        layers.append((tag_png(scene["tag"], f"tag_{sid}.png"), 0, D))
    for p, _, _ in layers:
        ins += ["-i", p]
    chain, last = filt, "v"
    for j, (_, a, b) in enumerate(layers):
        chain += f";[{last}][{n_in + j}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[o{j}]"
        last = f"o{j}"
    chain += f";[{last}]fade=t=in:st=0:d=0.25,fade=t=out:st={D - 0.3}:d=0.3,format=yuv420p[vout]"
    ins += ["-i", scene_audio(sid, placed, D)]
    a_idx = sum(1 for x in ins if x == "-i") - 1
    chain += f";[{a_idx}:a]anull[aout]"
    out = os.path.join(TMP, f"scene_{sid}.mp4")
    ff(*ins, "-filter_complex", chain, "-map", "[vout]", "-map", "[aout]", "-t", str(D), "-r", str(FPS),
       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ac", "2", out)
    return out


def main():
    man = json.load(open(os.path.join(REPO, "datasets", "manifests", "commons_manifest.json"), encoding="utf8"))
    used = ["001_", "007_", "012_", "016_", "020_", "022_", "026_", "032_", "041_"]
    credits = [((c["title"] or "").replace("File:", "").rsplit(".", 1)[0], c.get("attribution") or c.get("artist") or "unknown", c.get("license") or "")
               for c in man["clips"] if any(c["clip"].startswith(u) for u in used)]
    frame = os.path.join(TMP, "frame_title.png")
    ff("-ss", "55", "-i", clip("007_"), "-frames:v", "1", frame)
    vo_len = {t: dur(os.path.join(WORK, "vo", f"{t}.mp3")) for t in TIMING}
    M = json.load(open(os.path.join(WORK, "rec", "marks.json"), encoding="utf8"))
    m = lambda rec, name: M[rec][name]["t"]

    def at(scene, rec, name, early=0.2):            # a recorded click, as a time in the edited scene
        return round(rec_to_out(scene["pieces"], m(rec, name)) - early, 2)

    def zoom_on(rec, name, k=1.6, dy=-120):         # punch-in centred a little above the clicked control
        b = M[rec][name]["box"]
        return (b["x"] + b["width"] / 2, b["y"] + b["height"] / 2 + dy, k)

    s06 = {"id": "06", "kind": "rec", "rec": "06_import.mp4",
           "pieces": [(0, m("06_import", "analyse") + 0.3, 3.0), (m("06_import", "analyse") + 0.3, m("06_import", "analysed"), 6.0), (m("06_import", "analysed"), 47.8, 1.0)],
           "tags": ["Live app · ×3", f"Live app · analysis ×6 · {m('06_import', 'analysed') - m('06_import', 'analyse'):.0f} s real time", "Live app · real time"]}
    s06["cues"] = [None, at(s06, "06_import", "analyse")]
    s08 = {"id": "08", "kind": "rec", "rec": "08_sh05.mp4",
           "pieces": [(0, m("08_sh05", "play1") - 0.3, 1.5), (m("08_sh05", "play1") - 0.3, m("08_sh05", "reject") - 0.5, 1.0),
                      (m("08_sh05", "reject") - 0.5, m("08_sh05", "confirm_reject") + 1.2, 1.0, zoom_on("08_sh05", "reason", 1.5, 120)),
                      (m("08_sh05", "confirm_reject") + 1.2, m("08_sh05", "play2") + 3.2, 2.0),
                      (m("08_sh05", "play2") + 3.2, m("08_sh05", "accept") + 2.2, 1.0, zoom_on("08_sh05", "accept", 1.5))],
           "tags": ["Live app · ×1.5", "Live app · real time", "Live app · real time · zoom", "Live app · ×2", "Live app · real time · zoom"]}
    s08["cues"] = [None, at(s08, "08_sh05", "play1"), at(s08, "08_sh05", "chip2"), at(s08, "08_sh05", "accept", 0.4)]
    s09 = {"id": "09", "kind": "rec", "rec": "09_reshoot.mp4",
           "pieces": [(0, m("09_reshoot", "add1") - 0.3, 1.5), (m("09_reshoot", "add1") - 0.3, m("09_reshoot", "confirm1") + 1.0, 2.0, zoom_on("09_reshoot", "reason1", 1.5, 120)),
                      (m("09_reshoot", "confirm1") + 1.0, m("09_reshoot", "add2") - 0.3, 2.0),
                      (m("09_reshoot", "add2") - 0.3, m("09_reshoot", "confirm2") + 1.0, 2.0, zoom_on("09_reshoot", "reason2", 1.5, 120)),
                      (m("09_reshoot", "confirm2") + 1.0, 31.5, 1.0)],
           "tags": ["Live app · ×1.5", "Live app · ×2 · zoom", "Live app · ×2", "Live app · ×2 · zoom", "Live app · real time"]}
    s09["cues"] = [None, at(s09, "09_reshoot", "sh07"), at(s09, "09_reshoot", "board", -0.6)]
    s10 = {"id": "10", "kind": "rec", "rec": "10_new_clip.mp4",
           "pieces": [(0, m("10_new_clip", "analyse") - 0.2, 3.0), (m("10_new_clip", "analyse") - 0.2, m("10_new_clip", "analysed") + 0.3, 1.0),
                      (m("10_new_clip", "analysed") + 0.3, m("10_new_clip", "play") - 0.3, 3.0),
                      (m("10_new_clip", "play") - 0.3, m("10_new_clip", "accept") - 0.6, 1.0),
                      (m("10_new_clip", "accept") - 0.6, m("10_new_clip", "board") - 0.2, 1.0, zoom_on("10_new_clip", "accept", 1.5)),
                      (m("10_new_clip", "board") - 0.2, m("10_new_clip", "board") + 2.2, 1.0)],
           "tags": ["Live app · ×3", "Live app · real time", "Live app · ×3", "Reshoot stand-in: another Commons clip (022)", "Live app · real time · zoom", "Live app · real time"]}
    s10["cues"] = [at(s10, "10_new_clip", "import"), at(s10, "10_new_clip", "analyse"), at(s10, "10_new_clip", "play"), at(s10, "10_new_clip", "accept", 0.5)]
    S = [
        {"id": "01", "kind": "footage", "clips": [("007_", 53.0, 2.6), ("026_", 3.0, 2.4), ("001_", 1.0, 2.2)], "tag": "Real footage · Wikimedia Commons"},
        {"id": "02", "kind": "still", "png": card_problem(), "inset": ("020_", 36.0, 0, (1080, 360, 720, 405))},
        {"id": "03", "kind": "still", "png": card_tools()},
        {"id": "04", "kind": "still", "png": card_title(frame), "zoom": 0.04},
        {"id": "05", "kind": "rec", "rec": "05_shotlist.mp4", "pieces": [(0, 14.1, 1.25)], "tag": "Live app · ×1.25"},
        s06,
        {"id": "07", "kind": "rec", "rec": "07_coverage.mp4", "pieces": [(0, 15.3, 2.5)], "tag": "Live app · ×2.5"},
        s08, s09, s10,
        {"id": "11", "kind": "seq", "png": card_results(), "card_s": round(LEAD + TIMING["11"][1]["start"] - 0.25, 2), "clip": "11_chart.mp4"},
        {"id": "12", "kind": "still", "png": card_arch(), "zoom": 0.06, "zoom_to": (0.86, 0.3)},
        {"id": "13", "kind": "still", "png": card_end(credits)},
    ]
    S[4]["cues"] = [None, round(m("05_shotlist", "open_sh05") / 1.25 - 1.2, 2)]
    files = []
    for i, s in enumerate(S):
        s["placed"] = place_sentences(s, vo_len[s["id"]])
        last = s["placed"][-1]
        talk = last[2] + (last[1] - last[0]) + 0.6
        vis = sum(b - a for a, b in piece_windows(s["pieces"])) if s["kind"] == "rec" else 0
        s["D"] = round(max(talk, vis, 5.0 if s["id"] == "13" else 0), 2)
        files.append(build_scene(i, s))
        print(s["id"], s["D"], [round(p[2], 1) for p in s["placed"]])
    lst = os.path.join(TMP, "concat.txt")
    open(lst, "w", encoding="utf8").write("".join(f"file '{f}'\n" for f in files))
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
       "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-movflags", "+faststart", OUT)
    print("total", round(sum(s["D"] for s in S), 1), "s ->", OUT)


if __name__ == "__main__":
    main()
