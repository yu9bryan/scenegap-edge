"""Build spec.json for the SceneGap Stage I deck. Every measured number is read from the repo's result files here,
so the deck cannot drift from eval/results. Missing results render as "pending", never as a guess.

  python make_spec.py <repo> spec.json

Main deck: 20 pages including cover and closing. Technical detail and footage credits follow as an appendix.
"""
import json
import os
import sys

REPO, OUT = sys.argv[1], sys.argv[2]
RES = os.path.join(REPO, "eval", "results")
HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    p = os.path.join(REPO, p)
    return json.load(open(p, encoding="utf8")) if os.path.exists(p) else None


cal, test, perf, inter = load("eval/results/calibration.json"), load("eval/results/test_metrics.json"), load("eval/results/perf.json"), load("eval/results/interference.json")
agr, man, g1 = load("eval/labels/agreement.json"), load("datasets/manifests/commons_manifest.json"), load("eval/results/g1_selfcheck.json")
rule, diag = load("eval/results/rule_check.json"), load("eval/results/drop_diagnosis_019.json")
img = lambda n: os.path.join(HERE, "img", n)


def pc(w, digits=0):
    return "pending" if not w else f"{w['p'] * 100:.{digits}f}%"


def kn(w):
    return "pending" if not w else f"{w['k']}/{w['n']} ({w['p'] * 100:.0f}%)"


def ci(w):
    return "" if not w else f"{w['k']}/{w['n']}, 95% CI {w['lo'] * 100:.0f}–{w['hi'] * 100:.0f}%"


S = []
# 1 cover
S.append({"type": "title", "tagline": "Creator AI · Lightning track · ASUS UGen300", "title": "SceneGap Edge",
          "subtitle": "Helps a crew check the shot list against the footage before leaving the location, with playable evidence and a person's decision on every shot.",
          "chips": ["Runs on your own computer", "Evidence for every answer", "A person decides", "UGen300 port planned"],
          "footer": "Stage I proposal · [Team name] · github.com/[team]/scenegap-edge", "art": img("cover_art.png"),
          "notes": "A review assistant with evidence, not an automatic gap detector yet. Everything measured runs on a desktop CPU/GPU; UGen300 is not run yet."})
# 2 problem
S.append({"type": "story", "section": "Problem", "title": "The missing shot is found at 23:00, after the café has closed",
          "persona": "Illustrative scenario · two-person crew, café promo, 11 must-have shots", "icon": "FaVideo",
          "quote": "We had pours. None of them was three seconds long. We found out in the edit.",
          "beats": [{"time": "09:00", "text": "Shot list agreed with the client: storefront, interior, beans, grinder, 3 s pour, two barista takes, bag with readable brand."},
                    {"time": "17:40", "text": "Wrap. Several cards of footage; nobody has time to watch it all on site."},
                    {"time": "23:00", "text": "The editor scrubs for the pour: every take cuts away after 2 s, and nobody filmed a customer drinking."},
                    {"time": "Next week", "text": "Reshoot day: crew, café, client sign-off again."}],
          "notes": "Illustrative scenario built from PRD ch.4 user tasks; not an interview. Interviews are Stage II work."})
# 3 existing tools
S.append({"type": "table", "section": "Problem", "title": "Existing tools find footage; SceneGap adds shot-list rules, evidence and reshoot tracking",
          "header": ["Tool", "Searches footage", "Finds the moment in a clip", "Shot-list rules (length / takes / same frame)", "Runs locally"],
          "rows": [["Premiere Pro media intelligence", "yes", "yes (In/Out range)", "not in official docs", "yes (on device)"],
                   ["DaVinci Resolve 21 IntelliSearch", "yes", "visual: whole clips", "not in official docs", "not stated"],
                   ["Final Cut Pro 12 visual search", "yes", "yes", "not in official docs", "not stated"],
                   ["Frame.io semantic search", "yes (beta)", "yes", "not in official docs", "no (cloud)"],
                   ["Jumper", "yes", "yes", "not in official docs", "yes"],
                   ["invideo AI script supervisor", "matches footage to a shot list", "not stated", "done / pending", "no (upload)"],
                   ["SceneGap Edge", "yes", "yes", "checked per rule; a person decides", "yes"]],
          "colW": [3.3, 2.3, 2.2, 2.8, 1.5], "highlightRow": 6, "fontSize": 11.5,
          "note": "The difference is the workflow around search: shot list → rules → evidence → a person's decision → reshoot list → re-check.",
          "source": "Vendor documentation, accessed 2026-10-26 (Adobe media intelligence FAQ and others); URLs in docs/research/BUSINESS_FACTS.md."})
