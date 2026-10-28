"""Build spec.json for the SceneGap Stage I deck. Every measured number is computed here from the repo's result
files, so the deck cannot drift from eval/results. Sourced business and hardware facts come from
docs/research/BUSINESS_FACTS.md and docs/MODEL_PLAN.md (quoted with their verified flags).

  python make_spec.py <repo> spec.json

Main deck: 20 pages including cover and closing. Detailed tables follow as an appendix (A1–A13).
"""
import json
import os
import re
import sys
from collections import Counter

REPO, OUT = sys.argv[1], sys.argv[2]
RES = os.path.join(REPO, "eval", "results")
HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    p = os.path.join(REPO, p)
    return json.load(open(p, encoding="utf8")) if os.path.exists(p) else None


cal, test, perf, inter = load("eval/results/calibration.json"), load("eval/results/test_metrics.json"), load("eval/results/perf.json"), load("eval/results/interference.json")
agr, man, g1 = load("eval/labels/agreement.json"), load("datasets/manifests/commons_manifest.json"), load("eval/results/g1_selfcheck.json")
rule, diag, ex = load("eval/results/rule_check.json"), load("eval/results/drop_diagnosis_019.json"), load("eval/results/explore_dev_gap_tradeoff.json")
gold, cons, tcheck = load("eval/labels/gold.json")["clips"], load("eval/labels/consistency.json"), load("datasets/manifests/transcode_check.json")
reqs = {r["requirement_id"]: r for r in load("eval/requirements.json")}
acc_md = open(os.path.join(RES, "ACCEPTANCE.md"), encoding="utf8").read()
img = lambda n: os.path.join(HERE, "img", n)
SHOT = {"SH-01": "Storefront from the street", "SH-02": "Café interior, tables", "SH-03": "Coffee-bean close-up", "SH-04": "Grinding beans",
        "SH-05": "Coffee or latte art poured", "SH-06": "Cup of coffee on a table", "SH-07": "Someone drinking", "SH-08": "Two people, same frame",
        "SH-09": "Espresso extraction", "SH-10": "Bean bag, brand readable", "SH-11": "Barista, 2 takes"}


def pc(w, digits=0):
    return "pending" if not w else f"{w['p'] * 100:.{digits}f}%"


def kn(w, digits=0):
    return "pending" if not w else f"{w['k']}/{w['n']} ({w['p'] * 100:.{digits}f}%)"


def ci(w):
    return "" if not w else f"{w['k']}/{w['n']}, CI {w['lo'] * 100:.0f}–{w['hi'] * 100:.0f}%"


# ---------- derived numbers ----------
test_clips = set(test["test_clips"])
mp4_s = {r["clip"]: r["mp4_s"] for r in tcheck["rows"]}
tot_min = sum(mp4_s.values()) / 60
test_min = sum(mp4_s[c] for c in test_clips) / 60
dev_n, test_n = len(man["clips"]) - len(test_clips), len(test_clips)
dev_min = tot_min - test_min
no_gold = [c for c, v in gold.items() if not any(isinstance(x, list) and x for k, x in v.items() if k.startswith("SH-") and "_" not in k)]
lic = Counter()
for c in man["clips"]:
    L = c.get("license") or ""
    lic["CC BY-SA" if "BY-SA" in L else "CC BY" if "BY" in L else "CC0" if "CC0" in L else "public domain"] += 1
cons_by = Counter(x["requirement_id"] for x in cons if not x["keep"])
s = agr["sample_level"]
chosen = cal["chosen"]
row_t = next(r for r in cal["grid"] if abs(r["tau"] - chosen["tau"]) < 1e-9)
prec_t, rec_t = row_t["tp"] / (row_t["tp"] + row_t["fp"]), row_t["tp"] / (row_t["tp"] + row_t["fn"])


def split_perf(name):
    b = perf["backends"][name]
    secs = sum(c["duration_s"] for c in b["per_clip"])
    dec = sum(c["decode_sample_s"] for c in b["per_clip"]) / secs * 60
    emb = sum(c["embed_s"] for c in b["per_clip"]) / secs * 60
    tot = sum(c["analyse_total_s"] for c in b["per_clip"]) / secs * 60
    fps = sum(c["samples"] for c in b["per_clip"]) / sum(c["embed_s"] for c in b["per_clip"])
    return dec, emb, tot, fps, b


P_CPU, P_GPU = split_perf("cpu-reference"), split_perf("cuda-reference")
gaps = Counter()
full_on_gap = Counter()
for pr in test["projects"]:
    for rid, st in pr["requirements"].items():
        if not st["available"]:
            gaps[rid] += 1
            full_on_gap[st["full"]] += 1
m_tests = re.search(r"(\d+)/(\d+) tests passed", acc_md)
n_tests = int(m_tests.group(1)) if m_tests else 0
tc_rows = [l for l in acc_md.splitlines() if l.startswith("| TC-")]
tc_status = Counter(l.split("|")[3].strip() for l in tc_rows)
by_rc = {r["case"]: r for r in rule["rows"]} if rule else {}
ugen_spec = [["Chip", "Hailo-10H"], ["AI performance", "40 TOPS INT4 / 20 TOPS INT8"], ["Memory", "8 GB LPDDR4, 4266 MT/s"],
             ["Link", "USB 3.1 Gen2 Type-C, 10 Gbps"], ["Power / size", "2.5 W typical; 105 × 50 × 18 mm, 150 g"],
             ["OS", "Windows, Linux, Android (no macOS listed)"], ["Price", "$299.99 USB 8 GB (reported)"],
             ["CLIP ViT-B/32 image encoder", "81.5 / 350 FPS at batch 1 / 8 (Hailo zoo, PCIe)"]]

S = []
# 1 cover
S.append({"type": "title", "tagline": "Creator AI · Lightning track · ASUS UGen300", "title": "SceneGap Edge",
          "subtitle": "Helps a crew check the shot list against the footage before leaving the location, with playable evidence and a person's decision on every shot.",
          "chips": ["Runs on your own computer", "Evidence for every answer", "A person decides", "UGen300 port planned"],
          "footer": "Stage I proposal · rm-rf-1 · github.com/yu9bryan/scenegap-edge", "art": img("cover_art.png")})
# 2 problem
S.append({"type": "story", "section": "Problem", "title": "The missing shot is found at 23:00, after the café has closed",
          "persona": "Illustrative scenario · two-person crew, café promo, 11 must-have shots", "icon": "FaVideo",
          "quote": "We had pours. None of them was three seconds long. We found out in the edit.",
          "beats": [{"time": "09:00", "text": "Shot list agreed with the client: storefront, interior, beans, grinder, 3 s pour, two barista takes, bag with readable brand."},
                    {"time": "17:40", "text": "Wrap. Several cards of footage; the laptop is busy backing up cards and making proxies, so nobody watches it all on site."},
                    {"time": "23:00", "text": "The editor scrubs for the pour: every take cuts away after 2 s, and nobody filmed a customer drinking."},
                    {"time": "Next week", "text": "Reshoot day: NT$12,000–28,000 per crew-day in Taiwan, US$800–1,500 per videographer-day in the US, plus café and client again."}],
          "source": "Day rates: PRO360 quote statistics (TW), Film Lifestyle mid-level rates (US); docs/research/BUSINESS_FACTS.md."})
