"""Build the openly licensed footage set from Wikimedia Commons (PRD 21: real footage, licences traceable).

  python scripts/fetch_commons.py <candidates.json> <out_dir> [--manifest datasets/manifests/commons_manifest.json]

For each candidate: download the original, record its SHA-256, transcode to the first-version media path
(MP4, H.264, 8-bit, at most 1280 px wide, no audio) and record that SHA-256 too. Clips are not committed to
git; the manifest (URL, licence, author, hashes) is, so anyone can rebuild the same set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from scenegap.media.fixtures import ffmpeg_exe  # noqa: E402

UA = "SceneGapEdge-dataset/0.1 (student hackathon; downloads openly licensed clips once)"


def license_ok(lic: str) -> bool:
    """CC0, public domain, CC BY, CC BY-SA. Anything with NC (non-commercial) or ND (no derivatives) is out."""
    import re
    s = " " + (lic or "").lower().replace("_", " ").replace("-", " ") + " "
    if re.search(r"\b(nc|nd)\b", s):
        return False
    return bool(re.search(r"\bcc0\b|public domain|\bpd\b|\bcc by( sa)?\b", s))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


def safe_name(title: str) -> str:
    base = title.replace("File:", "")
    keep = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in base)
    return keep[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates")
    ap.add_argument("out_dir")
    ap.add_argument("--manifest", default=os.path.join("datasets", "manifests", "commons_manifest.json"))
    ap.add_argument("--max_mb", type=float, default=520)
    a = ap.parse_args()
    cands = json.load(open(a.candidates, encoding="utf8"))
    orig_dir, mp4_dir = os.path.join(a.out_dir, "original"), os.path.join(a.out_dir, "mp4")
    os.makedirs(orig_dir, exist_ok=True)
    os.makedirs(mp4_dir, exist_ok=True)
    ff = ffmpeg_exe()
    out, total = [], 0
    for i, c in enumerate(cands):
        if not license_ok(c.get("license")):
            print("skip licence", c["title"], c.get("license"))
            continue
        if total + (c.get("size_bytes") or 0) / 1e6 > a.max_mb:
            print("skip size budget", c["title"])
            continue
        ext = os.path.splitext(c["download_url"])[1] or ".bin"
        name = f"{i:03d}_{safe_name(c['title'])}"
        src = os.path.join(orig_dir, name + ext)
        if not os.path.exists(src):
            req = urllib.request.Request(c["download_url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r, open(src + ".part", "wb") as f:
                while b := r.read(1 << 20):
                    f.write(b)
            os.replace(src + ".part", src)
            time.sleep(0.5)                       # be polite to the Commons servers
        total += os.path.getsize(src) / 1e6
        dst = os.path.join(mp4_dir, name + ".mp4")
        if not os.path.exists(dst):
            subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-an", "-vf", "scale='min(1280,iw)':-2",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst],
                           check=True, timeout=600, shell=False)
        out.append({"clip": name + ".mp4", "title": c["title"], "page_url": c["page_url"], "download_url": c["download_url"],
                    "license": c.get("license"), "license_url": c.get("license_url"), "artist": c.get("artist"), "credit": c.get("credit"),
                    "source_sha256": sha256(src), "mp4_sha256": sha256(dst), "tags_from_metadata": c.get("tags", []),
                    "duration_s_metadata": c.get("duration_s")})
        print(f"{len(out):02d} {name} {os.path.getsize(src)/1e6:.1f} MB")
    os.makedirs(os.path.dirname(a.manifest), exist_ok=True)
    json.dump({"source": "Wikimedia Commons", "built": time.strftime("%Y-%m-%d"), "transcode": "H.264 yuv420p CRF23, <=1280 px, no audio",
               "clips": out}, open(a.manifest, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print("clips", len(out), "MB", round(total, 1))


if __name__ == "__main__":
    main()