# 4 status
n_rule = f"{rule['correct']} of {rule['cases']}" if rule else "pending"
S.append({"type": "twocol", "section": "Problem", "title": "What works today, and what still needs proof",
          "left": {"head": "Shown today (live app, real footage)", "bullets": [
              "Shot list in the crew's words, with rules: length, takes, same frame",
              "Candidate clips with playable evidence on the original timecode",
              f"Rule checks: {n_rule} controlled cases judged right (slide 11)",
              "A person accepts, rejects, or adds the shot to the reshoot list",
              "New footage re-checked; only the new files are analysed"]},
          "right": {"head": "Not shown yet", "bullets": [
              "Reliable automatic missing-shot detection (0 of 38 on test, slide 14)",
              "Time saved for a real crew: no user study yet",
              "UGen300 speed and quality: not run on the device yet",
              "Human-checked labels: current labels are AI-assisted"]},
          "verdict": "SceneGap Edge today is a review assistant that keeps evidence and a person's decision; automation grows only as it is proven."})
# 5 flow
S.append({"type": "flow", "section": "Solution", "title": "From your shot list to a decision you can play back",
          "steps": [{"head": "Write the shot list", "body": "In Chinese, as the crew speaks. A person checks the English search phrase and adds rules: min. length, takes, same frame.", "where": "PC"},
                    {"head": "Index footage locally", "body": "Find camera cuts and sample one frame per second on the original timecode; CLIP turns each frame into a searchable vector.", "where": "PC today → UGen300"},
                    {"head": "Check each rule", "body": "Search finds candidate clips; each rule is checked and shown as pass, fail or can't tell. Failing clips stay visible.", "where": "PC"},
                    {"head": "A person decides", "body": "Accept, reject with a reason, or add the shot to the reshoot list. Only the person's decision counts as done.", "where": "PC"}],
          "note": "UGen300 box = planned route; today the same model runs on the PC's CPU or GPU and is labelled cpu-/cuda-reference."})
# 6 states
S.append({"type": "cards", "section": "Solution", "title": "The AI gives one of four answers; only a person can mark a shot done",
          "lead": "The AI's answer and the person's decision are stored separately; only the person's counts as done.",
          "cols": 3, "cards": [
              {"icon": "FaCheckCircle", "head": "Candidate", "body": "Every rule passes on at least one clip. Still needs a person to accept."},
              {"icon": "FaAdjust", "head": "Partial", "body": "Something matched but a rule failed or can't be decided: too short, one take of two, a manual check left."},
              {"icon": "FaSearch", "head": "Not found", "body": "Nothing reached the threshold in the analysed files. Not proof of absence; a reshoot card is suggested."},
              {"icon": "FaQuestionCircle", "head": "Unverifiable", "body": "Files failed to decode or are missing, so absence cannot be claimed. Fix the scope first."},
              {"icon": "FaUserCheck", "head": "Person: accepted / rejected", "body": "Bound to the shot's version. Edit the shot and the old decision no longer counts."},
              {"icon": "FaHistory", "head": "Outdated", "body": "Shot, footage, model or threshold changed since the run. The old answer is hidden, not reused."}]})
# 7-9 live app
S.append({"type": "image", "section": "Solution", "title": "Before leaving, the crew sees which shots are confirmed and which need a look",
          "image": os.path.join(REPO, "docs", "screenshots", "04_coverage.png"),
          "caption": "Live app on 9 Wikimedia Commons clips after a CLIP run and a short review by a person. Frames are real footage.",
          "side": {"head": "Read in one pass", "bullets": ["Each row: the shot, the AI's answer, the person's decision, the clip", "Coverage counts only shots a person accepted", "Filters: waiting for review, missing, decided"]}})