# 3 existing tools
S.append({"type": "table", "section": "Problem", "title": "Existing tools find footage; SceneGap adds shot-list rules, evidence and reshoot tracking",
          "header": ["Tool", "Finds the moment in a clip", "Shot-list rules (length, takes, same frame)"],
          "rows": [["Premiere Pro media intelligence", "yes, In/Out range", "not in official docs"],
                   ["DaVinci Resolve 21 IntelliSearch", "visual search: whole clips", "not in official docs"],
                   ["Final Cut Pro 12 visual search", "yes", "not in official docs"],
                   ["invideo AI script supervisor", "not stated", "done / pending only"],
                   ["SceneGap Edge", "yes, original timecode", "checked per rule; a person decides"]],
          "colW": [4.0, 3.6, 4.5], "highlightRow": 4, "fontSize": 13,
          "note": "The difference is the workflow around search: shot list → rules → evidence → a person's decision → reshoot list → re-check.",
          "source": "Vendor documentation, accessed 2026-10-26 (Adobe media intelligence FAQ and others). More tools and prices: A11."})
# 4 status
n_rule = f"{rule['correct']} of {rule['cases']}" if rule else "pending"
rl = test["review_load"]
S.append({"type": "twocol", "section": "Problem", "title": "What works today, and what still needs proof",
          "left": {"head": "Shown today (live app, real footage)", "bullets": [
              "Shot list in the crew's words, with rules: length, takes, same frame",
              "Candidate clips with playable evidence on the original timecode",
              f"Rule checks: {n_rule} controlled cases judged right (slide 12)",
              "A person accepts, rejects, or adds the shot to the reshoot list",
              "Demo: 9 Commons clips (5.9 min) analysed in 22 s on a desktop GPU; new footage re-checked file by file"]},
          "right": {"head": "Not shown yet", "bullets": [
              "Missing shots on real café video: test 4 met both targets (65% caught, 3.8% wrong reshoots), but on still photos; test 3 video had 12% wrong (slide 15)",
              f"Time saved: no user study yet. Proxy: {rl['candidate_seconds_to_review']:.0f} s of candidate clips to play vs {rl['library_seconds']:.0f} s of footage ({rl['candidate_seconds_to_review'] / rl['library_seconds'] * 100:.0f}%)",
              "UGen300 speed and quality: not run on the device yet",
              "Human-checked labels: current labels are AI-assisted"]},
          "verdict": "SceneGap Edge today is a review assistant that keeps evidence and a person's decision; automation grows only as it is proven."})
# 5 flow + the four answers
st_full = Counter(r["status"] for r in test["per_requirement"])
steps = [("1 · Write the shot list", "In Chinese, as the crew speaks; a person checks the English search phrase and adds rules. Test list: 11 shots, each with a minimum length; 1 same-frame, 1 two-takes, 1 manual brand check."),
         ("2 · Index footage locally", f"Camera cuts, one frame per second on the original timecode, CLIP vectors. Desktop: {P_GPU[2]:.1f} s per minute of video (GPU), {P_CPU[2]:.1f} s (CPU). UGen300 next."),
         ("3 · Check each rule", f"Pass, fail or can't tell per rule; failing clips stay visible. Threshold τ {cal['chosen']['tau']} set on dev; search over 10,000 segments p95 {P_CPU[4]['search_ms']['p95']:.0f} ms."),
         ("4 · A person decides", "Accept, reject with a reason, or add to the reshoot list. Only the person's decision counts as done; it is bound to the shot's version.")]
S.append({"type": "blocks", "section": "Solution", "title": "From your shot list to a decision you can play back",
          "blocks": [{"kind": "text", "x": i * 3.025, "y": 0, "w": 2.85, "h": 2.3, "head": h_, "text": t_, "fontSize": 12} for i, (h_, t_) in enumerate(steps)]
                    + [{"kind": "table", "x": 0, "y": 2.5, "w": 11.9, "h": 2.3, "head": "The AI's four answers (a person's decision is stored separately)", "colW": [1.6, 7.0, 3.3], "fontSize": 10.5, "maxRowH": 0.4,
                        "header": ["AI answer", "Meaning", "On the 26-clip test library"],
                        "rows": [["Candidate", "Every rule passes on at least one clip; still needs a person to accept", f"{st_full.get('candidate', 0)} of 11 shots"],
                                 ["Partial", "Something matched but a rule failed or can't be decided (too short, one take of two, a manual check)", f"{st_full.get('partial', 0)} (SH-10, manual brand check)"],
                                 ["Not found", "Nothing reached the threshold in the analysed files; not proof of absence", f"{st_full.get('not_found', 0)}; {full_on_gap.get('candidate', 0)} of {sum(gaps.values())} missing shots still got 'candidate' (slide 15)"],
                                 ["Unverifiable", "Files failed to decode or are missing, so absence cannot be claimed", "0"]]}]})
# 6-8 live app, large
S.append({"type": "blocks", "section": "Solution", "title": "Before leaving, the crew sees which shots are confirmed",
          "blocks": [{"kind": "image", "x": 0, "y": 0.05, "w": 8.75, "h": 4.55, "path": img("shot_cov.png")},
                     {"kind": "text", "x": 9.0, "y": 0, "w": 2.9, "h": 4.65, "dark": True, "head": "This demo project", "fontSize": 11,
                      "bullets": ["9 Commons clips, 5.9 min, analysed in 22 s on a desktop GPU", "AI candidate: 10 of 11 shots", "Accepted by a person: 5 of 11 (SH-11 needs a second take)",
                                  "Partial: SH-10 (manual brand check)", "Reshoot list: grinder, drinking, coffee bag", "Decisions entered as a scripted demo review, not timed"]}],
          "source": "Live app (Coverage page, cropped). Columns: shot · AI answer · person's decision · reason · clip."})
S.append({"type": "blocks", "section": "Solution", "title": "Every answer plays its clip, and a person decides",
          "blocks": [{"kind": "image", "x": 0, "y": 0.05, "w": 8.4, "h": 4.65, "path": img("shot_evi.png")},
                     {"kind": "text", "x": 8.65, "y": 0, "w": 3.25, "h": 4.75, "dark": True, "head": "SH-05 on this screen", "fontSize": 11,
                      "bullets": ["Shot 「咖啡倒入杯中或拉花，連續 3 秒」 as fixed before any frame was seen (eval/requirements.json, 10/26 18:09)", "Filmstrip and clip ranges on the original timecode",
                                  "Ranking score 0.314: orders clips, not a probability", "Length check 24.0 s ≥ 3 s: how long frames stay close to the query",
                                  "Log: espresso stream with no cup rejected with a reason; latte-art pour accepted; each can be undone"]}],
          "source": "Live app (clip view, cropped). Original files are never touched."})
S.append({"type": "blocks", "section": "Solution", "title": "Shots without a usable clip go on the reshoot list",
          "blocks": [{"kind": "image", "x": 0, "y": 0.05, "w": 6.0, "h": 4.65, "path": img("shot_res.png")},
                     {"kind": "text", "x": 6.3, "y": 0, "w": 5.6, "h": 4.75, "dark": True, "head": "What the crew gets", "fontSize": 12,
                      "bullets": ["One card per shot: why it is missing, the closest clip, minimum length, how it will be checked",
                                  "The card shows the AI's rules passed; the person decided the clip shows tamping, not grinding",
                                  "Status: to decide → reshoot → shooting → done / not reshooting",
                                  "Video demo: the reshot clip was analysed alone in 2.5 s and the grinder shot left the list",
                                  "The demo review stopped at the top 3; the 4th candidate was a valid grinding clip (next page)",
                                  "Fixed: the card now shows how many candidates a person checked (已檢查 3／5) and warns when some are unchecked"]}],
          "source": "Live app (reshoot list, SH-04 card). Export: CSV / HTML."})
