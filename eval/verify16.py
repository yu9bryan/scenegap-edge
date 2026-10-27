"""Stage 1.6: the verifier decides whether a shot exists; CLIP only chooses which frames it looks at.

  python eval/verify16.py sims  --work F:/sg_data/_eval2                       # CLIP similarity of every 1 s sample
  python eval/verify16.py dev   --dense F:/sg_data/_dense                      # sweep on all earlier data, freeze
  python eval/verify16.py test3 --dense F:/sg_data/_dense --work F:/sg_data/_eval2   # scored once
  python eval/verify16.py test4 --dense F:/sg_data/_dense --work F:/sg_data/_eval2   # Stage 1.7, scored once

Rule family (eval/PROTOCOL.md, Stage 1.6). For each shot in a project:
  1. CLIP ranks every 1 s sample of the project's clips by its similarity to the shot (the system's own score);
     the verifier looks only at the top N samples (N = all when 'none').
  2. Each looked-at sample gets P(yes) from the verifier for a question set: q0 (Stage 1.5 question built from
     query_en), main (check question from eval/verify_questions.json) or main+parts (minimum over the check
     question and its extra conditions).
  3. The shot counts as present when some run of consecutive looked-at samples in one clip and one detected shot
     has P(yes) >= theta for at least m samples (m = 1, 2, or the shot's own minimum length in seconds).
     Otherwise it is reported missing ('not_found'). When the verifier finds the shot, the system's own status
     stays (so a shot CLIP already reports missing stays missing).
Data for 'dev' is every split already scored before: dev (20 projects), test (8 projects) and test-2 (12 projects),
with their original project seeds. 'test3' scores the frozen rule once on new footage and refuses a second run.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from evaluate import PROJECT_SEED, available, wilson  # noqa: E402

RES = os.path.join(HERE, "results")
MAN = os.path.join(ROOT, "datasets", "manifests")
THETAS = [round(0.05 * i, 2) for i in range(1, 20)]
TOPN = ["none", 8, 16, 32]
QSETS = ["q0", "main", "main+parts"]
MRULE = ["1", "2", "len"]
REQS = json.load(open(os.path.join(HERE, "requirements.json"), encoding="utf8"))


def load(p):
    return json.load(open(p, encoding="utf8"))


def sources():
    """name -> (mp4 dir, dense file, gold file, projects as clip lists, system status per project and shot)."""
    from split import split
    man = load(os.path.join(MAN, "commons_manifest.json"))
    sp = split(man["clips"])
    dev = sorted(c["clip"] for c in man["clips"] if sp[c["clip"]] == "dev")
    test = sorted(c["clip"] for c in man["clips"] if sp[c["clip"]] == "test")
    t2 = sorted(c["clip"] for c in load(os.path.join(MAN, "test2_manifest.json"))["clips"])
    kd, kt = max(3, min(8, len(dev) // 2)), max(3, min(8, len(test) // 2))
    pd = [random.Random(f"dev-explore-{i}").sample(dev, kd) for i in range(20)]
    pt = [random.Random(f"{PROJECT_SEED}-{i}").sample(test, kt) for i in range(8)]
    p2 = [random.Random(f"test2-{i}").sample(t2, 8) for i in range(12)]
    vd, tm, t2m = load(os.path.join(RES, "verify_dev.json"))["raw"], load(os.path.join(RES, "test_metrics.json"))["projects"], load(os.path.join(RES, "test2_metrics.json"))["raw"]
    for projs, recs in ((pd, vd), (pt, tm), (p2, t2m)):
        assert [sorted(x) for x in projs] == [sorted(r["clips"]) for r in recs], "project seeds do not match the stored runs"
    sd = [{rid: row["status"] for rid, row in r["rows"].items()} for r in vd]
    st = [{rid: row["full"] for rid, row in r["requirements"].items()} for r in tm]
    s2 = [{rid: row["status"] for rid, row in r["rows"].items()} for r in t2m]
    return {
        "dev": ("F:/sg_data/commons/mp4", "commons.json", os.path.join(HERE, "labels", "gold.json"), pd, sd),
        "test1": ("F:/sg_data/commons/mp4", "commons.json", os.path.join(HERE, "labels", "gold.json"), pt, st),
        "test2": ("F:/sg_data/commons2/mp4", "test2.json", os.path.join(HERE, "labels", "test2", "gold.json"), p2, s2),
    }


def system_status(work, mp4_dir, projects, device="cuda"):
    """The full system's status per project and shot (same settings as every earlier test)."""
    from evaluate import build_project, make_service, set_requirements
    cal = load(os.path.join(RES, "calibration.json"))
    svc, be = make_service(os.path.join(work, device), device, crop=cal["crop"])
    if be.manifest.fingerprint != cal["fingerprint"]:
        sys.exit("model fingerprint differs from the calibrated one")
    svc.cfg["semantic_threshold"] = {be.manifest.fingerprint: cal["chosen"]["tau"]}
    out = []
    for i, clips in enumerate(projects):
        pid, _, _ = build_project(svc, mp4_dir, clips, f"v16-{i}")
        set_requirements(svc, pid, REQS)
        run = svc.compute_run(pid)
        out.append({rid: o["status"] for rid, o in run["outcomes"].items()})
    return out


