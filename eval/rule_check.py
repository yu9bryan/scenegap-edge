"""Rule check: does SceneGap judge length, same-frame and takes correctly? Controlled cases cut from real Commons footage.

  python eval/rule_check.py build <commons_mp4_dir> <cases_dir>
  python eval/rule_check.py run <cases_dir> [http://127.0.0.1:8766]      # a running SceneGap with the frozen calibration

Each case is a short video (or a pair of files) whose correct answer is known by construction: a 4 s pour must pass a
3 s rule, a 2 s pour must not, two 2 s pours split by another shot must not add up, two people outdoors are not "in a
café", and the same clip copied or re-encoded is not a second take. Street footage pads every case so the system has
to find the moment, not just the file. Each case runs in its own project with only the shot under test.
Writes eval/results/rule_check.json. This is a separate experiment from the held-out test (eval/PROTOCOL.md) and does
not change its numbers.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FF = os.environ.get("FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()
REQS = {r["requirement_id"]: r for r in json.load(open(os.path.join(HERE, "requirements.json"), encoding="utf8"))}
PAD_A, PAD_B = ("041_", 0, 3), ("041_", 3, 6)        # empty Paris street: no coffee, no café interior

# case id -> (shot, expected to pass?, what it tests, [files: [(clip prefix, start s, end s), ...]], how to make file 2)
CASES = {
    "pour_4s":        ("SH-05", True,  "continuous 4 s latte-art pour",                [[PAD_A, ("027_", 2, 6), PAD_B]]),
    "pour_6s_other":  ("SH-05", True,  "6 s pour from a different shoot",               [[PAD_A, ("007_", 39, 45), PAD_B]]),
    "pour_2s":        ("SH-05", False, "pour lasts only 2 s (rule: 3 s)",              [[PAD_A, ("027_", 2, 4), PAD_B]]),
    "pour_2s_2s":     ("SH-05", False, "two 2 s pours split by another shot",         [[PAD_A, ("027_", 2, 4), ("041_", 6, 8), ("027_", 6, 8), PAD_B]]),
    "cup_no_pour":    ("SH-05", False, "finished latte, nothing is poured (5 s)",     [[PAD_A, ("026_", 19, 24), PAD_B]]),
    "two_in_cafe":    ("SH-08", True,  "two people at a café table, same frame",      [[PAD_A, ("007_", 12, 19), PAD_B]]),
    "two_outdoors":   ("SH-08", False, "two people, but outdoors (not in a café)",    [[PAD_A, ("043_", 1, 5), PAD_B]]),
    "split_shots":    ("SH-08", False, "two people, then a café interior: separate shots", [[PAD_A, ("043_", 1, 4), ("006_", 12, 15), PAD_B]]),
    "takes_one":      ("SH-11", False, "one barista clip (rule: 2 takes)",            [[("020_", 15, 24)]]),
    "takes_copy":     ("SH-11", False, "the same clip copied byte for byte",          [[("020_", 15, 24)], "copy"]),
    "takes_reencode": ("SH-11", False, "the same clip re-encoded (still one take)",   [[("020_", 15, 24)], "reencode"]),
    "takes_two":      ("SH-11", True,  "two different barista clips",                 [[("020_", 15, 24)], [("007_", 27, 36)]]),
}


def ff(*a):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


def build(src_dir, out_dir):
    names = os.listdir(src_dir)
    clip = lambda pre: os.path.join(src_dir, next(n for n in names if n.startswith(pre)))
    for cid, (_, _, _, files) in CASES.items():
        d = os.path.join(out_dir, cid)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        for k, spec in enumerate(files):
            out = os.path.join(d, f"{cid}_{k + 1}.mp4")
            if spec == "copy":
                shutil.copyfile(os.path.join(d, f"{cid}_1.mp4"), out)
                continue
            if spec == "reencode":
                ff("-i", os.path.join(d, f"{cid}_1.mp4"), "-c:v", "libx264", "-crf", "30", "-preset", "fast", "-an", out)
                continue
            ins, parts = [], []
            for i, (pre, a, b) in enumerate(spec):
                ins += ["-ss", str(a), "-t", str(b - a), "-i", clip(pre)]
                parts.append(f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}]")
            n = len(spec)
            ff(*ins, "-filter_complex", ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]",
               "-map", "[v]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-an", out)
        print("built", cid, len(files), "file(s)")


class Api:
    def __init__(self, base):
        self.base = base.rstrip("/")
        page = urllib.request.urlopen(self.base + "/").read().decode()
        self.tok = re.search(r'name="sg-token" content="([^"]+)"', page).group(1)

    def __call__(self, method, path, body=None):
        r = urllib.request.Request(self.base + "/api/v1" + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                   headers={"X-SG-Token": self.tok, "Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(r).read() or b"null")


def run(cases_dir, base):
    api = Api(base)
    rows = []
    for cid, (rid, expect, what, files) in CASES.items():
        pid = api("POST", "/projects", {"name": f"rule check {cid}", "purpose": "rule check", "aspect": "16:9", "target_len_s": 60})["project_id"]
        req = {k: v for k, v in REQS[rid].items() if k != "keywords"}
        api("POST", f"/projects/{pid}/requirements", {"data": req})
        root = api("POST", f"/projects/{pid}/roots", {"path": os.path.abspath(os.path.join(cases_dir, cid))})["root_id"]
        api("POST", f"/projects/{pid}/assets/import", {"root_id": root})
        jid = api("POST", f"/projects/{pid}/analyze")["job_id"]
        while api("GET", f"/jobs/{jid}")["state"] not in ("done", "failed", "cancelled"):
            time.sleep(0.5)
        out = api("GET", f"/projects/{pid}/coverage")
        row = next(x for x in out["requirements"] if x["requirement"]["requirement_id"] == rid)
        auto = row["auto"] or {}
        status = auto.get("status")
        cands = auto.get("candidates") or []
        best = cands[0] if cands else None
        passed = status == "candidate"
        rows.append({"case": cid, "shot": rid, "tests": what, "expected": "pass" if expect else "not pass",
                     "status": status, "passed": passed, "correct": passed == expect, "reasons": auto.get("reasons"),
                     "best_candidate_s": round((best["end_ms"] - best["start_ms"]) / 1000, 2) if best else None,
                     "conditions": best and [(c["kind"], c["verdict"]) for c in best["conditions"]],
                     "files": len(files), "takes_seen": len({c["capture_id"] for c in cands if c["overall"] == "pass"})})
        print(f"{cid:15s} {rid} expected {'pass' if expect else 'not pass':8s} -> {status:12s} {'OK' if passed == expect else 'WRONG'}  {auto.get('reasons')}")
    res = {"run_at": time.strftime("%Y-%m-%d %H:%M:%S"), "base": "frozen calibration (eval/results/calibration.json)",
           "correct": sum(r["correct"] for r in rows), "cases": len(rows), "rows": rows}
    json.dump(res, open(os.path.join(HERE, "results", "rule_check.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print(f"{res['correct']}/{res['cases']} cases judged correctly")


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3])
    else:
        run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:8766")
