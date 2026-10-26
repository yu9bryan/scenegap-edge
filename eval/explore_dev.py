"""Exploratory, DEV SPLIT ONLY (written after the one test scoring, to explain its gap-detection failure).

  python eval/explore_dev.py --mp4 F:/sg_data/commons/mp4 --work F:/sg_data/_eval

The frozen tau was chosen by frame-level F1 and turned out too permissive for project-level gap detection: on test,
every requirement found some candidate. This script sweeps tau on dev mini-projects and reports gap recall versus
wrong-reshoot rate, so a project-level objective can be pre-registered for Stage II and checked on fresh test
footage. Nothing here changes eval/results/test_metrics.json.
Status rule used here (approximation of the full system): candidate when some shot has a run of consecutive samples
>= tau whose span covers the requirement's minimum duration; not_found when no sample reaches tau.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from evaluate import available, build_project, load_inputs, make_service, wilson  # noqa: E402
from scenegap.domain.coverage import _semantic_queries  # noqa: E402
from scenegap.service import req_from_dict  # noqa: E402

GRID = [round(0.20 + 0.005 * i, 3) for i in range(21)]
NEG = ["a photo", "a blurry photo", "a photo of a room", "a photo of a street", "a photo of people", "a photo of an object"]
MGRID = [round(-0.01 + 0.0025 * i, 4) for i in range(25)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp4", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    cal = json.load(open(os.path.join(HERE, "results", "calibration.json"), encoding="utf8"))
    clips, sp, reqs, gold = load_inputs()
    dev = sorted(c["clip"] for c in clips if sp[c["clip"]] == "dev")
    svc, be = make_service(os.path.join(a.work, a.device), a.device, crop=cal["crop"])
    pid, amap, _ = build_project(svc, a.mp4, dev, "explore-dev")
    R = [req_from_dict({**{k: v for k, v in r.items() if k != "keywords"}, "revision": 1}) for r in reqs]
    assets, _ = svc._asset_indexes(pid, sorted({q for r in R for q in svc._queries(r)} | set(NEG)))
    by_clip = {amap[x.asset_id]: x for x in assets}

    def best_run_s(ai, r, tau, margin=False):
        qs = _semantic_queries(r)
        best, prev, start, shot = -1.0, None, None, None
        for s in ai.samples:
            v = min(s.sims[q] for q in qs)
            ok = (v - max(s.sims[n] for n in NEG)) >= tau if margin else v >= tau
            if ok and start is not None and s.shot_index == shot and prev is not None and s.t_ms - prev <= 1500:
                prev = s.t_ms
            elif ok:
                start, prev, shot = s.t_ms, s.t_ms, s.shot_index
            else:
                start = prev = None
            if start is not None:
                best = max(best, (prev - start) / 1000 + 1.0)
        return best

    k = max(3, min(8, len(dev) // 2))
    projects = [random.Random(f"dev-explore-{i}").sample(dev, k) for i in range(20)]

    def sweep(grid, margin):
        rows = []
        for tau in grid:
            gh = gaps = wr = av_n = fc = 0
            for sub in projects:
                for r in R:
                    need = (r.min_duration_ms or 0) / 1000
                    av = available(gold, sub, r.requirement_id, need)
                    runs = [best_run_s(by_clip[c], r, tau, margin) for c in sub]
                    status = "candidate" if any(x >= max(need, 1.0) for x in runs) else ("partial" if any(x > 0 for x in runs) else "not_found")
                    if av:
                        av_n += 1
                        wr += status == "not_found"
                    else:
                        gaps += 1
                        gh += status == "not_found"
                        fc += status == "candidate"
            rows.append({"tau": tau, "gap_recall": wilson(gh, gaps), "wrong_reshoot": wilson(wr, av_n), "false_candidate": wilson(fc, gaps)})
            print("margin" if margin else "raw", tau, rows[-1]["gap_recall"]["p"], rows[-1]["wrong_reshoot"]["p"], rows[-1]["false_candidate"]["p"])
        return rows
    rows = sweep(GRID, False)
    mrows = sweep(MGRID, True)
    out = {"split": "dev only", "projects": len(projects), "project_size": k, "frozen_tau": cal["chosen"]["tau"], "rows": rows, "margin_rows": mrows, "negative_prompts": NEG,
           "note": "exploratory, after the test scoring; used only to design the Stage II objective, never to rescore test"}
    json.dump(out, open(os.path.join(HERE, "results", "explore_dev_gap_tradeoff.json"), "w", encoding="utf8"), indent=1)


if __name__ == "__main__":
    main()