def clip_sims(work, mp4_dir, clips, device="cuda"):
    """{clip: {t_ms: {rid: similarity}}} with the system's calibrated CLIP model (min over a shot's queries)."""
    from evaluate import build_project, make_service
    cal = load(os.path.join(RES, "calibration.json"))
    svc, be = make_service(os.path.join(work, device), device, crop=cal["crop"])
    if be.manifest.fingerprint != cal["fingerprint"]:
        sys.exit("model fingerprint differs from the calibrated one")
    svc.cfg["semantic_threshold"] = {be.manifest.fingerprint: cal["chosen"]["tau"]}
    pid, amap, _ = build_project(svc, mp4_dir, clips, f"sims-{len(clips)}-{os.path.basename(os.path.dirname(mp4_dir))}")
    from evaluate import set_requirements
    set_requirements(svc, pid, REQS)
    R = svc.requirements(pid)
    assets, _ = svc._asset_indexes(pid, sorted({q for r in R for q in svc._queries(r)}))
    out = {}
    for a in assets:
        c = amap[a.asset_id]
        out[c] = {}
        for s in a.samples:
            out[c][s.t_ms] = {r.requirement_id: round(min(s.sims.get(q, 0.0) for q in svc._queries(r)), 5) for r in R}
    return out


def frame_p(row, i, rid, qset):
    p = row["p"]
    if qset == "q0":
        return p[f"{rid}:q0"][i]
    v = p[f"{rid}:main"][i]
    if qset == "main+parts":
        k = 0
        while f"{rid}:part{k}" in p:
            v = min(v, p[f"{rid}:part{k}"][i])
            k += 1
    return v


_FR = {}


def project_frames(dense, sims, clips, rid):
    """All 1 s samples of the project's clips: (clip, index, shot, t_ms, clip similarity). Cached."""
    key = (id(dense), tuple(clips), rid)
    if key in _FR:
        return _FR[key]
    fr = []
    for c in clips:
        row = dense[c]
        sc = sims.get(c, {})
        ts = sorted(sc)
        for i, t in enumerate(row["t_ms"]):
            s = sc.get(t)
            if s is None and ts:                           # nearest system sample (same 1 s grid, rounding only)
                s = sc[min(ts, key=lambda x: abs(x - t))]
            fr.append((c, i, row["shot"][i], t, (s or {}).get(rid, 0.0)))
    _FR[key] = fr
    return fr


def int_keys(sims):
    return {c: {int(t): v for t, v in d.items()} for c, d in sims.items()}


def present(dense, frames, rid, qset, topn, theta, m):
    look = frames if topn == "none" else sorted(frames, key=lambda f: -f[4])[:topn]
    ok = {(c, i): frame_p(dense[c], i, rid, qset) >= theta for c, i, *_ in look}
    by = {}
    for c, i, sh, t, _ in sorted(look, key=lambda f: (f[0], f[1])):
        by.setdefault((c, sh), []).append(i)
    for (c, _), idx in by.items():
        run = best = 0
        prev = None
        for i in idx:
            run = run + 1 if ok[(c, i)] and prev is not None and i == prev + 1 and ok[(c, prev)] else (1 if ok[(c, i)] else 0)
            best = max(best, run)
            prev = i
        if best >= m:
            return True, len(look)
    return False, len(look)


def m_for(rule, r):
    if rule == "len":
        return max(1, math.ceil((r.get("min_duration_ms") or 0) / 1000))
    return int(rule)