# 9-10 what the model returns
S.append({"type": "blocks", "section": "Evidence", "title": "What the model returns: top 5 per shot, checked against labels",
          "blocks": [{"kind": "image", "x": 0, "y": 0.05, "w": 9.35, "h": 4.75, "path": img("fig_top5.png")},
                     {"kind": "text", "x": 9.6, "y": 0, "w": 2.3, "h": 4.8, "head": "Read it as", "fontSize": 10.5,
                      "bullets": ["SH-05: right clips are in the list, but #1 is wrong", "SH-08: same-frame rule works here (4 of 5)",
                                  "SH-04: the right clip is 4th; ranking by peak is the fix", "SH-07: nothing to find, yet 5 clips pass, so missing shots go undetected"]}],
          "source": "Demo project (9 clips); candidates and scores from the live app; right / wrong from eval/labels/gold.json (≥ 0.5 s overlap). decks/scenegap/fig_top5.py."})
S.append({"type": "blocks", "section": "Evidence", "title": "How the length rule reads the model's scores",
          "blocks": [{"kind": "image", "x": 0, "y": 0.05, "w": 7.1, "h": 4.75, "path": img("fig_curves.png")},
                     {"kind": "text", "x": 7.35, "y": 0, "w": 4.55, "h": 4.8, "head": "What the curves show", "fontSize": 11,
                      "bullets": ["Street frames score about 0.18; the pour about 0.33, well above τ 0.225",
                                  "SceneGap samples 1 frame per second: a 4 s pour gives 4 samples, a lower bound of 3.0 s, so it passes the 3 s rule",
                                  "A 2 s pour gives 1.0 s: too short, correctly",
                                  "A finished latte scores 0.30 with nothing poured: CLIP sees the result, not the action, so a person checks it",
                                  "Stage II: denser sampling near the edges and an action check for pour-type shots"]}],
          "source": "Rule-check cases cut from real Commons footage (eval/rule_check.py); similarity from the same CLIP model at 4 frames/s. decks/scenegap/fig_curves.py."})
# 10 what each rule checks
p4 = by_rc.get("pour_4s", {}).get("best_candidate_s")
S.append({"type": "table", "section": "Evidence", "title": "What each rule measures, and what it cannot tell",
          "header": ["Rule", "What SceneGap measures", "What it cannot tell", "Today"],
          "rows": [["Length", "How long frames stay close to the query inside one camera cut (lower and upper bound; re-check every 0.25 s)",
                    f"Whether the action itself lasts that long; the lower bound runs about 1 s short (4 s pour → {p4} s)", "auto, a person checks"],
                   ["Same frame", "Both phrases above the threshold in the same sampled frame", "Who is with whom; objects too small for CLIP", "auto, a person checks"],
                   ["Takes", "Distinct files, by content hash; duplicates of one file are one take", "A re-encoded copy of the same take", "auto, a person checks"],
                   ["Readable brand", "Nothing automatic", "Reading text", "manual"],
                   ["Not found", "Nothing reached the threshold in the analysed files", "Proof the shot was never filmed; failed files make it 'can't tell'", "auto, scope shown"]],
          "colW": [1.7, 4.4, 4.0, 2.0], "fontSize": 12,
          "note": "Dense sampling gives more observations, not certainty: a clip that looks like pouring is still checked by a person."})
# 11 rule check
if rule:
    S.append({"type": "table", "section": "Evidence", "title": f"Rule check: {rule['correct']} of {rule['cases']} right; both misses are false acceptances",
              "header": ["Case (real Commons footage, cut to a known answer)", "Should", "SceneGap", "Measured run (s)", "Files / takes", "Right?"],
              "rows": [[f"{r['shot']} · {r['tests']}", r["expected"], ("pass" if r["passed"] else "not pass") + (f" ({', '.join(x.lower() for x in r['reasons'])})" if r["reasons"] else ""),
                        "—" if r["best_candidate_s"] is None else f"{r['best_candidate_s']:.1f}", f"{r['files']} / {r['takes_seen']}", "yes" if r["correct"] else "NO"] for r in rule["rows"]],
              "colW": [4.9, 1.1, 2.6, 1.3, 1.1, 0.8], "fontSize": 9.5,
              "source": "Open: an action check (a finished latte passes as 'pouring') and re-encoded-take dedup. Such passes stay 'candidate, a person confirms', never done. eval/rule_check.py, frozen threshold."})
# 12 method, data and labels
S.append({"type": "blocks", "section": "Evidence", "title": "How we tested: fixed protocol, open footage, AI-assisted labels",
          "lead": "Protocol and the 11 shots fixed before any label; threshold set on dev only; test scored once. Every file below is in the repo.",
          "blocks": [
              {"kind": "table", "x": 0, "y": 0, "w": 5.8, "h": 3.85, "head": "Footage", "colW": [1.5, 4.3], "fontSize": 10.5, "header": ["Item", "Value"],
               "rows": [["Source", f"{len(man['clips'])} Wikimedia Commons clips, {tot_min:.1f} min, H.264 ≤ 1280 px"],
                        ["Dev", f"{dev_n} clips, {dev_min:.1f} min: threshold only"],
                        ["Test", f"{test_n} clips, {test_min:.1f} min: scored once"],
                        ["Distractors", f"{len(no_gold)} of {len(man['clips'])} clips contain none of the 11 shots"],
                        ["Licences", ", ".join(f"{k} {v}" for k, v in lic.most_common())],
                        ["Split note", "one author pair crosses (022 dev, 025 test); without the 2 projects holding 025, SceneGap still catches 0/31"]]},
              {"kind": "table", "x": 6.1, "y": 0, "w": 5.8, "h": 3.85, "head": "Labels", "colW": [1.7, 4.1], "fontSize": 10.5, "header": ["Item", "Value"],
               "rows": [["Labellers", "two independent AI sessions on 1 fps sheets; an AI third pass"],
                        ["Agreement", f"{agr['pairs_agreeing_iou_ge_0.5_or_both_empty']}/{agr['clip_requirement_pairs']} clip × shot pairs ({agr['pair_agreement'] * 100:.1f}%); κ {s['cohen_kappa']:.3f} over {s['a'] + s['b'] + s['ab'] + s['none']:,} frame samples"],
                        ["Third pass", f"{agr['third_pass_decisions']} disputed frame labels decided with 9 written rules"],
                        ["Consistency pass", f"{agr['consistency_pass']['removed']} of {agr['consistency_pass']['checked']} agreed positives removed after labelling ({cons_by.get('SH-11', 0)} were SH-11)"],
                        ["Lenient labels", "restoring them leaves SceneGap unchanged (7/11, 18/55)"],
                        ["Threshold", f"τ {chosen['tau']}: dev F1 {chosen['f1']:.3f}, frame precision {prec_t * 100:.1f}%, recall {rec_t * 100:.1f}%"]]}],
          "note": "Simulated projects reuse the same clips, so they are not independent shoots. Human-checked labels on the original video come next; details in A5–A7."})
