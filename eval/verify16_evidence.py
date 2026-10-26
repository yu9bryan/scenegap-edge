"""Post-hoc (defined after test-3 was scored): would showing the verifier's most likely frames expose a wrong reshoot?

  python eval/verify16_evidence.py      # writes eval/results/verify16_evidence.json

For every shot the frozen Stage 1.6 rule reports missing although gold has it, take the K frames with the highest
P(yes), at most one per clip (what the reshoot card shows), and ask whether one of them is a gold frame. A wrong
reshoot "survives the check" only when none is. This assumes a person recognises the shot when shown the frame;
that is not measured (no user study).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import verify16 as V  # noqa: E402
from evaluate import available, wilson  # noqa: E402


def main(dense_dir="F:/sg_data/_dense", ks=(1, 3, 5)):
    fz = V.load(os.path.join(V.RES, "verify16_dev.json"))["chosen"]
    q, tn, m, th = fz["qset"], fz["topn"], fz["m"], fz["theta"]
    data = V.all_sources(dense_dir)
    out = {"setting": {"qset": q, "topn": tn, "m": m, "theta": th}, "post_hoc": True, "by_set": {}}
    for n, (dn, sm, g, pr, st) in data.items():
        rows = {k: {"wrong_reshoot": 0, "survives_check": 0} for k in ks}
        av_n = 0
        for clips, sts in zip(pr, st):
            for r in V.REQS:
                rid = r["requirement_id"]
                fr = V.project_frames(dn, sm, clips, rid)
                pres, _ = V.present(dn, fr, rid, q, tn, th, V.m_for(m, r))
                pres = pres and sts[rid] != "not_found"
                av = available(g, clips, rid, (r.get("min_duration_ms") or 0) / 1000)
                av_n += av
                if pres or not av:
                    continue
                best = {}
                for c, i, sh, t, s in fr:
                    p = V.frame_p(dn[c], i, rid, q)
                    if c not in best or p > best[c][0]:
                        best[c] = (p, t)
                ranked = sorted(best.items(), key=lambda kv: -kv[1][0])
                for k in ks:
                    hit = any(any(g0 <= t / 1000 < g1 for g0, g1 in g["clips"].get(c, {}).get(rid, [])) for c, (p, t) in ranked[:k])
                    rows[k]["wrong_reshoot"] += 1
                    rows[k]["survives_check"] += not hit
        out["by_set"][n] = {str(k): {"wrong_reshoot": wilson(v["wrong_reshoot"], av_n), "after_check": wilson(v["survives_check"], av_n)} for k, v in rows.items()}
        print(n, {k: (v["wrong_reshoot"], v["survives_check"], av_n) for k, v in rows.items()})
    json.dump(out, open(os.path.join(V.RES, "verify16_evidence.json"), "w", encoding="utf8"), indent=1)


if __name__ == "__main__":
    main()