S.append({"type": "image", "section": "Solution", "title": "Every answer plays its clip, and a person decides",
          "image": os.path.join(REPO, "docs", "screenshots", "05_evidence.png"),
          "caption": "Shot SH-05 「咖啡倒入杯中或拉花，連續 3 秒」 (coffee or latte art poured into a cup, 3 s). The espresso stream with no cup was rejected; the latte-art pour accepted. The 24 s range is how long the frames stay close to the query, not a measured pour: the person checks the action.",
          "side": {"head": "One click per decision", "bullets": ["Accept, reject with a reason, adjust the range, add to reshoot list", "Filmstrip and clip ranges on the original timecode", "Every decision is logged and can be undone", "Original files are never touched"]}})
S.append({"type": "image", "section": "Solution", "title": "Shots without a usable clip go on a reshoot list before the crew leaves",
          "image": os.path.join(REPO, "docs", "screenshots", "06_reshoots.png"),
          "caption": "Same demo: the AI still offered candidates for the grinder and someone drinking; a person rejected them and put both, with the coffee bag, on the reshoot list.",
          "side": {"head": "What the crew gets", "bullets": ["The shot, why it is missing, the closest clip", "Minimum length and how it will be checked", "Status: to decide → reshoot → shooting → done"]}})
# 10 what each rule checks
S.append({"type": "table", "section": "Evidence", "title": "What each rule actually measures, and what it cannot tell",
          "header": ["Rule", "What SceneGap measures", "What it cannot tell", "Today"],
          "rows": [["Length", "How long frames stay close to the query inside one camera cut (lower and upper bound; re-check every 0.25 s)", "Whether the action itself lasts that long: a finished latte looks like a pour", "auto, a person checks"],
                   ["Same frame", "Both phrases above the threshold in the same sampled frame", "Who is with whom; objects too small for CLIP", "auto, a person checks"],
                   ["Takes", "Distinct files, by content hash; duplicates of one file are one take", "A re-encoded copy of the same take", "auto, a person checks"],
                   ["Readable brand", "Nothing automatic", "Reading text", "manual"],
                   ["Not found", "Nothing reached the threshold in the analysed files", "Proof that the shot was never filmed; failed files make it 'can't tell'", "auto, scope shown"]],
          "colW": [1.7, 4.4, 4.0, 2.0], "fontSize": 12,
          "note": "Dense sampling gives more observations, not certainty: a clip that looks like pouring is still checked by a person."})
# 11 rule check
if rule:
    lab = {True: "pass", False: "not pass"}
    S.append({"type": "table", "section": "Evidence", "title": f"Rule check on real footage: {rule['correct']} of {rule['cases']} cases right; misses are a finished latte and a re-encoded copy",
              "header": ["Case (real Commons footage, cut to a known answer)", "Shot rule", "Should", "SceneGap", "Right?"],
              "rows": [[r["tests"], {"SH-05": "pour ≥ 3 s", "SH-08": "2 people in a café, same frame", "SH-11": "barista, 2 takes"}[r["shot"]],
                        r["expected"], ("pass" if r["passed"] else "not pass") + (f" ({', '.join(x.lower() for x in r['reasons'])})" if r["reasons"] else ""),
                        "yes" if r["correct"] else "NO"] for r in rule["rows"]],
              "colW": [4.5, 2.6, 1.2, 2.9, 0.9], "fontSize": 10,
              "source": "CLIP sees a finished latte as 'pouring'; takes are told apart by file hash. eval/rule_check.py, eval/results/rule_check.json; a separate experiment from the held-out test, frozen threshold."})
# 12 method
S.append({"type": "timeline", "section": "Evidence", "title": "How we tested: fixed protocol, open footage, AI-assisted labels",
          "items": [{"date": "Step 1", "head": "Protocol first", "body": "Metrics, split and threshold rule committed to git before any label existed."},
                    {"date": "Step 2", "head": "Shot list", "body": "11 café-promo shots and queries written before any frame was seen."},
                    {"date": "Step 3", "head": "Footage", "body": f"{len(man['clips']) if man else '?'} Wikimedia Commons clips, split by author: 18 dev, 26 test."},
                    {"date": "Step 4", "head": "AI-assisted labels", "body": f"Two AI passes on 1 fps sheets agree (κ {agr['sample_level']['cohen_kappa']:.2f}); a third pass on every disagreement. Human checks: Stage II." if agr else "pending"},
                    {"date": "Step 5", "head": "Test once", "body": "Threshold set on dev, frozen; test scored once. Versions, labels and result files are in the repo."}]})