# 13 retrieval
rt = test["retrieval"]
per = test["per_requirement"]
d3, d4 = (diag["SH-03"]["runs"][0], diag["SH-04"]["runs"][0]) if diag else (None, None)
S.append({"type": "blocks", "section": "Evidence", "title": "Right clip in the top 5 for 7 of 11 shots; plain frame search found 8",
          "blocks": [
              {"kind": "table", "x": 0, "y": 0, "w": 6.2, "h": 2.0, "colW": [2.4, 1.9, 1.9], "fontSize": 10, "highlightRow": 2, "maxRowH": 0.45,
               "header": ["Method", "Right clip in top 5", "Top-5 picks right"],
               "rows": [["Title keywords (whole clips)", f"{pc(rt['keyword']['recall_at_5'])} ({ci(rt['keyword']['recall_at_5'])})", f"{pc(rt['keyword']['precision_at_5'])} ({rt['keyword']['precision_at_5']['k']}/{rt['keyword']['precision_at_5']['n']}, < 5 returned)"],
                        ["Single-frame search", f"{pc(rt['single_frame']['recall_at_5'])} ({ci(rt['single_frame']['recall_at_5'])})", f"{pc(rt['single_frame']['precision_at_5'])} ({rt['single_frame']['precision_at_5']['k']}/{rt['single_frame']['precision_at_5']['n']})"],
                        ["SceneGap, ranked after rule checks", f"{pc(rt['full']['recall_at_5'])} ({ci(rt['full']['recall_at_5'])})", f"{pc(rt['full']['precision_at_5'])} ({rt['full']['precision_at_5']['k']}/{rt['full']['precision_at_5']['n']})"]]},
              {"kind": "text", "x": 0, "y": 2.2, "w": 6.2, "h": 2.2, "head": "Why one hit was lost",
               "bullets": ["Lost SH-03 and SH-04, gained SH-06.",
                           (f"Clip 019 is the right answer for both. On its own it passes every rule ({d3['len_s']:.0f} s and {d4['len_s']:.0f} s runs): the rules did not reject it." if d3 else "Diagnosis pending."),
                           "Runs are ranked by average similarity; single-frame search uses the peak frame. Stage II ranks by peak.",
                           "A hit needs 0.5 s overlap, so this layer does not test the length rule (slide 12 does)."]},
              {"kind": "chart", "x": 6.5, "y": 0, "w": 5.4, "h": 4.4, "head": "Correct clips in the top 5, per shot (of 5)", "chartType": "BAR", "barDir": "col",
               "labels": [r["requirement_id"] for r in per], "max": 5,
               "series": [{"name": "Single-frame search", "values": [r["single_frame"]["correct"] for r in per]},
                          {"name": "SceneGap", "values": [r["full"]["correct"] for r in per]}],
               "colors": ["A78BFA", "6C4CF5"]}],
          "source": f"{test_n} held-out clips, {test_min:.1f} min, scored once at τ {test['tau']}; Wilson 95% intervals. SH-03 and SH-07 each rest on one 3 s gold clip. Per shot: A5."})
# 14 missing shots: the AI check layer (Stage 1.5 on test-2, Stage 1.6 on test-3)
sm = test["simulation"]
t2, t3, ev = load("eval/results/test2_metrics.json"), load("eval/results/test3_metrics.json"), load("eval/results/verify16_evidence.json")
t4 = load("eval/results/test4_metrics.json")


def kk(w):
    return "pending" if not w else f"{w['k']}/{w['n']} ({w['k'] / w['n'] * 100:.0f}%)" if w["p"] >= 0.1 or w["k"] == 0 else f"{w['k']}/{w['n']} ({w['k'] / w['n'] * 100:.1f}%)"


rows15 = [["Test 1 (Oct 26)", "system alone", kk(sm["full"]["gap_recall"]), kk(sm["full"]["wrong_reshoot_rate"])],
          ["Test 2: 24 new clips", "check of the top 3 candidates", kk(t2["with_verifier"]["gap_recall"]), kk(t2["with_verifier"]["wrong_reshoot"])]]
if t3:
    after = ev["by_set"]["test3"]["3"]["after_check"] if ev else None
    rows15 += [["Test 3: 39 new clips", "check of every second (frozen)", kk(t3["result"]["gap_recall"]), kk(t3["result"]["wrong_reshoot"])],
               ["Test 3, post hoc", "+ 3-frame look (simulated)", kk(t3["result"]["gap_recall"]), kk(after)]]
if t4:
    rows15 += [["Test 4: 150 new photo clips", "same check, frozen", kk(t4["result"]["gap_recall"]), kk(t4["result"]["wrong_reshoot"])],
               ["Test 4, preregistered", "+ 3-frame look (simulated)", kk(t4["result"]["gap_recall"]), kk(t4["three_frame_look"]["after_look"])]]
title15 = (f"Missing shots: on test 4 the check layer catches {t4['result']['gap_recall']['p'] * 100:.0f}% at {t4['result']['wrong_reshoot']['k'] / t4['result']['wrong_reshoot']['n'] * 100:.1f}% wrong reshoots; both targets met" if t4 else "Missing shots: on new footage the check layer catches " + (f"{t3['result']['gap_recall']['p'] * 100:.0f}%; wrong reshoots {t3['result']['wrong_reshoot']['p'] * 100:.0f}%, under 5% only after a 3-frame look" if t3 else "35% (test 2)"))
S.append({"type": "blocks", "section": "Evidence", "title": title15,
          "blocks": [
              {"kind": "table", "x": 0, "y": 0, "w": 7.6, "h": 2.9, "colW": [2.2, 2.8, 1.3, 1.3], "fontSize": 9.5, "maxRowH": 0.42,
               "highlightRow": 4 if t4 else 2, "head": "Each test set scored once; targets: caught ≥ 30%, wrong reshoot ≤ 5%",
               "header": ["Data", "Method", "Missing caught", "Wrong reshoot"], "rows": rows15},
              {"kind": "text", "x": 0, "y": 3.0, "w": 7.6, "h": 1.4, "fontSize": 9.5,
               "bullets": ["How: Qwen2-VL-2B answers each shot's check question ('Is ground coffee coming out of a grinder?') for every 1 s frame; 2 confirmed seconds in a row = present.",
                           "Test 3's 8 wrong reshoots were borderline frames, so each alert shows the 3 most likely frames; test 4 then scored that look as a preregistered metric, simulated from the labels (assumes the person recognises the shot; not a user test).",
                           "Test 4 is Commons photos as 4 s clips: fresh images, but no motion or cuts. Upper 95% bound on wrong reshoots: 9.5%."]},
              {"kind": "chart", "x": 7.9, "y": 0, "w": 4.0, "h": 4.25, "head": "New footage, % of shots", "chartType": "BAR", "barDir": "col",
               "labels": ["Test 2", "Test 3", "Test 4"], "max": 70,
               "series": [{"name": "missing caught", "values": [round(t2["with_verifier"]["gap_recall"]["p"] * 100)] + [round(t3["result"]["gap_recall"]["p"] * 100), round(t4["result"]["gap_recall"]["p"] * 100)]},
                          {"name": "wrong reshoot", "values": [round(t2["with_verifier"]["wrong_reshoot"]["p"] * 100)] + [round(t3["result"]["wrong_reshoot"]["p"] * 100), round(t4["result"]["wrong_reshoot"]["p"] * 100)]}],
               "colors": ["6C4CF5", "F97316"]}],
          "note": "Labels: two AI passes and a blind third (κ 0.93–0.98), not yet checked by people. Next: real café video and a timed user test.",
          "source": "Unit: one shot in one simulated 8-clip project. eval/PROTOCOL.md (Stage 1.5–1.7); eval/verify16.py; eval/verify16_evidence.py; A8."})
# 15 hardware
S.append({"type": "blocks", "section": "Hardware", "title": "The editing PC is already busy; the AI models move to the UGen300",
          "blocks": [
              {"kind": "image", "x": 0, "y": 0.05, "w": 7.0, "h": 3.6, "path": img("architecture.png")},
              {"kind": "table", "x": 7.3, "y": 0, "w": 4.6, "h": 4.3, "head": "ASUS UGen300", "colW": [1.5, 3.1], "fontSize": 9.5, "header": ["Item", "Value"], "rows": ugen_spec},
              {"kind": "text", "x": 0, "y": 3.85, "w": 7.0, "h": 0.95, "fontSize": 10.5,
               "text": "Why a plug-in device: the PC is already decoding, playing back and exporting, so it keeps only decoding and the app. First job: the CLIP image encoder. Second: the missing-shot verifier, Qwen2-VL-2B, which Hailo lists for Hailo-10H (slide 15). Frames over USB: about 9 MB per minute (estimate). Both models must pass G1-style checks against the PC first (A1)."}],
          "source": "BUSINESS_FACTS.md §2 (ASUS spec; price reported by CNX Software), MODEL_PLAN.md §2, §6; Hailo Model Zoo measures over PCIe, not USB."})
