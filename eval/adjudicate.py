"""Combine two independent label sets into gold (eval/PROTOCOL.md, eval/LABEL_GUIDE.md).

  python eval/adjudicate.py diff  A.json B.json sheets/index.json  [out.json, default eval/labels/disagreements.json]
  python eval/adjudicate.py merge A.json B.json sheets/index.json eval/labels/adjudication.json

`diff` lists every (clip, requirement, sample time) where the annotators disagree, for a third pass.
`merge` writes eval/labels/gold.json (agreed samples plus the third pass) and eval/labels/agreement.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REQS = [r["requirement_id"] for r in json.load(open(os.path.join(HERE, "requirements.json"), encoding="utf8"))]


def samples(index, clip):
    """[(t_s, shot)] from the contact-sheet index."""
    info = index[clip]
    shots = info["shots_s"]
    out = []
    for t in info["samples_s"]:
        k = next((i for i, (a, b) in enumerate(shots) if a <= t < b), len(shots) - 1)
        out.append((round(t, 3), k))
    return out


def as_set(lbl, clip, rid, times):
    got = set()
    for t in lbl.get(clip, {}).get(rid, []):
        near = min(times, key=lambda x: abs(x - float(t))) if times else None
        if near is not None and abs(near - float(t)) <= 0.6:          # snap to the printed sample time
            got.add(near)
    return got


def intervals(pos, smp):
    """Positive samples -> merged [start, end) intervals; consecutive samples in the same shot are merged."""
    out, cur = [], None
    for t, shot in smp:
        if t in pos:
            if cur and cur[2] == shot and t - cur[1] <= 1.5:
                cur[1] = t
            else:
                if cur:
                    out.append([cur[0], round(cur[1] + 1.0, 3)])
                cur = [t, t, shot]
        elif cur:
            out.append([cur[0], round(cur[1] + 1.0, 3)])
            cur = None
    if cur:
        out.append([cur[0], round(cur[1] + 1.0, 3)])
    return out


def iou_sets(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def diff(A, B, index):
    out = []
    for clip in sorted(index):
        times = [t for t, _ in samples(index, clip)]
        for rid in REQS:
            a, b = as_set(A, clip, rid, times), as_set(B, clip, rid, times)
            for t in sorted(a ^ b):
                out.append({"clip": clip, "requirement_id": rid, "t": t, "A": t in a, "B": t in b})
    return out


def merge(A, B, index, adj, brand=None):
    brand = brand or {}
    decide = {(d["clip"], d["requirement_id"], round(float(d["t"]), 3)): bool(d["positive"]) for d in adj}
    gold, n, agree_iv, tp = {"clips": {}}, 0, 0, {"a": 0, "b": 0, "ab": 0, "none": 0}
    per_req = {r: {"pairs": 0, "agree": 0} for r in REQS}
    missing = []
    for clip in sorted(index):
        smp = samples(index, clip)
        times = [t for t, _ in smp]
        gold["clips"][clip] = {}
        for rid in REQS:
            a, b = as_set(A, clip, rid, times), as_set(B, clip, rid, times)
            pos = set(a & b)
            for t in a ^ b:
                k = (clip, rid, t)
                if k not in decide:
                    missing.append(k)
                elif decide[k]:
                    pos.add(t)
            gold["clips"][clip][rid] = intervals(pos, smp)
            ok = iou_sets(a, b) >= 0.5
            n += 1
            agree_iv += ok
            per_req[rid]["pairs"] += 1
            per_req[rid]["agree"] += ok
            for t in times:
                tp["ab" if (t in a and t in b) else "a" if t in a else "b" if t in b else "none"] += 1
        for key in ("SH-10_brand_readable",):
            ra, rb = A.get(clip, {}).get(key), B.get(clip, {}).get(key)
            gold["clips"][clip][key] = ra if ra == rb else brand.get(clip, "disagree")
    if missing:
        sys.exit(f"{len(missing)} disagreements have no third-pass decision, e.g. {missing[:3]}")
    tot = sum(tp.values())
    po = (tp["ab"] + tp["none"]) / tot
    pa, pb = (tp["ab"] + tp["a"]) / tot, (tp["ab"] + tp["b"]) / tot
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    agreement = {"clip_requirement_pairs": n, "pairs_agreeing_iou_ge_0.5_or_both_empty": agree_iv,
                 "pair_agreement": round(agree_iv / n, 4), "sample_level": {**tp, "observed": round(po, 4), "cohen_kappa": round(kappa, 4)},
                 "per_requirement": per_req, "third_pass_decisions": len(adj)}
    lab = os.path.join(HERE, "labels")
    json.dump(gold, open(os.path.join(lab, "gold.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    json.dump(agreement, open(os.path.join(lab, "agreement.json"), "w", encoding="utf8"), indent=1)
    print(json.dumps({k: v for k, v in agreement.items() if k != "per_requirement"}))


if __name__ == "__main__":
    mode = sys.argv[1]
    A, B, index = (json.load(open(p, encoding="utf8")) for p in sys.argv[2:5])
    if mode == "diff":                                   # written as UTF-8 (clip names are not ASCII; consoles may not be)
        d = diff(A, B, index)
        out = sys.argv[5] if len(sys.argv) > 5 else os.path.join(HERE, "labels", "disagreements.json")
        json.dump(d, open(out, "w", encoding="utf8"), ensure_ascii=False, indent=0)
        print(len(d), "disagreements ->", out)
    else:
        rules = sys.argv[6] if len(sys.argv) > 6 else None
        merge(A, B, index, json.load(open(sys.argv[5], encoding="utf8")),
              json.load(open(rules, encoding="utf8")).get("brand", {}) if rules else None)