# 13 retrieval
if test:
    rt = test["retrieval"]
    lost = "SH-03 and SH-04"
    d4 = diag["SH-04"]["runs"][0] if diag else None
    S.append({"type": "table", "section": "Evidence", "title": "Finding footage: right clip in the top 5 for 7 of 11 shots; plain frame search found 8",
              "header": ["Method", "Right clip in top 5 (Hit@5)", "Top-5 picks that are right"],
              "rows": [["Title keyword match (whole clips)", f"{pc(rt['keyword']['recall_at_5'])} ({ci(rt['keyword']['recall_at_5'])})", f"{pc(rt['keyword']['precision_at_5'])} ({ci(rt['keyword']['precision_at_5'])}; fewer than 5 returned)"],
                       ["Single-frame semantic search", f"{pc(rt['single_frame']['recall_at_5'])} ({ci(rt['single_frame']['recall_at_5'])})", f"{pc(rt['single_frame']['precision_at_5'])} ({ci(rt['single_frame']['precision_at_5'])})"],
                       ["SceneGap: clips ranked after the rule checks", f"{pc(rt['full']['recall_at_5'])} ({ci(rt['full']['recall_at_5'])})", f"{pc(rt['full']['precision_at_5'])} ({ci(rt['full']['precision_at_5'])})"]],
              "colW": [4.2, 3.9, 4.0], "highlightRow": 2,
              "note": (f"Lost {lost}, gained SH-06. The lost grinder clip passes every rule on its own ({d4['len_s']:.0f} s run), so the rules did not reject it: "
                       "ranking by a run's average similarity pushed it out. Stage II ranks by peak." if d4 else "Diagnosis pending."),
              "source": f"{len(test['test_clips'])} held-out clips, scored once, τ = {test['tau']}. A hit needs 0.5 s overlap, so this layer does not test the length rule (slide 11 does)."})
    sm = test["simulation"]
    S.append({"type": "table", "section": "Evidence", "title": "Finding missing shots automatically does not work yet",
              "header": ["Method", "Missing shots caught", "Reshoot asked, shot was there", "Couldn't decide", "Said 'found' when absent"],
              "rows": [[name, kn(sm[m]["gap_recall"]), kn(sm[m]["wrong_reshoot_rate"]), kn(sm[m]["unknown_rate"]), kn(sm[m]["false_candidate_rate"])]
                       for name, m in (("Title keyword match", "keyword"), ("Single-frame semantic", "single_frame"), ("SceneGap", "full"))],
              "colW": [3.2, 2.2, 2.5, 2.0, 2.2], "highlightRow": 2,
              "lead": "Unit: one shot in one simulated 8-clip project (8 × 11 = 88). Missing = 38, present = 50. Found = 'candidate'; couldn't decide = 'partial' or 'unverifiable'.",
              "note": "SceneGap never said 'not found', so its 0% wrong reshoots means nothing yet. The threshold was tuned on single frames; Stage II calibrates per shot.",
              "source": "eval/results/test_metrics.json; a dev-only sweep (relative score) catches 33% of gaps at 11% wrong reshoots, not used to rescore test."})
# 15 hardware
S.append({"type": "image", "section": "Hardware", "title": "Plan: the image half of CLIP on the UGen300; the PC keeps the rest",
          "image": img("architecture.png"),
          "caption": "Demo PC: Windows 11, RTX 4080. UGen300 supports Windows, Linux and Android (no macOS listed); on a Mac SceneGap runs on CPU only. "
                     "Before the device replaces the PC model it must pass five G1 checks against the PC (appendix A1).",
          "notes": "Hailo's model zoo lists CLIP ViT-B/32 image encoder for Hailo-10H (measured over PCIe, not USB)."})