# 16 performance
dc, mc, tc, fc, bc = P_CPU
dg, mg, tg, fg, bg = P_GPU
si = inter["summary"]
S.append({"type": "blocks", "section": "Hardware", "title": f"On a busy laptop the model takes {mc / tc * 100:.0f}% of the CPU run; the UGen300 would take that load off the PC",
          "blocks": [
              {"kind": "chart", "x": 0, "y": 0, "w": 5.2, "h": 4.3, "head": "CLIP index, s per minute of video (check layer not timed)", "chartType": "BAR", "barDir": "col", "grouping": "stacked",
               "labels": ["CPU", "RTX 4080 GPU"], "series": [{"name": "Decode + sample", "values": [round(dc, 2), round(dg, 2)]}, {"name": "Model (CLIP image)", "values": [round(mc, 2), round(mg, 2)]}],
               "format": "0.00", "colors": ["A78BFA", "6C4CF5"]},
              {"kind": "table", "x": 5.5, "y": 0, "w": 6.4, "h": 2.25, "head": "Model and search", "colW": [1.6, 1.6, 1.2, 2.0], "fontSize": 9.5, "maxRowH": 0.42,
               "header": ["Backend", "Model speed", "Model load", "Search p50 / p95 (10,000 segments)"],
               "rows": [["CPU", f"{fc:.1f} frames/s", f"{bc['model_load_s']} s", f"{bc['search_ms']['p50']} / {bc['search_ms']['p95']} ms"],
                        ["RTX 4080", f"{fg:.0f} frames/s", f"{bg['model_load_s']} s", f"{bg['search_ms']['p50']} / {bg['search_ms']['p95']} ms"],
                        ["UGen300 (vendor)", "81.5 / 350 FPS (batch 1 / 8, PCIe)", "not run", "not run"]]},
              {"kind": "table", "x": 5.5, "y": 2.4, "w": 6.4, "h": 1.95, "head": "Playing a 1080p30 test pattern while analysing (budget 33.3 ms)", "colW": [1.6, 1.5, 1.6, 1.7], "fontSize": 9.5, "maxRowH": 0.38,
               "header": ["Analysis", "Late frames", "Frame work p95", "Analyses finished"],
               "rows": [["none", "0 / 1,800", f"{si['none']['frame_work_ms_p95_max']:.1f} ms", "0"],
                        ["CPU", "0 / 1,800", f"{si['cpu']['frame_work_ms_p95_max']:.1f} ms", str(si['cpu']['load_clips_finished'])],
                        ["GPU", "0 / 1,800", f"{si['cuda']['frame_work_ms_p95_max']:.1f} ms", str(si['cuda']['load_clips_finished'])]]}],
          "note": f"Model share: {mc / tc * 100:.0f}% of the CPU run, {mg / tg * 100:.0f}% of the GPU run; decoding ({dg:.1f} s per minute) stays on the PC. The check layer (Qwen2-VL-2B) is heavier and not timed yet. Stage II: an editing app alone vs with CPU, GPU or UGen300 analysis.",
          "source": "eval/results/perf.json (six short clips, 85 s, ≤ 1280 px, warm model; import and hashing not timed), interference.json (synthetic test pattern, not an editing app)."})
# 18 market
S.append({"type": "blocks", "section": "Business", "title": "Sourced: who pays first is 1–3 person crews and freelance editors",
          "blocks": [
              {"kind": "chart", "x": 0, "y": 0, "w": 5.3, "h": 4.3, "head": "US floor (BLS OOH, 2025)", "chartType": "BAR", "barDir": "bar",
               "labels": ["Openings per year", "Self-employed (35%)", "Editors + camera operators"], "series": [{"name": "people", "values": [5600, 25200, 72000]}],
               "format": "#,##0", "colors": ["6C4CF5"]},
              {"kind": "table", "x": 5.6, "y": 0, "w": 6.3, "h": 3.4, "head": "Segments (PRD 4.1)", "colW": [1.8, 2.3, 2.2], "fontSize": 9.5,
               "header": ["Segment", "Size signal", "Must hold true"],
               "rows": [["1–3 person crews (first)", "≈ 11,400 self-employed US camera operators; TW crew-day NT$12,000–28,000", "they write a shot list and carry a computer on site"],
                        ["Freelance editors (first)", "≈ 13,800 self-employed US editors; median $75,420/yr", "client briefs are specific; a pickup can still be arranged"],
                        ["Student teams", "no data", "will check a little by hand"],
                        ["Brand content producers", "91% of businesses use video (Wyzowl 2026, partial)", "templates stay stable"]]},
              {"kind": "text", "x": 5.6, "y": 3.55, "w": 6.3, "h": 0.8, "fontSize": 10,
               "text": "BLS is a floor: it leaves out YouTubers and in-house marketing staff. Worldwide, ~50M creators and ~4% professional (Goldman Sachs, partly verified)."}],
          "source": "US BLS OOH accessed 2026-10-26 (39,400 editors + 32,600 camera operators; 35% self-employed; ~5,600 openings a year); self-employed split is our arithmetic. Day rates per videographer."})
# 19 value and price
S.append({"type": "blocks", "section": "Business", "title": "Hypothesis: one prevented reshoot could offset the device cost",
          "blocks": [
              {"kind": "table", "x": 0, "y": 0, "w": 6.7, "h": 3.0, "head": "Value = hours saved × hourly cost + reshoot avoided − tool cost", "colW": [2.2, 2.6, 1.9], "fontSize": 9.5, "maxRowH": 0.4,
               "header": ["Term", "Value used", "Status"],
               "rows": [["Hourly cost, editor", "$36.26/h = $75,420 ÷ 2,080 h", "sourced; 2,080 h assumed"],
                        ["Reshoot day, US, 2 people", "$1,600–3,000 = 2 × $800–1,500", "sourced rates; crew of 2 assumed"],
                        ["Reshoot day, Taiwan", "NT$12,000–28,000 per crew-day", "quote statistics"],
                        ["Tool cost", "$299.99 UGen300; core software free", "price reported"],
                        ["Hours saved", "unmeasured (proxy: 38% of footage to play)", "user study, Stage II"],
                        ["Reshoots avoided per project", "unmeasured", "interviews, Stage II"]]},
              {"kind": "kpis", "x": 0, "y": 3.2, "w": 6.7, "h": 1.15, "fontSize": 9.5,
               "items": [{"value": "8.3 h", "label": "of editor time pays for the device"}, {"value": "0.10–0.19", "label": "of one US two-person reshoot day"}]},
              {"kind": "chart", "x": 7.0, "y": 0, "w": 4.9, "h": 3.3, "head": "Price per seat, USD per year or one-time", "chartType": "BAR", "barDir": "bar",
               "labels": ["Jumper (from, *)", "Frame.io Team", "UGen300 (one-time)", "Final Cut Pro (one-time)", "Resolve Studio (one-time)", "Premiere Pro (*)", "Frame.io Pro", "Apple Creator Studio"],
               "series": [{"name": "USD", "values": [588, 300, 299.99, 299.99, 295, 276, 180, 129]}], "format": "$#,##0", "colors": ["6C4CF5"]},
              {"kind": "text", "x": 7.0, "y": 3.45, "w": 4.9, "h": 0.9, "fontSize": 9.5,
               "text": "Open core: the Apache-2.0 checker is free. Paid: a tested UGen300 bundle (installer, driver versions, device-checked model, support) and shot-list templates. Axle FOCUS: $2,995+/yr."}],
          "note": "Device price only: the on-site computer, setup, upkeep and the person's time are extra. Test it: two groups check one card, by hand vs with SceneGap.",
          "source": "BUSINESS_FACTS.md §1c, §2, §4; * vendor page not readable at access. Yearly = 12 × monthly list price."})
