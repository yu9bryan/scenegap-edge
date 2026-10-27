"""Test-4: openly licensed Commons photos turned into 4 s clips (eval/PROTOCOL.md, Stage 1.7 amendment).

  python scripts/fetch_commons_photos.py <out_dir> [--manifest datasets/manifests/test4_manifest.json]

Selection uses metadata only: for each category, the files directly in it (JPEG/PNG, width >= 800, free licence),
sorted by title, then random.Random("test4-<category>") picks N. Each photo is fetched as a 1280 px Commons
thumbnail and rendered as a 4 s, 25 fps clip with a slow 1.00 -> 1.08 centre zoom. Clips are named t4_000 ... in a
shuffled order so the name carries no category; the manifest keeps title, URL, licence, author and hashes.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fetch_commons import UA, download, license_ok, sha256  # noqa: E402
from scenegap.media.fixtures import ffmpeg_exe  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
PLAN = [("Sidewalk cafés", 12), ("Interiors of cafés", 14), ("Coffee beans", 12), ("Coffee grinders", 10),
        ("Latte art", 12), ("Coffee preparation", 14), ("Cups of coffee", 12), ("People drinking coffee", 14),
        ("Baristas", 12), ("Espresso", 10), ("Espresso machines", 10), ("Coffee bags", 10), ("Potted plants", 8)]


def api(**p):
    import urllib.error
    p["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(p)
    for k in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            time.sleep(int(e.headers.get("Retry-After") or 0) or 30 * (k + 1))
    raise RuntimeError("Commons API keeps refusing")


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def category_files(cat):
    """Files directly in the category with their image info (title order)."""
    out, cont = [], {}
    while True:
        r = api(action="query", generator="categorymembers", gcmtitle="Category:" + cat, gcmtype="file", gcmlimit=50,
                prop="imageinfo", iiprop="url|size|mime|extmetadata", iiurlwidth=1280, **cont)
        for p in r.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata", {})
            out.append({"title": p["title"], "mime": ii.get("mime"), "width": ii.get("width"),
                        "page_url": ii.get("descriptionurl"), "thumb_url": ii.get("thumburl") or ii.get("url"),
                        "license": strip_html(md.get("LicenseShortName", {}).get("value")),
                        "license_url": md.get("LicenseUrl", {}).get("value"),
                        "artist": strip_html(md.get("Artist", {}).get("value")), "credit": strip_html(md.get("Credit", {}).get("value"))})
        if "continue" not in r:
            break
        cont = r["continue"]
        time.sleep(2)
    return sorted(out, key=lambda f: f["title"])


def eligible(f):
    return f["mime"] in ("image/jpeg", "image/png") and (f["width"] or 0) >= 800 and license_ok(f["license"])


def render(ff, img, dst, tmp):
    """4 s at 25 fps, 1280x720 (photo fitted inside, dark bars), slow centre zoom 1.00 -> 1.08 (scaled up first so
    zoompan does not jitter)."""
    out = os.path.join(tmp, "out.mp4")
    vf = ("scale=2560:1440:force_original_aspect_ratio=decrease,pad=2560:1440:(ow-iw)/2:(oh-ih)/2,zoompan=z='1+0.08*on/100':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=100:s=1280x720:fps=25,"
          "setsar=1")
    r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", "100",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                       timeout=300)
    if r.returncode == 0 and os.path.getsize(out) > 0:
        os.replace(out, dst)
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--manifest", default=os.path.join("datasets", "manifests", "test4_manifest.json"))
    a = ap.parse_args()
    orig, mp4, tmp = (os.path.join(a.out_dir, d) for d in ("original", "mp4", "_tmp"))
    for d in (orig, mp4, tmp):
        os.makedirs(d, exist_ok=True)
    sel_p = os.path.join(a.out_dir, "selection.json")
    if os.path.exists(sel_p):
        picks = json.load(open(sel_p, encoding="utf8"))
    else:
        picks, seen = [], set()
        for cat, n in PLAN:
            files = [f for f in category_files(cat) if eligible(f)]
            chosen = random.Random(f"test4-{cat}").sample(files, min(n, len(files)))
            for f in chosen:
                if f["title"] not in seen:
                    seen.add(f["title"])
                    picks.append(dict(f, category=cat))
            print(f"{cat}: {len(files)} eligible, picked {len(chosen)}", flush=True)
            time.sleep(2)
        order = list(range(len(picks)))
        random.Random("test4-names").shuffle(order)
        for k, i in enumerate(order):
            picks[i]["clip"] = f"t4_{k:03d}.mp4"
        json.dump(picks, open(sel_p, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    ff = ffmpeg_exe()
    out, failed = [], []
    for f in picks:
        ext = ".png" if f["mime"] == "image/png" else ".jpg"
        src = os.path.join(orig, f["clip"].replace(".mp4", ext))
        if not os.path.exists(src):
            download(f["thumb_url"], src)
            time.sleep(4)
        dst = os.path.join(mp4, f["clip"])
        if not os.path.exists(dst) and not render(ff, src, dst, tmp):
            failed.append(f["title"])
            print("render failed", f["title"], flush=True)
            continue
        out.append({k: f[k] for k in ("clip", "title", "category", "page_url", "thumb_url", "license", "license_url", "artist", "credit")}
                   | {"source_sha256": sha256(src), "mp4_sha256": sha256(dst)})
        print(f"{len(out):03d} {f['clip']}", flush=True)
    out.sort(key=lambda c: c["clip"])
    os.makedirs(os.path.dirname(a.manifest), exist_ok=True)
    json.dump({"source": "Wikimedia Commons photos", "built": time.strftime("%Y-%m-%d"),
               "render": "1280 px Commons thumbnail -> 4 s, 25 fps, 1280x720, zoom 1.00->1.08, H.264 CRF23",
               "plan": PLAN, "failed": failed, "clips": out}, open(a.manifest, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print("clips", len(out), "failed", len(failed))


if __name__ == "__main__":
    main()