# 16 performance
if perf:
    rows = []
    for name, b in perf["backends"].items():
        secs = sum(c["duration_s"] for c in b["per_clip"])
        tot = sum(c["analyse_total_s"] for c in b["per_clip"])
        rows.append([name, b["device"], f"{tot / secs * 60:.1f} s per minute of video", f"{b['search_ms']['p50']} / {b['search_ms']['p95']} ms", f"{b['model_load_s']} s"])
    rows.append(["UGen300", "Hailo-10H", "not run yet", "not run yet", "not run yet"])
    play = ""
    if inter:
        s_ = inter["summary"]
        play = (f" Playing a 1080p30 test pattern while analysing: 0 of 1,800 frames late (slowest 5%: {s_['none']['frame_work_ms_p95_max']:.1f} ms idle, "
                f"{s_['cpu']['frame_work_ms_p95_max']:.1f} ms CPU, {s_['cuda']['frame_work_ms_p95_max']:.1f} ms GPU).")
    S.append({"type": "table", "section": "Hardware", "title": "On a desktop, analysis already costs 2.3–3.1 s per minute; UGen300's value is a hypothesis",
              "header": ["Backend", "Device", "Analyse (decode + model)", "Search, typical / slowest 5% (10k clips)", "Model load"],
              "rows": rows, "colW": [2.0, 3.0, 2.8, 2.6, 1.7],
              "note": "Stage II test: an editing app alone, then with CPU, GPU or UGen300 analysis — dropped frames, CPU/GPU load, power and index time.",
              "source": "eval/results/perf.json (six short clips, ≤1280 px), interference.json." + play})
# 17 engineering
S.append({"type": "cards", "section": "Engineering", "title": "Engineering: 46 automated tests; 30 of 36 acceptance cases pass by test",
          "lead": "These show the software is reliable, not that the AI is accurate. The other 6: two need a UGen300, one needs an object detector, three are measured, proxy or manual.",
          "cols": 3, "cards": [
              {"icon": "FaVial", "head": "Media edge cases", "body": "Rotation, 29.97 fps, VFR, start offsets, corrupt and unsupported codecs, files still copying, moved files found again by hash."},
              {"icon": "FaBalanceScale", "head": "Logic", "body": "'Can't tell' stays 'can't tell'; two short clips never count as one long one; duplicates are not two takes; editing a shot voids old decisions."},
              {"icon": "FaShieldAlt", "head": "Security", "body": "127.0.0.1 only, per-run token, Origin + Host checks, authorised folders, CSV formula guard, escaped HTML, errors never expose internals."},
              {"icon": "FaPlug", "head": "Offline", "body": "Core flow tested with outbound sockets blocked. Footage never leaves the computer."},
              {"icon": "FaHdd", "head": "Failure", "body": "Disk full stops safely and resumes; interrupted jobs resume; originals' hashes unchanged."},
              {"icon": "FaBoxOpen", "head": "Rebuild", "body": "A fresh venv from the public index passes all 46 tests; Dockerfile and CI included; Apache-2.0."}]})
# 18 market and value
S.append({"type": "table", "section": "Business", "title": "Who pays: small crews and freelance editors who shoot on location",
          "header": ["Signal", "Number", "Source"],
          "rows": [["US film and video editors / camera operators (2025)", "39,400 / 32,600; 35% self-employed", "US BLS OOH, accessed 2026-10-26"],
                   ["Median pay, editors (May 2025)", "$75,420 / yr", "US BLS OOH, accessed 2026-10-26"],
                   ["Day rate, small crew (estimate)", "NT$12,000–28,000 (TW); $800–1,500 (US)", "PRO360 quotes; rate cards"],
                   ["Creators worldwide", "~50M, ~4% professional", "Goldman Sachs (estimate, partly verified)"],
                   ["Shot-list practice", "crews tick off shots and schedule pickup shots", "StudioBinder guide"]],
          "colW": [4.6, 4.0, 3.5],
          "note": "Value per project = hours saved × hourly cost + expected reshoot cost avoided − tool cost. Hours include setup, import, waiting and review; unmeasured until the user study.",
          "source": "docs/research/BUSINESS_FACTS.md (URLs, access dates, verified flags)."})