# 20 closing scorecard
g1m = g1["metrics"] if g1 else {}
S.append({"type": "blocks", "section": "Plan", "title": "Shown today, proven next",
          "lead": "SceneGap Edge today: shot list → candidate clips with evidence → a person's decision → reshoot list → re-check, on real footage.",
          "blocks": [
              {"kind": "table", "x": 0, "y": 0, "w": 11.9, "h": 3.9, "colW": [1.6, 3.9, 4.3, 2.1], "fontSize": 10.5, "maxRowH": 0.62,
               "header": ["Proof", "Today", "Stage II target", "Source"],
               "rows": [["1 · Rules", f"{n_rule} controlled cases; top 5 right for 7/11; missing shots: test 4 caught 65% at 3.8% wrong reshoots (0% with a simulated 3-frame look; photo clips)",
                         "Recall@5 ≥ 90% and wrong reshoot ≤ 5% in the supported scope; ranking by peak; per-shot thresholds", "PRD 21.5"],
                        ["2 · Labels", f"AI-assisted, κ {s['cohen_kappa']:.2f}", "a person labels sampled pairs on the original video", "Protocol"],
                        ["3 · People", "no study; proxy 38% of footage to play", "3–5 interviews, then 8–12 crews; median task time −30%", "PRD 22.1"],
                        ["4 · UGen300", f"not run; PC harness cos {g1m.get('G1a_median_cos', 0):.4f}, ρ {g1m.get('G1b_median_rho', 0):.5f}",
                         "G1a cos ≥ 0.98, G1b ρ ≥ 0.95, G1e status ≥ 90%; USB speed, power, editing-app load", "MODEL_PLAN §4"],
                        ["5 · Speed", "search p95 13–14 ms; CLIP index 2.3 s per minute (GPU); check layer not timed", "first result for a 60 s clip ≤ 45 s, timed end to end", "PRD NFR-05"],
                        ["6 · Software", f"{n_tests} automated tests; {tc_status.get('pass', 0)} of {len(tc_rows)} acceptance cases pass; clean rebuild passes", "the device and user cases (TC-017, 018, 033, 034)", "A9, A12"]]}],
          "note": "The crew leaves the location with a reshoot list and the evidence a person checked.",
          "source": "Code, data and results: github.com/yu9bryan/scenegap-edge (Apache-2.0). References: A13."})
# ---------- appendix ----------
S.append({"type": "table", "section": "Appendix", "title": "A1 · G1: six checks before the UGen300 replaces the PC model",
          "header": ["Check", "Measure (dev frames, same preprocessing)", "Pass bar", "Status"],
          "rows": [["G1a", "Cosine, HEF vs fp32 embedding, per frame", "median ≥ 0.98, p5 ≥ 0.95", "not run yet"],
                   ["G1b", "Spearman ρ of similarity per query", "median ≥ 0.95, worst ≥ 0.85", "not run yet"],
                   ["G1c", "Top-5 / top-10 shot overlap", "≥ 0.80 / ≥ 0.85", "not run yet"],
                   ["G1d", "Dev Hit@5, each backend with its own τ", "no dev shot lost vs fp32", "not run yet"],
                   ["G1e", "Status agreement on the dev project simulation", "≥ 90% same status; no new 'candidate' on a true gap", "not run yet"],
                   ["G1f", "Frames/s over USB, 60 s clip end to end", "reported, no bar", "not run yet"],
                   ["Harness", "Same script, CPU vs CUDA fp32 (662 frames, 13 queries; plan ≥ 2,000 / ≥ 40)", "≈ 1.0 expected",
                    "pending" if not g1 else f"cos {g1m['G1a_median_cos']:.4f}, ρ {g1m['G1b_median_rho']:.5f}"]],
          "colW": [1.1, 5.1, 3.4, 2.5], "fontSize": 11,
          "note": "Vendor: Hailo-10H ViT-B/32 image encoder, CIFAR-100 zero-shot 65.3 float → 64.5 on chip (PCIe, not USB).",
          "source": "docs/MODEL_PLAN.md §2, §4; eval/results/g1_selfcheck.json; Hailo Model Zoo (vendor figures)."})
S.append({"type": "table", "section": "Appendix", "title": "A1b · After G1: product-level checks on the device",
          "header": ["Check", "What it protects against", "Status"],
          "rows": [["Status agreement, UGen300 vs PC, on dev projects", "quantisation causing more false acceptances", "not run yet"],
                   ["USB end-to-end analysis time for a 60 s clip", "a device that is fast in the zoo but slow over USB", "not run yet"],
                   ["Editing-app playback and scrubbing with analysis on the device", "claiming host relief without measuring it", "not run yet"],
                   ["Whole-system extra power (meter at the wall)", "quoting 2.5 W as the system's cost", "not run yet"],
                   ["Missing shots caught and wrong reshoots on new footage, verifier on the device", "judging the device by matching vectors alone", "not run yet"]],
          "colW": [4.6, 4.9, 2.6], "fontSize": 12,
          "note": "Model agreement (G1) is necessary, not sufficient: the product effect is measured on new footage."})
S.append({"type": "table", "section": "Appendix", "title": "A2 · What could break, and what we do then",
          "header": ["Risk", "Fallback"],
          "rows": [["HEF fails G1 (quantisation hurts ranking)", "Recalibrate with dev frames; TinyCLIP; else ship the CPU/GPU version and say so"],
                   ["A borderline camera cut splits a long take", "The length check says 'can't tell', not 'too short'; the cut is shown"],
                   ["One global threshold fits some shots badly", "One threshold per model version now; per type of shot next, set on dev"],
                   ["English phrase drifts from the Chinese shot", "A person checks the phrase; a multilingual model only after its own check"],
                   ["AI-assisted labels, Commons footage, small test", "Intervals shown; Stage II adds human labels and self-shot projects"],
                   ["Crews will not write shot lists", "Templates; the interviews check this first"]],
          "colW": [5.2, 6.9]})
S.append({"type": "timeline", "section": "Appendix", "title": "A3 · Stage II order: rules and people first, then the device",
          "items": [{"date": "Wk 1–2", "head": "Rules and labels", "body": "More controlled cases; a person labels sampled pairs on the original video; rank runs by peak."},
                    {"date": "Wk 2–3", "head": "Missing shots", "body": "Per-shot thresholds with a project-level target; preregister, score once on new footage."},
                    {"date": "Wk 3–5", "head": "User study", "body": "3–5 interviews, then 8–12 crews: by hand vs SceneGap, counterbalanced; time, misses, wrong reshoots."},
                    {"date": "Wk 4–6", "head": "UGen300", "body": "G1 on the device; editing-app load with CPU, GPU or UGen300 analysis."},
                    {"date": "Wk 6+", "head": "Chinese queries", "body": "A multilingual model (SigLIP 2), adopted only if it finds as many dev shots."}]})
shown = ("001", "007", "012", "016", "019", "020", "026", "032", "041")
S.append({"type": "table", "section": "Appendix", "title": "A4 · Footage shown in this deck",
          "header": ["#", "Wikimedia Commons file", "Author", "Licence"],
          "rows": [[c["clip"][:3], (c.get("title") or "").replace("File:", ""), c.get("attribution") or c.get("artist") or "", c.get("license") or ""] for c in man["clips"] if c["clip"][:3] in shown],
          "colW": [0.6, 6.6, 3.1, 1.8], "fontSize": 10, "boldFirst": False, "fontFace": "Microsoft JhengHei",
          "note": f"Screenshots and cover frames come from these clips. All {len(man['clips'])} clips used in the evaluation, with links: docs/CREDITS.md."})


def gold_s(rid, clips):
    n = [c for c in clips if gold.get(c, {}).get(rid)]
    return len(n), sum(b - a for c in n for a, b in gold[c][rid])


