"""Check every transcoded clip against its original: duration within 1 s, decodable, and SHA-256 matching the
manifest. Writes datasets/manifests/transcode_check.json.

  python scripts/verify_transcodes.py F:/sg_data/commons
"""
import hashlib
import json
import os
import sys

import av

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from scenegap.media.probe import probe  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


def main(base):
    od, md = os.path.join(base, "original"), os.path.join(base, "mp4")
    man = json.load(open(os.path.join(ROOT, "datasets", "manifests", "commons_manifest.json"), encoding="utf8"))
    origs = [x for x in os.listdir(od) if not x.endswith(".part")]
    rows, bad = [], 0
    for c in man["clips"]:
        fn = c["clip"]
        o = next(x for x in origs if x.startswith(fn[:-4]))
        with av.open(os.path.join(od, o)) as cont:
            st = cont.streams.video[0]
            d0 = cont.duration / 1e6 if cont.duration else float(st.duration * st.time_base)
        pr = probe(os.path.join(md, fn))
        ok = abs(d0 - pr.duration_ms / 1000) < 1.0 and pr.supported and sha(os.path.join(md, fn)) == c["mp4_sha256"]
        bad += not ok
        rows.append({"clip": fn, "orig_s": round(d0, 2), "mp4_s": round(pr.duration_ms / 1000, 2), "codec": pr.codec,
                     "size": f"{pr.width}x{pr.height}", "ok": ok})
    out = {"clips": len(rows), "failed": bad, "rows": rows}
    json.dump(out, open(os.path.join(ROOT, "datasets", "manifests", "transcode_check.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} clips, {bad} failed")


if __name__ == "__main__":
    main(sys.argv[1])
