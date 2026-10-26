"""Verifier P(yes) for every 1 s sample of every clip, for the Stage 1.5 question and the Stage 1.6 check questions.

  python eval/verify_dense.py <mp4_dir> <out.json> [--device cuda]

Samples are the system's own 1 s samples (scenegap.shots.analyze), so times line up with the gold labels.
Output: {clip: {"t_ms": [...], "shot": [...], "p": {question_id: [...]}}}; question ids are "<SH>:q0" (Stage 1.5
question from query_en), "<SH>:main" and "<SH>:part<i>" (eval/verify_questions.json). Resumes from an existing file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from scenegap.backends.vlm_verify import VlmVerifier, question_for  # noqa: E402
from scenegap.media.probe import probe  # noqa: E402
from scenegap.shots.analyze import analyze  # noqa: E402


def question_set():
    reqs = json.load(open(os.path.join(HERE, "requirements.json"), encoding="utf8"))
    qs = json.load(open(os.path.join(HERE, "verify_questions.json"), encoding="utf8"))
    out = {}
    for r in reqs:
        rid = r["requirement_id"]
        out[f"{rid}:q0"] = question_for(r["query_en"])
        s = qs["shots"][rid]
        out[f"{rid}:main"] = s["main"] + qs["suffix"]
        for i, p in enumerate(s.get("parts", [])):
            out[f"{rid}:part{i}"] = p + qs["suffix"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4_dir")
    ap.add_argument("out")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    Q = question_set()
    ids, texts = list(Q), list(Q.values())
    res = json.load(open(a.out, encoding="utf8")) if os.path.exists(a.out) else {}
    v = VlmVerifier(device=a.device)
    clips = sorted(f for f in os.listdir(a.mp4_dir) if f.endswith(".mp4"))
    t0 = time.time()
    for n, clip in enumerate(clips):
        if clip in res:
            continue
        path = os.path.join(a.mp4_dir, clip)
        _, frames, _ = analyze(path, probe(path).rotation, 1000, keep_px=448)
        row = {"t_ms": [], "shot": [], "p": {i: [] for i in ids}}
        for f in frames:
            ps = v.p_yes_many(f.image, texts)
            row["t_ms"].append(f.t_ms)
            row["shot"].append(f.shot_index)
            for i, p in zip(ids, ps):
                row["p"][i].append(round(p, 4))
        res[clip] = row
        json.dump(res, open(a.out, "w", encoding="utf8"))
        print(f"{n + 1}/{len(clips)} {clip[:50]} frames {len(frames)} calls {v.calls} {time.time() - t0:.0f}s", flush=True)
    json.dump({"questions": Q, "verifier_fingerprint": v.fingerprint, "clips": len(res)},
              open(a.out.replace(".json", "_meta.json"), "w", encoding="utf8"), indent=1)


if __name__ == "__main__":
    main()