def score_source(dense, sims, gold, projects, status, qset, topn, theta, mrule):
    gh = gaps = wr = av_n = calls = 0
    nq = {"q0": 1, "main": 1}
    for clips, sts in zip(projects, status):
        for r in REQS:
            rid = r["requirement_id"]
            fr = project_frames(dense, sims, clips, rid)
            pres, looked = present(dense, fr, rid, qset, topn, theta, m_for(mrule, r))
            pres = pres and sts[rid] != "not_found"
            parts = sum(1 for k in dense[clips[0]]["p"] if k.startswith(f"{rid}:part"))
            calls += looked * nq.get(qset, 1 + parts)
            av = available(gold, clips, rid, (r.get("min_duration_ms") or 0) / 1000)
            if av:
                av_n += 1
                wr += not pres
            else:
                gaps += 1
                gh += not pres
    return {"gap_recall": wilson(gh, gaps), "wrong_reshoot": wilson(wr, av_n), "verifier_calls": calls}


def pooled(rows):
    def add(key):
        k = sum(r[key]["k"] for r in rows)
        n = sum(r[key]["n"] for r in rows)
        return wilson(k, n)
    return {"gap_recall": add("gap_recall"), "wrong_reshoot": add("wrong_reshoot"), "verifier_calls": sum(r["verifier_calls"] for r in rows)}


def choose(rows):
    """Preregistered: pooled wrong reshoot <= 3% and every source <= 5%; then most missing shots caught;
    ties -> fewer verifier calls, then higher theta."""
    ok = [r for r in rows if r["pooled"]["wrong_reshoot"]["p"] <= 0.03 and all(s["wrong_reshoot"]["p"] <= 0.05 for s in r["by_source"].values())]
    return max(ok, key=lambda r: (r["pooled"]["gap_recall"]["p"], -r["pooled"]["verifier_calls"], r["theta"])) if ok else None


def all_sources(dense_dir):
    """Every scored set, test-3 included (after its single scoring): name -> (dense, sims, gold, projects, status)."""
    src = sources()
    data = {n: (load(os.path.join(dense_dir, d)), int_keys(load(os.path.join(dense_dir, "sims_" + ("test2" if n == "test2" else "commons") + ".json"))), load(g), pr, st)
            for n, (_, d, g, pr, st) in src.items()}
    t3 = load(os.path.join(RES, "test3_metrics.json"))
    sp = os.path.join(RES, "test3_system_status.json")          # the system's statuses on the same 20 projects
    if not os.path.exists(sp):
        json.dump(system_status("F:/sg_data/_eval2", "F:/sg_data/commons3/mp4", t3["projects_clips"]), open(sp, "w", encoding="utf8"))
    st3 = load(sp)
    data["test3"] = (load(os.path.join(dense_dir, "test3.json")), int_keys(load(os.path.join(dense_dir, "sims_test3.json"))),
                     load(os.path.join(HERE, "labels", "test3", "gold.json")), t3["projects_clips"], st3)
    return data


def loso(a, caps=(0.03, 0.02, 0.01, 0.0)):
    """Leave one scored set out: choose on the other three with the Stage 1.6 rule (pooled cap, every set <= 5%),
    report the chosen setting on the left-out set. Repeated for stricter pooled caps."""
    data = all_sources(a.dense)
    grid = [(q, t, m, th) for q in QSETS for t in TOPN for m in MRULE for th in THETAS]
    table = {}
    for q, t, m, th in grid:
        table[(q, t, m, th)] = {n: score_source(dn, sm, g, pr, st, q, t, th, m) for n, (dn, sm, g, pr, st) in data.items()}
    out = {"caps": {}}
    for cap in caps:
        folds = {}
        for held in data:
            train = [n for n in data if n != held]
            ok = [(k, v) for k, v in table.items()
                  if pooled([v[n] for n in train])["wrong_reshoot"]["p"] <= cap and all(v[n]["wrong_reshoot"]["p"] <= 0.05 for n in train)]
            if not ok:
                folds[held] = None
                continue
            k, v = max(ok, key=lambda kv: (pooled([kv[1][n] for n in train])["gap_recall"]["p"], -pooled([kv[1][n] for n in train])["verifier_calls"], kv[0][3]))
            folds[held] = {"setting": dict(zip(("qset", "topn", "m", "theta"), k)), "train": pooled([v[n] for n in train]), "held_out": v[held]}
        tot = [f["held_out"] for f in folds.values() if f]
        out["caps"][str(cap)] = {"folds": folds, "held_out_pooled": pooled(tot) if len(tot) == len(data) else None}
        print("cap", cap, {n: (f and (f["setting"]["qset"], f["setting"]["topn"], f["setting"]["m"], f["setting"]["theta"],
                                       f["held_out"]["gap_recall"]["k"], f["held_out"]["gap_recall"]["n"],
                                       f["held_out"]["wrong_reshoot"]["k"], f["held_out"]["wrong_reshoot"]["n"])) for n, f in folds.items()}, flush=True)
        if out["caps"][str(cap)]["held_out_pooled"]:
            hp = out["caps"][str(cap)]["held_out_pooled"]
            print("   held-out pooled: caught", hp["gap_recall"]["k"], "/", hp["gap_recall"]["n"], "wrong", hp["wrong_reshoot"]["k"], "/", hp["wrong_reshoot"]["n"], flush=True)
    out["all_four"] = {f"{q}|{t}|{m}|{th}": {"pooled": pooled(list(v.values())), "by_source": v} for (q, t, m, th), v in table.items()}
    json.dump(out, open(os.path.join(RES, "verify_loso.json"), "w", encoding="utf8"), indent=1)


