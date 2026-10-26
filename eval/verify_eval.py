"""Missing-shot detection with a second-stage verifier (Stage 1.5, after the first test scoring).

  python eval/verify_eval.py dev   --mp4 F:/sg_data/commons/mp4  --work F:/sg_data/_eval2
  python eval/verify_eval.py test2 --mp4 F:/sg_data/commons2/mp4 --work F:/sg_data/_eval2      # scored once

The full system runs per simulated project exactly as in evaluate.py (same threshold, densify, ranking). Then the
top-K candidates of each shot go to the verifier (Qwen2-VL-2B, eval of P(yes) on the K best frames of each
candidate). A shot is reported 'not_found' when no candidate reaches θ; otherwise the system's own status stays.

dev:   sweeps K and θ on the 20 dev projects used in explore_dev.py and freezes the setting chosen by the rule in
       eval/PROTOCOL.md (most missing shots caught with wrong reshoots ≤ 5% on dev; ties → higher θ, then smaller K).
       Writes eval/results/verify_dev.json.
test2: scores the frozen setting once on the new held-out set (datasets/manifests/test2_manifest.json,
       eval/labels/test2/gold.json) and refuses a second run. Writes eval/results/test2_metrics.json.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from evaluate import available, build_project, cand_window_s, make_service, matches, set_requirements, single_frame, wilson  # noqa: E402
from scenegap.backends.vlm_verify import VlmVerifier, question_for  # noqa: E402
from scenegap.domain.coverage import _semantic_queries  # noqa: E402

RES = os.path.join(HERE, "results")
THETAS = [round(0.05 * i, 2) for i in range(1, 20)]
KS = [1, 3, 5]
NFRAMES = 3
FF = os.environ.get("FFMPEG") or __import__("imageio_ffmpeg").get_ffmpeg_exe()


def frame_at(path, t_ms, tmp):
    from PIL import Image
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t_ms / 1000:.3f}", "-i", path, "-frames:v", "1", "-q:v", "2", tmp], check=True)
    im = Image.open(tmp)
    im.load()
    return im.convert("RGB")


class Scorer:
    """P(yes) per candidate = max over its NFRAMES best-matching samples; cached by (clip, t_ms, question)."""

    def __init__(self, verifier, mp4_dir, cache_path):
        self.v, self.mp4, self.cache_path = verifier, mp4_dir, cache_path
        self.cache = json.load(open(cache_path, encoding="utf8")) if os.path.exists(cache_path) else {}
        self.tmp = os.path.join(os.path.dirname(cache_path), "_frame.jpg")

    def frame_p(self, clip, t_ms, q):
        key = f"{clip}|{t_ms}|{q}"
        if key not in self.cache:
            self.cache[key] = round(self.v.p_yes(frame_at(os.path.join(self.mp4, clip), t_ms, self.tmp), q), 4)
        return self.cache[key]

    def candidate_p(self, r, cand, ai, clip):
        qs = _semantic_queries(r)
        inside = [s for s in ai.samples if cand["start_ms"] <= s.t_ms < max(cand["end_ms"], cand["start_ms"] + 1) and s.shot_index == cand["shot"]]
        if not inside:
            inside = sorted(ai.samples, key=lambda s: abs(s.t_ms - cand["start_ms"]))[:1]
        best = sorted(inside, key=lambda s: -min(s.sims.get(q, 0.0) for q in qs))[:NFRAMES]
        q = question_for(r.query_en)
        return max(self.frame_p(clip, s.t_ms, q) for s in best)

    def save(self):
        json.dump(self.cache, open(self.cache_path, "w", encoding="utf8"))


def run_projects(svc, mp4, projects, reqs, scorer, kmax):
    """System statuses and verifier scores of the top-kmax candidates, per project and shot."""
    out = []
    for i, sub in enumerate(projects):
        pid, amap, _ = build_project(svc, mp4, sub, f"verify-{i}")
        set_requirements(svc, pid, reqs)
        run = svc.compute_run(pid)
        R = svc.requirements(pid)
        assets, _ = svc._asset_indexes(pid, sorted({q for r in R for q in svc._queries(r)}))
        by_id = {a.asset_id: a for a in assets}
        rows = {}
        for r in R:
            o = run["outcomes"][r.requirement_id]
            cands = o["candidates"][:kmax]
            ps = [scorer.candidate_p(r, c, by_id[c["asset_id"]], amap[c["asset_id"]]) for c in cands]
            rows[r.requirement_id] = {"status": o["status"], "p": ps, "cands": [(amap[c["asset_id"]], *cand_window_s(c["start_ms"], c["end_ms"])) for c in cands],
                                      "single_frame": "candidate" if single_frame(assets, amap, r, svc.cfg["semantic_threshold"][svc.backend.manifest.fingerprint], 1) else "not_found"}
        out.append({"clips": sub, "rows": rows})
        print("project", i, "done", flush=True)
        scorer.save()
    return out


def decide(row, k, theta):
    if not row["p"][:k] or max(row["p"][:k]) < theta:
        return "not_found"
    return row["status"]


def score(results, gold, reqs, k, theta):
    gh = gaps = wr = av_n = fc = unk = tot = 0
    for pr in results:
        for r in reqs:
            rid = r["requirement_id"]
            st = decide(pr["rows"][rid], k, theta) if theta is not None else pr["rows"][rid]["status"]
            av = available(gold, pr["clips"], rid, (r.get("min_duration_ms") or 0) / 1000)
            tot += 1
            unk += st in ("partial", "unverifiable")
            if av:
                av_n += 1
                wr += st == "not_found"
            else:
                gaps += 1
                gh += st == "not_found"
                fc += st == "candidate"
    return {"k": k, "theta": theta, "gap_recall": wilson(gh, gaps), "wrong_reshoot": wilson(wr, av_n),
            "unknown": wilson(unk, tot), "false_candidate": wilson(fc, gaps)}


def choose(rows, cap=0.05):
    ok = [r for r in rows if r["theta"] is not None and r["wrong_reshoot"]["p"] <= cap]
    return max(ok, key=lambda r: (r["gap_recall"]["p"], r["theta"], -r["k"])) if ok else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "test2"])
    ap.add_argument("--mp4", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    cal = json.load(open(os.path.join(RES, "calibration.json"), encoding="utf8"))
    reqs = json.load(open(os.path.join(HERE, "requirements.json"), encoding="utf8"))
    svc, be = make_service(os.path.join(a.work, a.device), a.device, crop=cal["crop"])
    if be.manifest.fingerprint != cal["fingerprint"]:
        sys.exit("model fingerprint differs from the calibrated one")
    svc.cfg["semantic_threshold"] = {be.manifest.fingerprint: cal["chosen"]["tau"]}
    v = VlmVerifier(device=a.device)
    t0 = time.time()
    if a.mode == "dev":
        sys.path.insert(0, HERE)
        from split import split
        man = json.load(open(os.path.join(ROOT, "datasets", "manifests", "commons_manifest.json"), encoding="utf8"))
        sp = split(man["clips"])
        dev = sorted(c["clip"] for c in man["clips"] if sp[c["clip"]] == "dev")
        gold = json.load(open(os.path.join(HERE, "labels", "gold.json"), encoding="utf8"))
        k = max(3, min(8, len(dev) // 2))
        projects = [random.Random(f"dev-explore-{i}").sample(dev, k) for i in range(20)]
        scorer = Scorer(v, a.mp4, os.path.join(a.work, "verify_cache_dev.json"))
        res = run_projects(svc, a.mp4, projects, reqs, scorer, max(KS))
        rows = [score(res, gold, reqs, None, None)] + [score(res, gold, reqs, kk, th) for kk in KS for th in THETAS]
        pick = choose(rows)
        out = {"split": "dev", "projects": len(projects), "project_size": k, "verifier": v.name, "verifier_fingerprint": v.fingerprint,
               "frames_per_candidate": NFRAMES, "baseline": rows[0], "sweep": rows[1:], "chosen": pick,
               "rule": "most missing shots caught with wrong reshoot <= 5% on dev; ties -> higher theta, then smaller K",
               "verifier_calls": v.calls, "seconds": round(time.time() - t0, 1), "raw": res}
        json.dump(out, open(os.path.join(RES, "verify_dev.json"), "w", encoding="utf8"), indent=1)
        print("baseline", rows[0]["gap_recall"], rows[0]["wrong_reshoot"])
        print("chosen", pick and (pick["k"], pick["theta"], pick["gap_recall"], pick["wrong_reshoot"]))
    else:
        out_p = os.path.join(RES, "test2_metrics.json")
        if os.path.exists(out_p):
            sys.exit("test2 already scored once; results are frozen")
        frozen = json.load(open(os.path.join(RES, "verify_dev.json"), encoding="utf8"))["chosen"]
        man = json.load(open(os.path.join(ROOT, "datasets", "manifests", "test2_manifest.json"), encoding="utf8"))
        gold = json.load(open(os.path.join(HERE, "labels", "test2", "gold.json"), encoding="utf8"))
        clips = sorted(c["clip"] for c in man["clips"])
        k = 8
        projects = [random.Random(f"test2-{i}").sample(clips, k) for i in range(12)]
        scorer = Scorer(v, a.mp4, os.path.join(a.work, "verify_cache_test2.json"))
        res = run_projects(svc, a.mp4, projects, reqs, scorer, max(KS))
        base = score(res, gold, reqs, None, None)
        main_ = score(res, gold, reqs, frozen["k"], frozen["theta"])
        # retrieval on the whole new library: Hit@5 as ranked by the system, and as re-ranked by the verifier
        lib = run_projects(svc, a.mp4, [clips], reqs, scorer, 5)[0]["rows"]
        def hit(order):
            hits = den = 0
            for r in reqs:
                rid = r["requirement_id"]
                if not any(gold.get("clips", {}).get(c, {}).get(rid) for c in clips):
                    continue
                den += 1
                hits += any(matches(gold, c, rid, s, e) for c, s, e in order(lib[rid]))
            return wilson(hits, den)
        out = {"split": "test2 (new held-out footage)", "clips": len(clips), "projects": len(projects), "project_size": k,
               "frozen": {"k": frozen["k"], "theta": frozen["theta"], "verifier_fingerprint": v.fingerprint},
               "system_only": base, "with_verifier": main_,
               "hit5_system": hit(lambda row: row["cands"]),
               "hit5_reranked": hit(lambda row: [c for _, c in sorted(zip(row["p"], row["cands"]), key=lambda x: -x[0])]),
               "scored_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - t0, 1), "raw": res, "library": lib}
        json.dump(out, open(out_p, "w", encoding="utf8"), indent=1)
        print("system only", base["gap_recall"], base["wrong_reshoot"])
        print("with verifier", main_["gap_recall"], main_["wrong_reshoot"])


if __name__ == "__main__":
    main()