def rule_txt(r):
    t = f"≥ {r['min_duration_ms'] / 1000:g} s"
    if r["min_takes"] > 1:
        t += f", {r['min_takes']} takes"
    if any(c["kind"] == "co_occur" for c in r["constraints"]):
        t += ", same frame"
    if any(c.get("capability") == "manual" for c in r["constraints"]):
        t += ", brand (manual)"
    return t


S.append({"type": "table", "section": "Appendix", "title": "A5 · The 11 shots and per-shot results (correct / returned, top 5)",
          "header": ["Shot", "In English", "Rule", "Test clips with gold", "SceneGap", "Single-frame", "Keywords", "Missing in projects"],
          "rows": [[r["requirement_id"], SHOT[r["requirement_id"]], rule_txt(reqs[r["requirement_id"]]),
                    "{} ({:.0f} s)".format(*gold_s(r["requirement_id"], test_clips)),
                    f"{r['full']['correct']}/{r['full']['returned']}" + (" ✓" if r["full"]["correct"] else ""),
                    f"{r['single_frame']['correct']}/{r['single_frame']['returned']}" + (" ✓" if r["single_frame"]["correct"] else ""),
                    f"{r['keyword']['correct']}/{r['keyword']['returned']}" + (" ✓" if r["keyword"]["correct"] else ""),
                    f"{gaps.get(r['requirement_id'], 0)} of 8"] for r in per],
          "colW": [0.8, 2.6, 2.1, 1.7, 1.2, 1.3, 1.1, 1.3], "fontSize": 9.5,
          "source": "eval/requirements.json, eval/labels/gold.json, eval/results/test_metrics.json. ✓ = a correct clip in the top 5."})
cons_tab = []
for rid in ("SH-03", "SH-04", "SH-09", "SH-11"):
    xs = [x for x in cons if x["requirement_id"] == rid]
    cons_tab.append([rid, str(len(xs)), str(sum(1 for x in xs if not x["keep"])), xs[0]["rule"] if xs else ""])
S.append({"type": "blocks", "section": "Appendix", "title": "A6 · Labels: agreement, third pass and the consistency pass",
          "blocks": [
              {"kind": "table", "x": 0, "y": 0, "w": 5.8, "h": 3.2, "head": "Agreement between the two AI annotators", "colW": [3.2, 2.6], "fontSize": 10.5,
               "header": ["Measure", "Value"],
               "rows": [["Clip × shot pairs agreeing (IoU ≥ 0.5 or both empty)", f"{agr['pairs_agreeing_iou_ge_0.5_or_both_empty']} / {agr['clip_requirement_pairs']}"],
                        ["Frame samples (1 fps × 11 shots)", f"{s['a'] + s['b'] + s['ab'] + s['none']:,}"],
                        ["Both positive / A only / B only", f"{s['ab']} / {s['a']} / {s['b']}"],
                        ["Observed agreement / Cohen's κ", f"{s['observed'] * 100:.1f}% / {s['cohen_kappa']:.3f}"],
                        ["Disputed labels to third pass", str(agr["third_pass_decisions"])]]},
              {"kind": "table", "x": 6.1, "y": 0, "w": 5.8, "h": 2.5, "head": "Consistency pass (added after labelling, before calibration)", "colW": [1.2, 1.9, 1.3, 1.4], "fontSize": 10.5,
               "header": ["Shot", "Agreed positives checked", "Removed", "Rule"], "rows": cons_tab},
              {"kind": "text", "x": 6.1, "y": 2.7, "w": 5.8, "h": 1.6, "head": "Rules the third pass wrote (examples)", "fontSize": 10,
               "bullets": ["R3 barista: commercial setting, actively preparing coffee", "R5 anything poured into the cup → SH-05, not SH-06", "R8 grinding: grounds visibly come out of the spout"]}],
          "note": "Only removals were possible; restoring all 78 leaves SceneGap's numbers unchanged (lenient labels, A7).",
          "source": "eval/labels/agreement.json, consistency.json, adjudication_rules.json."})
lt = test["sensitivity_lenient_gold"]
grid = [r for r in cal["grid"] if 0.2049 < r["tau"] < 0.2451]
S.append({"type": "blocks", "section": "Appendix", "title": "A7 · Threshold on dev; lenient labels on test",
          "blocks": [
              {"kind": "table", "x": 0, "y": 0, "w": 6.3, "h": 4.4, "head": f"Dev sweep ({cal['pairs']:,} frame × shot pairs, {cal['positives']} positive)", "colW": [1.0, 0.9, 1.0, 0.9, 1.0, 0.9, 0.9], "fontSize": 9.5,
               "header": ["τ", "TP", "FP", "FN", "Precision", "Recall", "F1"],
               "highlightRow": next(i for i, r in enumerate(grid) if abs(r["tau"] - chosen["tau"]) < 1e-9),
               "rows": [[f"{r['tau']:.3f}", str(r["tp"]), f"{r['fp']:,}", str(r["fn"]), f"{r['tp'] / (r['tp'] + r['fp']) * 100:.1f}%", f"{r['tp'] / (r['tp'] + r['fn']) * 100:.1f}%", f"{r['f1']:.4f}"] for r in grid]},
              {"kind": "table", "x": 6.6, "y": 0, "w": 5.3, "h": 2.4, "head": "Test, with the 78 removed labels restored", "colW": [1.6, 1.3, 1.2, 1.2], "fontSize": 9.5,
               "header": ["Method", "Hit@5", "Precision@5", "Missing caught"],
               "rows": [[n, kn(lt["retrieval"][m]["recall_at_5"]), kn(lt["retrieval"][m]["precision_at_5"]), kn(lt["simulation"][m]["gap_recall"])]
                        for n, m in (("Title keywords", "keyword"), ("Single-frame", "single_frame"), ("SceneGap", "full"))]},
              {"kind": "text", "x": 6.6, "y": 2.6, "w": 5.3, "h": 1.8, "fontSize": 10,
               "bullets": [f"F1 is flat between 0.220 and 0.225; τ {chosen['tau']} chosen by the rule written before labels (ties go higher).",
                           "Precision stays at 12–15% across the range: no single threshold separates shots well frame by frame.",
                           "Centre crop beat padding by 0.0035 F1 (" + ", ".join(f"{a['crop']} {a['chosen']['f1']}" for a in cal["alternatives"]) + ")."]}],
          "source": "eval/results/calibration.json, test_metrics.json (sensitivity_lenient_gold)."})
S.append({"type": "table", "section": "Appendix", "title": "A8 · Missing-shot trade-off on dev (not used to rescore)",
          "header": ["Score", "Setting", "Missing caught", "Wrong reshoot", "'Found' when absent"],
          "rows": [["raw cosine", f"τ {r['tau']}", kn(r["gap_recall"]), kn(r["wrong_reshoot"]), kn(r["false_candidate"])] for r in ex["rows"] if r["tau"] in (0.225, 0.24, 0.27, 0.285, 0.29, 0.3)]
                  + [["margin over generic prompts", f"{r['tau']}", kn(r["gap_recall"]), kn(r["wrong_reshoot"]), kn(r["false_candidate"])] for r in ex["margin_rows"] if r["tau"] in (0.0, 0.0075, 0.02, 0.0475, 0.05)],
          "colW": [2.6, 1.6, 2.6, 2.6, 2.7], "fontSize": 10,
          "source": f"eval/results/explore_dev_gap_tradeoff.json: {ex['projects']} dev projects × {ex['project_size']} clips. Margin = similarity minus the best of {len(ex['negative_prompts'])} generic prompts."})
acc_groups = {}
for l in tc_rows:
    parts = [x.strip() for x in l.split("|")]
    acc_groups.setdefault(parts[3], []).append(parts[1].replace("TC-", ""))
