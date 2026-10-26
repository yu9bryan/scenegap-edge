"""Find new openly licensed café / coffee videos on Wikimedia Commons for a fresh held-out test set (test-2).

  python scripts/search_commons.py <out_candidates.json> [--n 24] [--exclude datasets/manifests/commons_manifest.json]

Selection uses metadata only (search rank, licence, length, size), never the frames, so it cannot favour the
method under test. Clips already in the first dataset are excluded. Order: round robin over the search terms,
each term in Commons' own relevance order.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), ".."))
from scripts.fetch_commons import UA, license_ok  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
TERMS = ["coffee shop", "café interior", "barista", "espresso", "latte art", "pouring coffee", "drinking coffee",
         "coffee grinder", "coffee beans", "coffee roasting", "cafe terrace", "coffee cup"]


def get(params):
    q = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    for k in range(5):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": UA}), timeout=60).read())
        except Exception as e:  # noqa: BLE001
            print("retry", k, e)
            time.sleep(5 * (k + 1))
    raise RuntimeError("Commons API failed")


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--exclude", default="datasets/manifests/commons_manifest.json")
    a = ap.parse_args()
    old = {c["title"] for c in json.load(open(a.exclude, encoding="utf8"))["clips"]}
    per_term = {}
    for t in TERMS:
        r = get({"action": "query", "generator": "search", "gsrsearch": f"filetype:video {t}", "gsrnamespace": 6, "gsrlimit": 50,
                 "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata|mediatype"})
        pages = sorted((r.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
        rows = []
        for p in pages:
            ii = (p.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata") or {}
            lic = (md.get("LicenseShortName") or {}).get("value", "")
            dur = ii.get("duration")
            if p["title"] in old or not license_ok(lic):
                continue
            if not dur or not (5 <= float(dur) <= 120) or (ii.get("size") or 0) > 80e6:
                continue
            rows.append({"title": p["title"], "page_url": ii.get("descriptionurl"), "download_url": ii.get("url"), "mime": ii.get("mime"),
                         "size_bytes": ii.get("size"), "duration_s": float(dur), "width": ii.get("width"), "height": ii.get("height"),
                         "license": lic, "license_url": (md.get("LicenseUrl") or {}).get("value", ""),
                         "artist": strip_html((md.get("Artist") or {}).get("value", "")), "credit": strip_html((md.get("Credit") or {}).get("value", "")),
                         "search_term": t})
        per_term[t] = rows
        print(t, len(rows))
        time.sleep(1)
    picked, seen = [], set()
    while len(picked) < a.n and any(per_term.values()):
        for t in TERMS:
            while per_term[t] and per_term[t][0]["title"] in seen:
                per_term[t].pop(0)
            if per_term[t] and len(picked) < a.n:
                c = per_term[t].pop(0)
                seen.add(c["title"])
                picked.append(c)
    json.dump(picked, open(a.out, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print(len(picked), "picked,", round(sum(c["duration_s"] for c in picked) / 60, 1), "min")


if __name__ == "__main__":
    main()