def look3(dense, sims, gold, projects, status, fz, k=3, tol_s=0.5):
    """Stage 1.7 secondary metric: a wrong reshoot is cleared when one of the k evidence frames (the most likely
    sample per clip, top k clips, as on the reshoot card) lies inside a gold segment of the shot, +-tol_s."""
    q, tn, th, m = fz["qset"], fz["topn"], fz["theta"], fz["m"]
    av_n = wrong = left = 0
    for clips, sts in zip(projects, status):
        for r in REQS:
            rid = r["requirement_id"]
            fr = project_frames(dense, sims, clips, rid)
            pres, _ = present(dense, fr, rid, q, tn, th, m_for(m, r))
            pres = pres and sts[rid] != "not_found"
            av = available(gold, clips, rid, (r.get("min_duration_ms") or 0) / 1000)
            av_n += av
            if pres or not av:
                continue
            best = {}
            for c, i, sh, t, s in fr:
                p = frame_p(dense[c], i, rid, q)
                if c not in best or p > best[c][0]:
                    best[c] = (p, t)
            top = sorted(best.items(), key=lambda kv: -kv[1][0])[:k]
            hit = any(any(g0 - tol_s <= t / 1000 < g1 + tol_s for g0, g1 in gold["clips"].get(c, {}).get(rid, [])) for c, (p, t) in top)
            wrong += 1
            left += not hit
    return {"wrong_reshoot": wilson(wrong, av_n), "after_look": wilson(left, av_n)}


