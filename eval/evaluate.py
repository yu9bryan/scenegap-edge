"""Score SceneGap on the openly licensed footage set, following eval/PROTOCOL.md.

  python eval/evaluate.py calibrate --mp4 F:/sg_data/commons/mp4 --work F:/sg_data/_eval
  python eval/evaluate.py test      --mp4 F:/sg_data/commons/mp4 --work F:/sg_data/_eval   (runs once; refuses a second run)
  python eval/evaluate.py perf      --mp4 F:/sg_data/commons/mp4 --work F:/sg_data/_eval

Inputs: datasets/manifests/commons_manifest.json, eval/requirements.json, eval/labels/gold.json.
Outputs: eval/results/*.json and eval/results/REPORT.md. CPU/GPU numbers are reference numbers, never NPU numbers.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from scenegap.domain.coverage import _semantic_queries, candidates_for  # noqa: E402
from scenegap.service import SceneGap, req_from_dict  # noqa: E402
from split import split  # noqa: E402

RES = os.environ.get("SG_EVAL_RES", os.path.join(HERE, "results"))           # override only for dry runs
GRID = [round(0.150 + 0.005 * i, 3) for i in range(51)]
SAMPLE_MS = 1000
MATCH_MIN_S = 0.5
N_PROJECTS, PROJECT_SEED = 8, "scenegap-projects-2026-10-26"


# ---------------- helpers ----------------
def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"k": k, "n": n, "p": round(p, 4), "lo": round(max(0.0, c - h), 4), "hi": round(min(1.0, c + h), 4)}


def load_inputs():
    man = json.load(open(os.environ.get("SG_EVAL_MANIFEST", os.path.join(ROOT, "datasets", "manifests", "commons_manifest.json")), encoding="utf8"))
    reqs = json.load(open(os.path.join(HERE, "requirements.json"), encoding="utf8"))
    gold = json.load(open(os.environ.get("SG_EVAL_GOLD", os.path.join(HERE, "labels", "gold.json")), encoding="utf8"))
    clips = man["clips"]
    sp = split(clips)
    return clips, sp, reqs, gold


def gold_intervals(gold, clip, rid):
    return [tuple(x) for x in gold["clips"].get(clip, {}).get(rid, [])]


def overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def cand_window_s(start_ms, end_ms):
    s, e = start_ms / 1000, end_ms / 1000
    if e - s < SAMPLE_MS / 1000:              # PROTOCOL: widen to one sampling period
        e = s + SAMPLE_MS / 1000
    return s, e


def matches(gold, clip, rid, s, e):
    return any(overlap(s, e, g0, g1) >= MATCH_MIN_S for g0, g1 in gold_intervals(gold, clip, rid))


def available(gold, clip_list, rid, min_s):
    for c in clip_list:
        for g0, g1 in gold_intervals(gold, c, rid):
            if g1 - g0 >= max(min_s, 1e-9):
                return True
    return False


def make_service(work, device, tau=None, crop="center-crop"):
    from scenegap.backends.cpu_clip import ClipReference
    be = ClipReference(device=device, crop=crop)
    cfg = {"stable_wait_s": 0.0, "semantic_threshold": tau}
    return SceneGap(work, lambda: be, cfg), be


def build_project(svc, mp4_dir, clips, name):
    pid = svc.create_project(name)
    rid = svc.add_root(pid, mp4_dir)
    svc.import_assets(pid, rid, list(clips))
    t0 = time.perf_counter()
    svc.analyze_assets(pid)
    dt = time.perf_counter() - t0
    amap = {a["asset_id"]: os.path.basename(svc.asset_path(a["asset_id"])) for a in svc.assets(pid)}
    bad = [a for a in svc.assets(pid) if a["status"] != "analyzed"]
    if bad:
        print("not analysed:", [(amap[a["asset_id"]], a["status"], a["error_code"]) for a in bad])
    return pid, amap, dt


def set_requirements(svc, pid, reqs):
    for r in reqs:
        d = {k: v for k, v in r.items() if k != "keywords"}
        svc.set_requirement(pid, d)


# ---------------- calibrate on dev ----------------
def calibrate_one(a, crop, dev, reqs, gold):
    svc, be = make_service(os.path.join(a.work, a.device), a.device, crop=crop)
    pid, amap, dt = build_project(svc, a.mp4, dev, "dev-" + crop)
    R = [req_from_dict({**{k: v for k, v in r.items() if k != "keywords"}, "revision": 1}) for r in reqs]
    queries = sorted({q for r in R for q in svc._queries(r)})
    assets, _ = svc._asset_indexes(pid, queries)
    scores, labels = [], []
    for ai in assets:
        clip = amap[ai.asset_id]
        for r in R:
            qs = _semantic_queries(r)
            for s in ai.samples:
                t = s.t_ms / 1000
                scores.append(min(s.sims[q] for q in qs))
                labels.append(any(g0 <= t < g1 for g0, g1 in gold_intervals(gold, clip, r.requirement_id)))
    sc, lb = np.array(scores), np.array(labels, bool)
    table = []
    for tau in GRID:
        pred = sc >= tau
        tp, fp, fn = int((pred & lb).sum()), int((pred & ~lb).sum()), int((~pred & lb).sum())
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        table.append({"tau": tau, "tp": tp, "fp": fp, "fn": fn, "f1": round(f1, 4)})
    best = max(table, key=lambda x: (x["f1"], x["tau"]))
    print(f"[{crop}] dev pairs {len(sc)} positives {int(lb.sum())}  tau {best['tau']}  F1 {best['f1']}")
    return {"crop": crop, "fingerprint": be.manifest.fingerprint, "backend": be.name, "model": be.manifest.to_dict(),
            "pairs": int(len(sc)), "positives": int(lb.sum()), "chosen": best, "grid": table, "analyse_s": round(dt, 2)}


def calibrate(a):
    """Dev only: pick the crop policy and tau by sample-level F1 (PROTOCOL), then freeze them."""
    clips, sp, reqs, gold = load_inputs()
    dev = [c["clip"] for c in clips if sp[c["clip"]] == "dev"]
    tried = [calibrate_one(a, crop, dev, reqs, gold) for crop in ("center-crop", "pad-square")]
    pick = max(tried, key=lambda x: (x["chosen"]["f1"], x["crop"] == "center-crop"))
    out = {**pick, "dev_clips": dev, "alternatives": [{"crop": t["crop"], "chosen": t["chosen"]} for t in tried],
           "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    os.makedirs(RES, exist_ok=True)
    json.dump(out, open(os.path.join(RES, "calibration.json"), "w", encoding="utf8"), indent=1)
    print("frozen:", pick["crop"], pick["chosen"])


# ---------------- score test once ----------------
def keyword_hits(clips_meta, clip_list, r):
    kws = [k.lower() for k in r.get("keywords", [])]
    titles = {c["clip"]: (c["title"] + " " + c["clip"]).lower().replace("_", " ") for c in clips_meta}
    return [c for c in clip_list if any(k in titles[c] for k in kws)]


def single_frame(assets, amap, r, tau, k=5):
    qs = _semantic_queries(r)
    best = {}
    for ai in assets:
        for s in ai.samples:
            v = min(s.sims[q] for q in qs)
            key = (ai.asset_id, s.shot_index)
            if v >= tau and v > best.get(key, (-9, 0))[0]:
                best[key] = (v, s.t_ms)
    ranked = sorted(((v, aid, t) for (aid, _), (v, t) in best.items()), reverse=True)[:k]
    return [(amap[aid], t, t + SAMPLE_MS) for v, aid, t in ranked]


def test(a):
    os.makedirs(RES, exist_ok=True)
    out_p = os.path.join(RES, "test_metrics.json")
    if os.path.exists(out_p):
        sys.exit("test split already scored once; results are frozen (see eval/results/test_metrics.json)")
    cal = json.load(open(os.path.join(RES, "calibration.json"), encoding="utf8"))
    tau = cal["chosen"]["tau"]
    clips, sp, reqs, gold = load_inputs()
    test_clips = [c["clip"] for c in clips if sp[c["clip"]] == "test"]
    svc, be = make_service(os.path.join(a.work, a.device), a.device, crop=cal["crop"])
    if be.manifest.fingerprint != cal["fingerprint"]:
        sys.exit("model fingerprint differs from the calibrated one; recalibrate on dev")
    svc.cfg["semantic_threshold"] = {be.manifest.fingerprint: tau}
    byid = {r["requirement_id"]: r for r in reqs}

    # 1) system outputs, computed once (they do not depend on any label)
    pid, amap, _ = build_project(svc, a.mp4, test_clips, "test-library")
    set_requirements(svc, pid, reqs)
    run = svc.compute_run(pid)
    R = svc.requirements(pid)
    queries = sorted({q for r in R for q in svc._queries(r)})
    assets, _ = svc._asset_indexes(pid, queries)
    outputs = {}
    for r in R:
        rid = r.requirement_id
        outputs[rid] = {"full": [(amap[c["asset_id"]], *cand_window_s(c["start_ms"], c["end_ms"])) for c in run["outcomes"][rid]["candidates"]],
                        "single_frame": [(c, t0 / 1000, t1 / 1000) for c, t0, t1 in single_frame(assets, amap, r, tau)],
                        "keyword": [(c, 0.0, 1e9) for c in keyword_hits(clips, test_clips, byid[rid])[:5]],
                        "status": run["outcomes"][rid]["status"], "reasons": run["outcomes"][rid]["reasons"], "query_en": r.query_en,
                        "min_s": (r.min_duration_ms or 0) / 1000}
    lib_s = sum(x["duration_ms"] for x in svc.assets(pid)) / 1000
    shown_s = sum(min(c["end_ms"] - c["start_ms"], 10000) / 1000 if c["end_ms"] - c["start_ms"] >= 1000 else 1.0
                  for r in R for c in run["outcomes"][r.requirement_id]["candidates"])
    review_load = {"library_seconds": round(lib_s, 1), "requirements": len(R), "full_watch_seconds": round(lib_s, 1),
                   "candidate_seconds_to_review": round(shown_s, 1),
                   "note": "proxy only: footage seconds a person would play (each candidate counted at its lower-bound length, "
                           "at least 1 s, at most 10 s) versus watching the library once; not a user-time measurement"}
    rng_clips = sorted(test_clips)
    k = max(3, min(8, len(rng_clips) // 2))
    sims = []
    for i in range(N_PROJECTS):
        sub = random.Random(f"{PROJECT_SEED}-{i}").sample(rng_clips, k)
        ppid, pmap, _ = build_project(svc, a.mp4, sub, f"sim-{i}")
        set_requirements(svc, ppid, reqs)
        prun = svc.compute_run(ppid)
        PR = svc.requirements(ppid)
        passets, _ = svc._asset_indexes(ppid, sorted({q for r in PR for q in svc._queries(r)}))
        sims.append({"clips": sub, "status": {r.requirement_id: {
            "full": prun["outcomes"][r.requirement_id]["status"],
            "single_frame": "candidate" if single_frame(passets, pmap, r, tau, 1) else "not_found",
            "keyword": "candidate" if keyword_hits(clips, sub, byid[r.requirement_id]) else "not_found"} for r in PR}})

    # 2) score the same outputs against each gold set (primary first)
    def score(g):
        per_req, retr = [], {m: {"hit": 0, "den": 0, "good": 0, "ret": 0} for m in ("keyword", "single_frame", "full")}
        for rid, o in outputs.items():
            has_gold = any(gold_intervals(g, c, rid) for c in test_clips)
            row = {"requirement_id": rid, "query_en": o["query_en"], "gold_clips": sum(1 for c in test_clips if gold_intervals(g, c, rid)),
                   "status": o["status"], "reasons": o["reasons"]}
            for m in ("keyword", "single_frame", "full"):
                ok = [matches(g, c, rid, st, en) for c, st, en in o[m]]
                retr[m]["ret"] += len(ok)
                retr[m]["good"] += sum(ok)
                if has_gold:
                    retr[m]["den"] += 1
                    retr[m]["hit"] += int(any(ok))
                row[m] = {"returned": len(ok), "correct": sum(ok)}
            per_req.append(row)
        retrieval = {m: {"recall_at_5": wilson(v["hit"], v["den"]), "precision_at_5": wilson(v["good"], v["ret"])} for m, v in retr.items()}
        sim = {m: {"gap_hit": 0, "gaps": 0, "wrong_reshoot": 0, "avail": 0, "unknown": 0, "false_candidate": 0, "total": 0} for m in ("keyword", "single_frame", "full")}
        projects = []
        for pr in sims:
            prow = {"clips": pr["clips"], "requirements": {}}
            for rid, st in pr["status"].items():
                av = available(g, pr["clips"], rid, outputs[rid]["min_s"])
                prow["requirements"][rid] = {"available": av, **st}
                for m, s_ in st.items():
                    v = sim[m]
                    v["total"] += 1
                    v["unknown"] += int(s_ in ("partial", "unverifiable"))
                    if av:
                        v["avail"] += 1
                        v["wrong_reshoot"] += int(s_ == "not_found")
                    else:
                        v["gaps"] += 1
                        v["gap_hit"] += int(s_ == "not_found")
                        v["false_candidate"] += int(s_ == "candidate")
            projects.append(prow)
        simulation = {m: {"gap_recall": wilson(v["gap_hit"], v["gaps"]), "wrong_reshoot_rate": wilson(v["wrong_reshoot"], v["avail"]),
                          "unknown_rate": wilson(v["unknown"], v["total"]), "false_candidate_rate": wilson(v["false_candidate"], v["gaps"]),
                          "false_ready_rate": "N/A (no automatic completion; human confirmation required)"} for m, v in sim.items()}
        return {"retrieval": retrieval, "per_requirement": per_req, "simulation": simulation, "projects": projects}

    primary = score(gold)
    lenient_p = os.environ.get("SG_EVAL_GOLD_LENIENT", os.path.join(HERE, "labels", "gold_lenient.json"))
    sensitivity = score(json.load(open(lenient_p, encoding="utf8"))) if os.path.exists(lenient_p) else None
    out = {"tau": tau, "crop": cal["crop"], "fingerprint": cal["fingerprint"], "backend": be.name, "test_clips": test_clips, "project_size": k,
           **primary, "review_load": review_load,
           "sensitivity_lenient_gold": sensitivity and {k_: sensitivity[k_] for k_ in ("retrieval", "simulation")},
           "scored_at": time.strftime("%Y-%m-%d %H:%M:%S"), "note": "CPU/GPU reference backend; no NPU result exists."}
    json.dump(out, open(out_p, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    for name, res in (("primary", primary), ("lenient", sensitivity)):
        if not res:
            continue
        for m in ("keyword", "single_frame", "full"):
            print(name, m, "R@5", res["retrieval"][m]["recall_at_5"], "P@5", res["retrieval"][m]["precision_at_5"])
            print("   ", {kk: (vv["p"] if isinstance(vv, dict) else vv) for kk, vv in res["simulation"][m].items()})


# ---------------- performance ----------------
def perf(a):
    import torch
    clips, sp, reqs, gold = load_inputs()
    names = sorted(c["clip"] for c in clips)
    rows = {}
    devices = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])
    for dev in devices:
        work = os.path.join(a.work, "perf_" + dev)
        cal = json.load(open(os.path.join(RES, "calibration.json"), encoding="utf8"))
        t0 = time.perf_counter()
        svc, be = make_service(work, dev, tau=cal["chosen"]["tau"], crop=cal["crop"])
        cold_s = time.perf_counter() - t0                       # model load (cold start)
        from PIL import Image
        be.encode_images([Image.new("RGB", (640, 360))] * 4)    # warm-up, not timed
        pick = names[: a.perf_clips]
        per_clip = []
        for n in pick:
            pid, amap, dt = build_project(svc, a.mp4, [n], "perf-" + n)
            aid = next(iter(amap))
            z, meta = svc._load_index(svc.assets(pid)[0]["sha256"])
            per_clip.append({"clip": n, "duration_s": round(svc.assets(pid)[0]["duration_ms"] / 1000, 2), "samples": int(len(z["t_ms"])),
                             "decode_sample_s": meta.get("decode_sample_s"), "embed_s": meta.get("embed_s"), "analyse_total_s": round(dt, 3)})
        # search latency over 10,000 indexed segments
        embs = [svc._load_index(x["sha256"])[0]["emb"] for p in [svc.db.all("SELECT * FROM assets")] for x in p]
        E = np.concatenate(embs).astype(np.float32)
        E = np.tile(E, (int(np.ceil(10000 / len(E))), 1))[:10000]
        qs = [r["query_en"] for r in reqs] * 5
        lat = []
        be.encode_texts(["warm up"])
        for q in qs:
            t0 = time.perf_counter()
            tv = be.encode_texts([q])[0]
            s = E @ tv
            top = np.argpartition(-s, 5)[:5]
            top = top[np.argsort(-s[top])]
            lat.append((time.perf_counter() - t0) * 1000)
        rows[be.name] = {"model_load_s": round(cold_s, 2), "per_clip": per_clip, "search_ms": {"n": len(lat), "segments": int(len(E)), "p50": round(float(np.percentile(lat, 50)), 2),
                                                             "p95": round(float(np.percentile(lat, 95)), 2)},
                         "device": torch.cuda.get_device_name(0) if dev == "cuda" else "desktop CPU"}
    out = {"measured_at": time.strftime("%Y-%m-%d %H:%M:%S"), "note": "reference backends on a desktop; UGen300 numbers: not_run", "backends": rows}
    os.makedirs(RES, exist_ok=True)
    json.dump(out, open(os.path.join(RES, "perf.json"), "w", encoding="utf8"), indent=1)
    print(json.dumps({k: v["search_ms"] for k, v in rows.items()}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["calibrate", "test", "perf"])
    ap.add_argument("--mp4", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--perf_clips", type=int, default=6)
    a = ap.parse_args()
    {"calibrate": calibrate, "test": test, "perf": perf}[a.stage](a)