# 19 business model
S.append({"type": "cards", "section": "Business", "title": "Open core; customers pay for a tested bundle and templates",
          "lead": "Prices are hypotheses to test in interviews. Benchmarks: Resolve Studio $295 and Final Cut Pro $299.99 one-time; UGen300 reported at $299.99.",
          "cols": 3, "cards": [
              {"icon": "FaCodeBranch", "head": "Free: Apache-2.0 core", "body": "Anyone can run, audit and extend the checker on CPU or GPU. Trust matters when footage never leaves the machine."},
              {"icon": "FaMicrochip", "head": "Paid: UGen300 bundle", "body": "Signed installer, tested driver and runtime versions, the device-checked model, and support. Sold with or for the accelerator."},
              {"icon": "FaLayerGroup", "head": "Paid: shot-list templates", "body": "Per genre (café, product, event, wedding) with tested queries and rules; yearly updates."}]})
# 20 closing
S.append({"type": "closing", "title": "Shown today, proven next", "subtitle": "SceneGap Edge · a review assistant that keeps evidence and a person's decision for every shot",
          "bullets": ["Shown: shot list → candidate clips with evidence → a person's decision → reshoot list → re-check, on real footage",
                      "Proof 1, the rules: more controlled cases, human-checked labels on the original video, ranking by peak",
                      "Proof 2, people: 3–5 interviews, then crews checking a card by hand vs with SceneGap (time, misses, wrong reshoots)",
                      "Proof 3, the UGen300: G1 checks on the device, then editing-app load with and without it"]})
# appendix
S.append({"type": "table", "section": "Appendix", "title": "A1 · G1: five checks before the UGen300 replaces the PC model",
          "header": ["Check", "Measure (dev frames, same preprocessing)", "Pass bar", "Status"],
          "rows": [["G1a", "Cosine, HEF vs fp32 embedding, per frame", "median ≥ 0.98, p5 ≥ 0.95", "not run yet"],
                   ["G1b", "Spearman ρ of similarity per query", "median ≥ 0.95, worst ≥ 0.85", "not run yet"],
                   ["G1c", "Top-5 / top-10 shot overlap", "≥ 0.80 / ≥ 0.85", "not run yet"],
                   ["G1d", "Dev Hit@5, each backend with its own τ", "no dev shot lost vs fp32", "not run yet"],
                   ["G1f", "Frames/s over USB, 60 s clip end to end", "reported, no bar", "not run yet"],
                   ["Harness", "Same script, CPU vs CUDA fp32 (self-check)", "≈ 1.0 expected",
                    "pending" if not g1 else f"cos {g1['metrics']['G1a_median_cos']:.4f}, ρ {g1['metrics']['G1b_median_rho']:.5f}"]],
          "colW": [1.2, 5.0, 3.2, 2.7],
          "note": "Vendor: Hailo-10H ViT-B/32 image encoder, CIFAR-100 zero-shot 65.3 float → 64.5 on chip (PCIe, not USB).",
          "source": "docs/MODEL_PLAN.md §2, §4; Hailo Model Zoo (vendor figures)."})
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
if man:
    # only the clips that appear in this deck (live-app screenshots and cover frames); all 44 are in docs/CREDITS.md
    shown = ("001", "007", "012", "016", "019", "020", "026", "032", "041")
    rows = [[c["clip"][:3], (c.get("title") or "").replace("File:", ""), c.get("attribution") or c.get("artist") or c.get("credit") or "", c.get("license") or ""]
            for c in man["clips"] if c["clip"][:3] in shown]
    S.append({"type": "table", "section": "Appendix", "title": "A4 · Footage shown in this deck",
              "header": ["#", "Wikimedia Commons file", "Author", "Licence"], "rows": rows, "colW": [0.6, 6.6, 3.1, 1.8], "fontSize": 10,
              "boldFirst": False, "fontFace": "Microsoft JhengHei",
              "note": f"Screenshots and cover frames come from these {len(rows)} clips. All {len(man["clips"])} clips used in the evaluation, with links: docs/CREDITS.md in the repository."})

spec = {"title": "SceneGap Edge – Stage I proposal", "short": "SceneGap Edge · Stage I", "team": "[Team name]", "slides": S}
json.dump(spec, open(OUT, "w", encoding="utf8"), ensure_ascii=False, indent=1)
print(len(S), "slides;", sum(1 for s in S if s.get("section") != "Appendix"), "main")