def test4(a):
    """Stage 1.7 (eval/PROTOCOL.md): the frozen Stage 1.6 rule on test-4, 30 projects x 8 clips, scored once."""
    out_p = os.path.join(RES, "test4_metrics.json")
    if os.path.exists(out_p):
        sys.exit("test4 already scored once; results are frozen")
    fz = load(os.path.join(RES, "verify16_dev.json"))["chosen"]
    mp4 = "F:/sg_data/commons4/mp4"
    clips = sorted(c["clip"] for c in load(os.path.join(MAN, "test4_manifest.json"))["clips"])
    projects = [random.Random(f"test4-{i}").sample(clips, 8) for i in range(30)]
    dense = load(os.path.join(a.dense, "test4.json"))
    sims = int_keys(load(os.path.join(a.dense, "sims_test4.json")))
    gold = load(os.path.join(HERE, "labels", "test4", "gold.json"))
    assert set(clips) <= set(dense) and set(clips) <= set(gold["clips"]), "dense scores or labels missing for some clips"
    status = system_status(a.work, mp4, projects, a.device)
    res = score_source(dense, sims, gold, projects, status, fz["qset"], fz["topn"], fz["theta"], fz["m"])
    base = score_source(dense, sims, gold, projects, status, "q0", "none", 0.0, "1")      # theta 0: the system alone
    look = look3(dense, sims, gold, projects, status, fz)
    out = {"split": "test4 (Commons photos as 4 s clips, new held-out)", "clips": len(clips), "projects": len(projects),
           "project_size": 8, "frozen": {k: fz[k] for k in ("qset", "topn", "m", "theta")}, "result": res,
           "three_frame_look": look, "system_only": base,
           "targets": {"wrong_reshoot_max": 0.05, "gap_recall_min": 0.30, "after_look_max": 0.05},
           "met_primary": res["wrong_reshoot"]["p"] <= 0.05 and res["gap_recall"]["p"] >= 0.30,
           "met_after_look": look["after_look"]["p"] <= 0.05,
           "scored_at": time.strftime("%Y-%m-%d %H:%M:%S"), "projects_clips": projects, "system_status": status}
    json.dump(out, open(out_p, "w", encoding="utf8"), indent=1)
    print(json.dumps({k: out[k] for k in ("frozen", "result", "three_frame_look", "met_primary", "met_after_look")}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sims", "dev", "test3", "loso", "test4"])
    ap.add_argument("--dense", default="F:/sg_data/_dense")
    ap.add_argument("--work", default="F:/sg_data/_eval2")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    t0 = time.time()
    if a.mode == "sims":
        out = {}
        for name, mp4 in [("commons", "F:/sg_data/commons/mp4"), ("test2", "F:/sg_data/commons2/mp4"), ("test3", "F:/sg_data/commons3/mp4"),
                         ("test4", "F:/sg_data/commons4/mp4")]:
            if not os.path.isdir(mp4) or os.path.exists(os.path.join(a.dense, f"sims_{name}.json")):
                continue
            clips = sorted(f for f in os.listdir(mp4) if f.endswith(".mp4"))
            out[name] = clip_sims(a.work, mp4, clips, a.device)
            json.dump(out[name], open(os.path.join(a.dense, f"sims_{name}.json"), "w", encoding="utf8"))
            print(name, len(clips), "clips", round(time.time() - t0), "s", flush=True)
        return
    if a.mode == "dev":
        rows = []
        src = sources()
        data = {n: (load(os.path.join(a.dense, d)), int_keys(load(os.path.join(a.dense, "sims_" + ("test2" if n == "test2" else "commons") + ".json"))), load(g), pr, st)
                for n, (_, d, g, pr, st) in src.items()}
        for qset in QSETS:
            for topn in TOPN:
                for mrule in MRULE:
                    for th in THETAS:
                        by = {n: score_source(dn, sm, g, pr, st, qset, topn, th, mrule) for n, (dn, sm, g, pr, st) in data.items()}
                        rows.append({"qset": qset, "topn": topn, "m": mrule, "theta": th, "by_source": by, "pooled": pooled(list(by.values()))})
            print(qset, "done", round(time.time() - t0), "s", flush=True)
        pick = choose(rows)
        # Stage 1.5 rule on the same data for reference is in verify_dev.json / test_metrics.json / test2_metrics.json
        out = {"split": "all earlier data: dev 20 + test 8 + test-2 12 projects", "rule": choose.__doc__.strip(),
               "grid": {"qset": QSETS, "topn": TOPN, "m": MRULE, "theta": THETAS}, "chosen": pick, "rows": rows,
               "seconds": round(time.time() - t0, 1)}
        json.dump(out, open(os.path.join(RES, "verify16_dev.json"), "w", encoding="utf8"), indent=1)
        if pick:
            print("chosen", pick["qset"], pick["topn"], pick["m"], pick["theta"], pick["pooled"])
            for n, s in pick["by_source"].items():
                print(" ", n, s["gap_recall"]["k"], "/", s["gap_recall"]["n"], "wrong", s["wrong_reshoot"]["k"], "/", s["wrong_reshoot"]["n"])
        else:
            print("no setting meets the wrong-reshoot cap")
        return
    if a.mode == "loso":
        loso(a)
        return
    if a.mode == "test4":
        test4(a)
        return
    out_p = os.path.join(RES, "test3_metrics.json")
    if os.path.exists(out_p):
        sys.exit("test3 already scored once; results are frozen")
    fz = load(os.path.join(RES, "verify16_dev.json"))["chosen"]
    clips = sorted(c["clip"] for c in load(os.path.join(MAN, "test3_manifest.json"))["clips"])
    projects = [random.Random(f"test3-{i}").sample(clips, 8) for i in range(20)]
    dense = load(os.path.join(a.dense, "test3.json"))
    sims = int_keys(load(os.path.join(a.dense, "sims_test3.json")))
    gold = load(os.path.join(HERE, "labels", "test3", "gold.json"))
    status = system_status(a.work, "F:/sg_data/commons3/mp4", projects, a.device)
    res = score_source(dense, sims, gold, projects, status, fz["qset"], fz["topn"], fz["theta"], fz["m"])
    base = score_source(dense, sims, gold, projects, status, "q0", "none", 0.0, "1")      # theta 0: the system alone
    out = {"split": "test3 (new held-out footage)", "clips": len(clips), "projects": len(projects), "project_size": 8,
           "frozen": {k: fz[k] for k in ("qset", "topn", "m", "theta")}, "result": res, "system_only": base,
           "targets": {"wrong_reshoot_max": 0.05, "gap_recall_min": 0.30},
           "met": res["wrong_reshoot"]["p"] <= 0.05 and res["gap_recall"]["p"] >= 0.30,
           "scored_at": time.strftime("%Y-%m-%d %H:%M:%S"), "projects_clips": projects, "system_status": status}
    json.dump(out, open(out_p, "w", encoding="utf8"), indent=1)
    print(json.dumps({k: out[k] for k in ("frozen", "result", "met")}, indent=1))


if __name__ == "__main__":
    main()
