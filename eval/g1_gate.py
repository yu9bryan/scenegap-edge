"""G1 gate harness (docs/MODEL_PLAN.md §4): compare a candidate image encoder with the fp32 reference on the same
preprocessed dev frames.

  python eval/g1_gate.py --mp4 F:/sg_data/commons/mp4 --candidate hailo      # on a machine with a UGen300
  python eval/g1_gate.py --mp4 F:/sg_data/commons/mp4 --candidate cuda --self-check

Measures G1a (per-frame cosine), G1b (Spearman rho per query), G1c (top-K overlap at shot level). G1d/G1e need
each backend's own dev calibration and are run with eval/evaluate.py. `--self-check` compares the CPU and CUDA
reference backends (both fp32); it only proves the harness, never the device. Output: eval/results/g1_*.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from split import split  # noqa: E402

BARS = {"G1a_median_cos": 0.98, "G1a_p5_cos": 0.95, "G1b_median_rho": 0.95, "G1b_min_rho": 0.85, "G1c_mean_top5": 0.80, "G1c_mean_top10": 0.85}


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def frames_for(mp4_dir, clips):
    from scenegap.media.probe import probe
    from scenegap.shots.analyze import analyze
    imgs, keys = [], []
    for c in clips:
        p = os.path.join(mp4_dir, c)
        shots, frames, _ = analyze(p, probe(p).rotation, 1000)
        for f in frames:
            imgs.append(f.image)
            keys.append((c, f.shot_index))
    return imgs, keys


def topk_shots(sim, keys, k):
    best = {}
    for i, v in enumerate(sim):
        if v > best.get(keys[i], -9):
            best[keys[i]] = v
    return {s for s, _ in sorted(best.items(), key=lambda x: -x[1])[:k]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp4", required=True)
    ap.add_argument("--candidate", choices=["hailo", "cuda", "cpu"], required=True)
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    from scenegap.backends.cpu_clip import ClipReference
    man = json.load(open(os.path.join(os.path.dirname(HERE), "datasets", "manifests", "commons_manifest.json"), encoding="utf8"))
    cal = json.load(open(os.path.join(HERE, "results", "calibration.json"), encoding="utf8"))
    sp = split(man["clips"])
    dev = [c["clip"] for c in man["clips"] if sp[c["clip"]] == "dev"]
    reqs = json.load(open(os.path.join(HERE, "requirements.json"), encoding="utf8"))
    queries = sorted({r["query_en"] for r in reqs} | {q for r in reqs for c in r["constraints"] if c["kind"] == "co_occur" for q in c["params"]["queries"]})
    ref = ClipReference(device="cpu", crop=cal["crop"])
    if a.candidate == "hailo":
        from scenegap.backends.hailo import HailoClip
        cand = HailoClip()                                    # refuses to run until a device and a validated HEF exist
    else:
        if not a.self_check:
            sys.exit("a non-Hailo candidate is only allowed with --self-check")
        cand = ClipReference(device=a.candidate, crop=cal["crop"])
    imgs, keys = frames_for(a.mp4, dev)
    t0 = time.perf_counter()
    e_ref = ref.encode_images(imgs)
    t1 = time.perf_counter()
    e_c = cand.encode_images(imgs)
    t2 = time.perf_counter()
    cos = np.sum(e_ref * e_c, axis=1)
    tv = ref.encode_texts(queries)                           # text stays on the host with the same weights (route A)
    s_ref, s_c = e_ref @ tv.T, e_c @ tv.T
    rho = [spearman(s_ref[:, j], s_c[:, j]) for j in range(len(queries))]
    top5 = [len(topk_shots(s_ref[:, j], keys, 5) & topk_shots(s_c[:, j], keys, 5)) / 5 for j in range(len(queries))]
    top10 = [len(topk_shots(s_ref[:, j], keys, 10) & topk_shots(s_c[:, j], keys, 10)) / 10 for j in range(len(queries))]
    m = {"G1a_median_cos": float(np.median(cos)), "G1a_p5_cos": float(np.percentile(cos, 5)), "G1b_median_rho": float(np.median(rho)),
         "G1b_min_rho": float(np.min(rho)), "G1c_mean_top5": float(np.mean(top5)), "G1c_mean_top10": float(np.mean(top10))}
    out = {"run_at": time.strftime("%Y-%m-%d %H:%M:%S"), "reference": ref.name, "candidate": cand.name,
           "self_check": a.self_check, "frames": len(imgs), "queries": len(queries), "dev_clips": len(dev),
           "metrics": {k: round(v, 5) for k, v in m.items()}, "bars": BARS,
           "pass": {k: m[k] >= BARS[k] for k in BARS}, "encode_s": {"reference": round(t1 - t0, 2), "candidate": round(t2 - t1, 2)},
           "note": ("harness self-check between two fp32 reference backends; says nothing about the UGen300"
                    if a.self_check else "G1a-c on a real device; G1d-e via eval/evaluate.py with this backend's own tau")}
    name = "g1_selfcheck.json" if a.self_check else "g1_hailo.json"
    json.dump(out, open(os.path.join(HERE, "results", name), "w", encoding="utf8"), indent=1)
    print(json.dumps(out["metrics"]), out["pass"])


if __name__ == "__main__":
    main()