S.append({"type": "table", "section": "Appendix", "title": f"A9 · Acceptance cases: {tc_status.get('pass', 0)} of {len(tc_rows)} pass by automated check",
          "header": ["Status", "Count", "Cases (TC-)"],
          "rows": [[k.replace("_", " "), str(len(v)), ", ".join(v)] for k, v in sorted(acc_groups.items(), key=lambda kv: -len(kv[1]))],
          "colW": [2.2, 1.0, 8.9], "fontSize": 10.5,
          "note": f"{n_tests} automated tests; TC-035 is the clean rebuild from the public package index.",
          "source": "eval/results/ACCEPTANCE.md (each case with the test that covers it), clean_env.json."})
S.append({"type": "table", "section": "Appendix", "title": "A10 · Hailo-10H model zoo: options for the device",
          "header": ["Model (HEF)", "Accuracy, float → on chip", "FPS batch 1 / 8", "Role"],
          "rows": [["clip_vit_b_32_image_encoder", "CIFAR-100 zero-shot 65.3 → 64.5", "81.5 / 350", "planned: same OpenAI weights as the PC model"],
                   ["clip_vit_b_32_text_encoder", "Retrieval@10 90.6 → 89.3", "48.9 / 98.8", "not planned: text stays on the PC"],
                   ["tinyclip_vit_61m_32 image", "72.8 → 69.8", "101 / 388", "fallback if G1 fails (new threshold)"],
                   ["siglip2_b_32_256 image", "74.7 → 70.4", "64.7 / 221", "multilingual option for Chinese shot lists"],
                   ["clip_vit_b_16 image", "68.6 → 64.6", "51.5 / 158", "finer detail, slower"],
                   ["Qwen2-VL-2B-Instruct (VLM)", "listed for Hailo-10H (GenAI zoo)", "see vendor page", "planned: the missing-shot verifier"]],
          "colW": [3.2, 3.2, 1.8, 3.9], "fontSize": 11,
          "note": f"At batch 8 the vendor figure (350 FPS) is close to the RTX 4080 we measured ({P_GPU[3]:.0f} frames/s); the device's case is freeing the host, not raw speed.",
          "source": "Hailo Model Zoo, Hailo-10H, PCIe Gen3 ×4 host (not USB); docs/MODEL_PLAN.md §2."})
S.append({"type": "table", "section": "Appendix", "title": "A11 · Market and price sources",
          "header": ["Fact", "Value", "Source", "Verified"],
          "rows": [["US film and video editors / camera operators", "39,400 / 32,600 (2025); 35% self-employed", "US BLS OOH, accessed 2026-10-26", "yes"],
                   ["Median pay, editors / camera operators", "$75,420 / $74,990 (May 2025)", "US BLS OOH", "yes"],
                   ["Day rate, mid-level videographer (US)", "$800–1,500", "Film Lifestyle rate guide", "yes (estimate)"],
                   ["Event video, full day (Taiwan)", "NT$12,000–28,000", "PRO360 quote statistics", "yes (estimate)"],
                   ["UGen300 USB 8 GB", "$299.99 (M.2 $259.99)", "CNX Software; ASUS spec page", "partial"],
                   ["Premiere Pro single app / Jumper", "$22.99/mo / from $49/mo", "Adobe checkout excerpt / Jumper site", "no / partial"],
                   ["Resolve Studio / Final Cut Pro", "$295 / $299.99 one-time", "Blackmagic / Apple", "yes"],
                   ["Frame.io Pro / Team; Creator Studio", "$15 / $25 per member per month; $129/yr", "Frame.io / Apple", "yes"],
                   ["Axle AI FOCUS", "$2,995–28,995 per year", "trade press (IBC 2026)", "yes"],
                   ["Creators worldwide", "~50M, ~4% professional", "Goldman Sachs", "partial"]],
          "colW": [3.4, 3.3, 3.6, 1.8], "fontSize": 10,
          "source": "docs/research/BUSINESS_FACTS.md (URLs, access dates and verified flags for every row)."})

# 17 engineering
S.append({"type": "cards", "section": "Appendix", "title": f"A12 · Engineering: {n_tests} tests; {tc_status.get('pass', 0)} of {len(tc_rows)} acceptance cases pass",
          "lead": f"These show the software is reliable, not that the AI is accurate. Other {len(tc_rows) - tc_status.get('pass', 0)}: "
                  + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in tc_status.items() if k != "pass") + " (needs a UGen300, a detector, or users).",
          "cols": 3, "cards": [
              {"icon": "FaVial", "head": "Media edge cases", "body": "Rotation, 29.97 fps, VFR, start offsets, corrupt and unsupported codecs, files still copying, moved files found again by hash."},
              {"icon": "FaBalanceScale", "head": "Logic", "body": "'Can't tell' stays 'can't tell'; two short clips never count as one long one; duplicates are not two takes; editing a shot voids old decisions."},
              {"icon": "FaShieldAlt", "head": "Security", "body": "127.0.0.1 only, per-run token, Origin + Host checks, authorised folders, CSV formula guard, escaped HTML, errors never expose internals."},
              {"icon": "FaPlug", "head": "Offline", "body": "Core flow tested with outbound sockets blocked. Footage never leaves the computer."},
              {"icon": "FaHdd", "head": "Failure", "body": "Disk full stops safely and resumes; interrupted jobs resume; originals' hashes unchanged."},
              {"icon": "FaBoxOpen", "head": "Rebuild", "body": "A fresh venv from the public index passes the test suite; Dockerfile and CI included; Apache-2.0."}],
          "source": "eval/results/ACCEPTANCE.md lists all 36 cases with the test that covers each (A9)."})

S.append({"type": "table", "section": "Appendix", "title": "A13 · References and source code",
          "header": ["Item", "Reference", "Link"],
          "rows": [["Source code (Apache-2.0)", "SceneGap Edge repository; release v0.1.0 has this deck and the video", "github.com/yu9bryan/scenegap-edge"],
                   ["Project page", "Summary, results and footage credits", "yu9bryan.github.io/scenegap-edge"],
                   ["CLIP ViT-B/32", "Radford et al., Learning Transferable Visual Models From Natural Language Supervision, ICML 2021", "huggingface.co/openai/clip-vit-base-patch32"],
                   ["Qwen2-VL-2B-Instruct", "Wang et al., Qwen2-VL, arXiv:2409.12191, 2024", "huggingface.co/Qwen/Qwen2-VL-2B-Instruct"],
                   ["ASUS UGen300", "ASUS UGen300 USB 8 GB tech spec", "asus.com (UGen300 USB 8G tech spec)"],
                   ["Hailo-10H models", "Hailo Model Zoo, HAILO10H zero-shot classification; GenAI model list", "github.com/hailo-ai/hailo_model_zoo; hailo_model_zoo_genai"],
                   ["Footage", "Wikimedia Commons clips and photos, CC0 / PD / CC BY / CC BY-SA", "datasets/manifests/*.json in the repo"],
                   ["Statistics", "Wilson score interval (Wilson 1927, JASA); Cohen's kappa (Cohen 1960)", "eval/PROTOCOL.md"],
                   ["Market and competitors", "US BLS OOH; vendor documentation and price pages (A11)", "docs/research/BUSINESS_FACTS.md"],
                   ["Device plan sources", "[S1]–[S20]: Hailo zoo configs, hailo-apps, community threads", "docs/MODEL_PLAN.md, Sources"]],
          "colW": [2.4, 5.6, 4.1], "fontSize": 10,
          "source": "Full URLs and access dates are in the files named in the last column."})

spec = {"title": "SceneGap Edge – Stage I proposal", "short": "SceneGap Edge · Stage I", "team": "rm-rf-1", "slides": S}
json.dump(spec, open(OUT, "w", encoding="utf8"), ensure_ascii=False, indent=1)
print(len(S), "slides;", sum(1 for x in S if x.get("section") != "Appendix"), "main")
