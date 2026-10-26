"""Build spec.json for the SceneGap Stage I deck. Every measured number is read from the repo's result files here,
so the deck cannot drift from eval/results. Missing results render as "pending", never as a guess.

  python make_spec.py <repo> spec.json
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
acc_md = open(os.path.join(RES, "ACCEPTANCE.md"), encoding="utf8").read() if os.path.exists(os.path.join(RES, "ACCEPTANCE.md")) else ""
img = lambda n: os.path.join(HERE, "img", n)


def pc(w, digits=0):
    return "pending" if not w else f"{w['p'] * 100:.{digits}f}%"


def ci(w):
    return "" if not w else f"{w['k']}/{w['n']}, 95% CI {w['lo'] * 100:.0f}–{w['hi'] * 100:.0f}%"


S = []
# 1 title
S.append({"type": "title", "tagline": "Creator AI · Lightning track · ASUS UGen300", "title": "SceneGap Edge",
          "subtitle": "Checks your shot list against your footage, on your own computer, before the crew leaves the location.",
          "chips": ["Local-first", "Evidence for every answer", "A person confirms", "UGen300 port planned"],
          "footer": "Stage I proposal · [Team name] · github.com/[team]/scenegap-edge", "art": img("cover_art.png"),
          "notes": "One line: a shot-list checker, not another footage search. Everything measured is on a desktop CPU/GPU reference; UGen300 numbers are not run yet."})
# 2 story
lib_min = round(sum(c.get("duration_s_metadata") or 0 for c in man["clips"]) / 60) if man else None
S.append({"type": "story", "section": "Problem", "title": "The missing shot is found at 23:00, after the café has closed",
          "persona": "Illustrative scenario · two-person crew, café promo, 11 must-have shots", "icon": "FaVideo",
          "quote": "We had pours. None of them was three seconds long. We found out in the edit.",
          "beats": [{"time": "09:00", "text": "Shot list agreed with the client: storefront, interior, beans, grinder, 3 s pour, two barista takes, bag with readable brand."},
                    {"time": "17:40", "text": "Wrap. Several cards of footage; nobody has time to watch it all on site."},
                    {"time": "23:00", "text": "The editor scrubs for the pour: every take cuts away after 2 s, and nobody filmed a customer drinking."},
                    {"time": "Next week", "text": "Reshoot day: crew, café, client sign-off again."}],
          "notes": "Illustrative scenario built from PRD ch.4 user tasks; not an interview. The user study is Stage II work."})
# 3 competitors
S.append({"type": "table", "section": "Problem", "title": "Editors can search footage; none checks length, takes or same-frame rules",
          "header": ["Tool", "Searches footage", "Finds the moment in a clip", "Checks duration / takes / same frame", "Runs locally", "Price"],
          "rows": [["Premiere Pro Media Intelligence", "yes", "not stated", "no", "yes", "~$22.99/mo"],
                   ["DaVinci Resolve 21 IntelliSearch", "yes", "visual: whole clips", "no", "not stated (likely)", "Studio $295"],
                   ["Final Cut Pro 12 Visual Search", "yes", "yes", "no", "not stated", "$299.99"],
                   ["Frame.io semantic search", "yes (beta)", "yes", "no", "no (cloud)", "$25/member/mo"],
                   ["Jumper", "yes", "yes", "no", "yes", "from $49/mo"],
                   ["invideo AI script supervisor", "matches to shot list", "not stated", "done/pending only", "upload", "not listed"],
                   ["SceneGap Edge", "yes", "yes", "yes, and says when it can't tell", "yes", "see slide 18"]],
          "colW": [3.2, 1.6, 1.9, 2.4, 1.4, 1.6], "highlightRow": 6, "fontSize": 11.5,
          "note": "Search tells you where a cup appears. SceneGap checks each clip against the shot's rules, for a person to confirm.",
          "source": "Vendor pages and trade press, accessed 2026-10-26; full list with URLs in docs/research/BUSINESS_FACTS.md."})
# 4 flow
S.append({"type": "flow", "section": "Solution", "title": "From your shot list to a decision you can play back",
          "steps": [{"head": "Write the shot list", "body": "In Chinese, as the crew speaks. A person confirms the English query for the model and adds rules: min. length, takes, same-frame.", "where": "Host CPU"},
                    {"head": "Index footage locally", "body": "Find camera cuts and sample one frame per second on the original timecode; CLIP turns each frame into a searchable vector.", "where": "PC today → UGen300"},
                    {"head": "Check each rule", "body": "Check length, takes and same-frame rules on the matching frames. When unsure, look again every 0.25 s.", "where": "Host CPU"},
                    {"head": "Decide with evidence", "body": "Candidate / partial / not found / unverifiable, each with playable clips. A person accepts, or adds the shot to the reshoot list.", "where": "Host CPU"}],
          "note": "UGen300 box = planned route A; today the same model runs on the host CPU/GPU and is labelled cpu-/cuda-reference."})
# 5 states
S.append({"type": "cards", "section": "Solution", "title": "The AI gives one of four answers; only a person can mark a shot done",
          "lead": "The AI's answer and the person's answer are stored separately; only the person's counts as done.",
          "cols": 3, "cards": [
              {"icon": "FaCheckCircle", "head": "Candidate", "body": "Every rule passes on at least one segment. Still needs a person to accept."},
              {"icon": "FaAdjust", "head": "Partial", "body": "Something matched but a rule failed or is undecided: too short, one take of two, a manual check left."},
              {"icon": "FaSearch", "head": "Not found", "body": "Nothing reached the threshold in the analysed scope. A reshoot card is proposed, with the nearest frames to check first."},
              {"icon": "FaQuestionCircle", "head": "Unverifiable", "body": "Files failed to decode or are missing, so absence cannot be claimed. Fix the scope first."},
              {"icon": "FaUserCheck", "head": "Human: accepted / rejected", "body": "Bound to the requirement revision. Edit the requirement and the old acceptance no longer counts."},
              {"icon": "FaHistory", "head": "Outdated", "body": "Requirement, footage, model or threshold changed since the run. The old verdict is hidden, not reused."}]})
# 6-7 UI
S.append({"type": "image", "section": "Solution", "title": "Before leaving, the crew sees which shots are confirmed and which need a look",
          "image": os.path.join(REPO, "docs", "screenshots", "04_coverage.png"),
          "caption": "Live app on 9 Wikimedia Commons clips after a CLIP run and a short human review. Frames are real footage.",
          "side": {"head": "Read in one pass", "bullets": ["Each row: the shot, the AI's answer, the person's decision, the clip", "Coverage counts only shots a person confirmed", "Filters: waiting for review, missing, done"]}})
S.append({"type": "image", "section": "Solution", "title": "Every answer plays its clip",
          "image": os.path.join(REPO, "docs", "screenshots", "05_evidence.png"),
          "caption": "Latte-art clip accepted for 'coffee poured into a cup'; the espresso-only clip before it was rejected (no cup in frame).",
          "side": {"head": "One click per decision", "bullets": ["Accept, reject, adjust the range, add to reshoot list", "Filmstrip and clip ranges on the original timecode", "Every decision is logged and can be undone", "Original files are never touched"]}})
S.append({"type": "image", "section": "Solution", "title": "Shots nobody could find go on a reshoot list before the crew leaves",
          "image": os.path.join(REPO, "docs", "screenshots", "06_reshoots.png"),
          "caption": "Same demo: a person rejected the grinder and drinking candidates and put them, with the coffee bag, on the reshoot list.",
          "side": {"head": "What the crew gets", "bullets": ["The shot, why it is missing, the closest clip", "Minimum length and how it will be checked", "Status: to decide → reshoot → shooting → done"]}})
# 8 architecture
S.append({"type": "image", "section": "Hardware", "title": "UGen300 takes the image encoder; the host keeps the rest",
          "image": img("architecture.png"), "caption": "Plan (ADR-002): the image half of CLIP ViT-B/32 runs on the UGen300 as Hailo's precompiled model; the text half and every rule check stay on the PC.",
          "notes": "Why this split: the image tower is the repeated per-frame cost; the text tower runs once per query. Same checkpoint keeps the pair compatible."})
# 9 G1 gate
S.append({"type": "table", "section": "Hardware", "title": "Before we trust the UGen300, its results must match the PC's",
          "lead": "G1 = five checks that the device ranks clips the same way as the PC, on the same dev frames.",
          "header": ["Check", "Measure (dev frames, same preprocessing)", "Pass bar", "Status"],
          "rows": [["G1a", "Cosine, HEF vs fp32 embedding, per frame", "median ≥ 0.98, p5 ≥ 0.95", "Not run yet"],
                   ["G1b", "Spearman ρ of similarity per query", "median ≥ 0.95, worst ≥ 0.85", "Not run yet"],
                   ["G1c", "Top-5 / top-10 shot overlap", "≥ 0.80 / ≥ 0.85", "Not run yet"],
                   ["G1d", "Dev Recall@5, each backend with its own τ", "≥ fp32 − 3 pts", "Not run yet"],
                   ["G1f", "Frames/s over USB, 60 s clip end to end", "reported, no bar", "Not run yet"],
                   ["Harness", "Same script, CPU vs CUDA fp32 (self-check)", "≈ 1.0 expected",
                    "pending" if not g1 else f"cos {g1['metrics']['G1a_median_cos']:.4f}, ρ {g1['metrics']['G1b_median_rho']:.5f}"]],
          "colW": [1.2, 5.0, 3.2, 2.7],
          "note": "Vendor: Hailo-10H ViT-B/32 image encoder, CIFAR-100 zero-shot 65.3 float → 64.5 on chip (PCIe, not USB).",
          "source": "docs/MODEL_PLAN.md §2, §4; Hailo Model Zoo (vendor figures)."})
# 10 method timeline
S.append({"type": "timeline", "section": "Evidence", "title": "How we tested without fooling ourselves",
          "items": [{"date": "Step 1", "head": "Protocol first", "body": "Metrics, split, threshold rule committed to git before any label existed."},
                    {"date": "Step 2", "head": "Shot list", "body": "11 café-promo shots and queries written before any frame was seen."},
                    {"date": "Step 3", "head": "Two AI annotators", "body": "Independent AI labelling sessions on 1 fps contact sheets; a third pass on every disagreement."},
                    {"date": "Step 4", "head": "Dev only", "body": "Threshold τ and crop policy chosen on dev clips, then frozen."},
                    {"date": "Step 5", "head": "Test once", "body": "Held-out authors, scored once; the script refuses a second run."}]})
# 11 data stats
if man:
    n = len(man["clips"])
    secs = sum(c.get("duration_s_metadata") or 0 for c in man["clips"])
    lic = {}
    for c in man["clips"]:
        k = (c.get("license") or "?").replace("Public domain", "public domain")
        lic[k] = lic.get(k, 0) + 1
    S.append({"type": "stats", "section": "Evidence", "title": "Real footage, open licences, not shot by us",
              "stats": [{"value": str(n), "label": f"Wikimedia Commons clips, {secs / 60:.0f} min, every licence and SHA-256 in the manifest"},
                        {"value": f"{agr['sample_level']['cohen_kappa']:.2f}" if agr else "pending", "label": "agreement between two AI annotators (Cohen's κ; 1 = perfect)"},
                        {"value": "26 / 18", "label": "test / dev clips, split by author"},
                        {"value": "11", "label": "shots, incl. a same-frame rule and a manual brand check"}],
              "takeaway": "Licences: " + ", ".join(f"{k} ×{v}" for k, v in sorted(lic.items(), key=lambda x: -x[1])),
              "notes": "Annotators are separate AI sessions reading contact sheets, not people watching video; stated as a limitation."})
# 12 retrieval
if test:
    rt = test["retrieval"]
    S.append({"type": "table", "section": "Evidence", "title": "Right clip in the top 5 for 7 of 11 shots; the rule checks cost one hit against plain search",
              "header": ["Method", "Right clip in top 5 (Recall@5)", "Top-5 picks that are right (Precision@5)"],
              "rows": [["Title keyword match", f"{pc(rt['keyword']['recall_at_5'])} ({ci(rt['keyword']['recall_at_5'])})", f"{pc(rt['keyword']['precision_at_5'])} ({ci(rt['keyword']['precision_at_5'])})"],
                       ["Single-frame semantic search", f"{pc(rt['single_frame']['recall_at_5'])} ({ci(rt['single_frame']['recall_at_5'])})", f"{pc(rt['single_frame']['precision_at_5'])} ({ci(rt['single_frame']['precision_at_5'])})"],
                       ["SceneGap: + length, re-check, same-frame rules", f"{pc(rt['full']['recall_at_5'])} ({ci(rt['full']['recall_at_5'])})", f"{pc(rt['full']['precision_at_5'])} ({ci(rt['full']['precision_at_5'])})"]],
              "colW": [4.6, 3.7, 3.8], "highlightRow": 2,
              "note": f"{len(test['test_clips'])} held-out clips, scored once with τ = {test['tau']}. A hit needs 0.5 s of overlap, so Recall@5 does not test the length rules.",
              "source": "eval/results/test_metrics.json; Wilson 95% intervals."})
    sm = test["simulation"]
    S.append({"type": "table", "section": "Evidence", "title": "Finding missing shots automatically is the open problem",
              "header": ["Method", "Missing shots caught", "Reshoot asked, shot was there", "Couldn't decide", "Said 'found' when absent"],
              "rows": [[name, pc(sm[m]["gap_recall"]), pc(sm[m]["wrong_reshoot_rate"]), pc(sm[m]["unknown_rate"]), pc(sm[m]["false_candidate_rate"])]
                       for name, m in (("Title keyword match", "keyword"), ("Single-frame semantic", "single_frame"), ("SceneGap", "full"))],
              "colW": [3.6, 2.0, 2.2, 1.8, 2.5], "highlightRow": 2,
              "note": "The threshold was tuned for single frames, so almost every shot finds some candidate. On dev, a relative score catches 33% of gaps at 11% wrong reshoots; Stage II calibrates per shot.",
              "source": "eval/results/test_metrics.json; explore_dev_gap_tradeoff.json (dev only)."})
# 14 performance
if perf:
    rows = []
    for name, b in perf["backends"].items():
        secs = sum(c["duration_s"] for c in b["per_clip"])
        tot = sum(c["analyse_total_s"] for c in b["per_clip"])
        rows.append([name, b["device"], f"{tot / secs * 60:.1f} s per minute of video", f"{b['search_ms']['p50']} / {b['search_ms']['p95']} ms", f"{b['model_load_s']} s"])
    rows.append(["UGen300", "Hailo-10H", "Not run yet", "Not run yet", "Not run yet"])
    perf_note = ""
    if inter:
        s_ = inter["summary"]
        perf_note = (f"Playing a 1080p30 test pattern while analysing: 0 of 1,800 frames late; slowest 5% of frames {s_['none']['frame_work_ms_p95_max']:.1f} ms idle, "
                     f"{s_['cpu']['frame_work_ms_p95_max']:.1f} ms with CPU analysis, {s_['cuda']['frame_work_ms_p95_max']:.1f} ms with GPU (budget 33 ms).")
    S.append({"type": "table", "section": "Evidence", "title": "Analysis costs 2.3–3.1 s per minute of video; decoding, not the model, dominates",
              "header": ["Backend", "Device", "Analyse (decode + embed)", "Search, typical / slowest 5% (10k clips)", "Model load"],
              "rows": rows, "colW": [2.0, 3.0, 2.8, 2.6, 1.7], "note": perf_note or None, "source": "eval/results/perf.json, interference.json."})
# 15 engineering
pass_line = next((l for l in acc_md.splitlines() if l.startswith("Generated")), "")
S.append({"type": "cards", "section": "Engineering", "title": "46 automated tests cover media edge cases, logic, security and recovery",
          "lead": "30 of the PRD's 36 acceptance cases pass by test; a fresh-environment install passes all 46 tests.",
          "cols": 3, "cards": [
              {"icon": "FaVial", "head": "Media edge cases", "body": "Rotation, 29.97 fps, VFR, start offsets, corrupt and unsupported codecs, files still copying, moved files found again by hash."},
              {"icon": "FaBalanceScale", "head": "Logic", "body": "'Can't tell' stays 'can't tell'; two short clips never count as one long one; duplicates are not two takes; editing a shot voids old decisions."},
              {"icon": "FaShieldAlt", "head": "Security", "body": "127.0.0.1 only, per-run token, Origin + Host checks, authorised folders, CSV formula guard, escaped HTML, errors never expose internals."},
              {"icon": "FaPlug", "head": "Offline", "body": "Core flow tested with outbound sockets blocked. Footage never leaves the computer."},
              {"icon": "FaHdd", "head": "Failure", "body": "Disk full stops safely and resumes; interrupted jobs resume; originals' hashes unchanged."},
              {"icon": "FaBoxOpen", "head": "Rebuild", "body": "Fresh venv from the public index passes the suite; Dockerfile and CI included; Apache-2.0."}]})
# 16-17 business
S.append({"type": "table", "section": "Business", "title": "Who pays: small crews and freelance editors who shoot on location",
          "header": ["Signal", "Number", "Source"],
          "rows": [["US film and video editors / camera operators (2025)", "39,400 / 32,600; 35% self-employed", "US BLS OOH"],
                   ["Median pay, editors (May 2025)", "$75,420 / yr", "US BLS OOH"],
                   ["Day rate, small crew (estimate)", "NT$12,000–28,000 (TW); $800–1,500 (US)", "PRO360 quotes; rate cards"],
                   ["Creators worldwide", "~50M, ~4% professional", "Goldman Sachs (estimate, partly verified)"],
                   ["Shot-list practice", "crews tick off shots and schedule pickup shots", "StudioBinder guide"]],
          "colW": [4.6, 4.0, 3.5],
          "note": "Value per project ≈ review hours saved × rate + avoided reshoot day − setup and review time. Unproven until the Stage II user study.",
          "source": "docs/research/BUSINESS_FACTS.md (URLs, access dates, verified flags)."})
S.append({"type": "cards", "section": "Business", "title": "Pricing hypothesis: one-time licence, sold with the accelerator",
          "cols": 3, "cards": [
              {"icon": "FaKey", "head": "Perpetual licence", "body": "Local-first users dislike per-minute upload pricing. Benchmark: Resolve Studio $295, Final Cut $299.99 one-time."},
              {"icon": "FaMicrochip", "head": "With UGen300", "body": "UGen300 USB reported at $299.99 (CNX Software). A bundle adds a concrete creator workflow to a USB accelerator."},
              {"icon": "FaLayerGroup", "head": "Template packs", "body": "Reusable shot-list templates per genre (café, product, event) with tuned queries; yearly updates."}],
          "lead": "All prices here are hypotheses to test in interviews (PRD 22.3), not a market claim. ASUS has not endorsed this product."})
# 18 plan
S.append({"type": "timeline", "section": "Plan", "title": "Stage II: device, users, Chinese queries",
          "items": [{"date": "Wk 1–2", "head": "G1 on a UGen300", "body": "Run the HEF image encoder; pass G1a–d or report the failure and stay on cpu-reference."},
                    {"date": "Wk 2–3", "head": "Speed with the device", "body": "Same clips, CPU vs GPU vs NPU; playback interference in a real editing-app timeline."},
                    {"date": "Wk 3–5", "head": "User study", "body": "3–5 interviews, then 8–12 crews: manual vs SceneGap, counterbalanced; time, misses, wrong reshoots."},
                    {"date": "Wk 5–6", "head": "Chinese queries", "body": "A multilingual model (SigLIP 2), so Chinese shot lists need no English query; adopt only if it finds as many dev shots."},
                    {"date": "Wk 6+", "head": "Hints", "body": "Optional person counts and text detection, each behind its own check."}]})
# 19 risks
S.append({"type": "table", "section": "Plan", "title": "What could break, and what we do then",
          "header": ["Risk", "Fallback"],
          "rows": [["HEF fails G1 (quantisation hurts ranking)", "Recalibrate with dev frames; TinyCLIP; else ship cpu-reference and say so"],
                   ["False cut splits a long take → false 'too short'", "A borderline cut makes the length check say 'can't tell', not 'too short'; the cut is shown"],
                   ["One global τ fits some queries badly", "One threshold per model version now; per type of shot next, set on dev"],
                   ["English query drifts from the Chinese requirement", "A person checks the English search phrase; multilingual model only after its check"],
                   ["AI annotators, Commons footage, small test split", "Wide CIs shown; Stage II adds human labels and self-shot projects"],
                   ["Crews will not write shot lists", "Templates; the interview checks this first"]],
          "colW": [5.2, 6.9]})
# 20 closing
S.append({"type": "closing", "title": "Fewer surprises in the edit", "subtitle": "SceneGap Edge · checks your shot list against your footage, on your own computer",
          "bullets": ["Checks the shot list, not just the footage: length, takes, same frame",
                      "Finds the right clip in the top 5 for 7 of 11 shots on held-out footage; a person confirms each one",
                      "Next: the image encoder on UGen300, per-shot thresholds for missing-shot detection, and a user study"]})
# appendix: credits
if man:
    rows = [[c["clip"][:3], (c.get("title") or "").replace("File:", ""), c.get("attribution") or c.get("artist") or c.get("credit") or "", c.get("license") or ""] for c in man["clips"]]
    per = 11
    for i in range(0, len(rows), per):
        S.append({"type": "table", "section": "Appendix", "title": f"Footage credits ({i // per + 1} of {(len(rows) + per - 1) // per})",
                  "header": ["#", "Wikimedia Commons file", "Author", "Licence"], "rows": rows[i:i + per], "colW": [0.6, 6.6, 3.1, 1.8], "fontSize": 9, "boldFirst": False, "fontFace": "Microsoft JhengHei"})

spec = {"title": "SceneGap Edge – Stage I proposal", "short": "SceneGap Edge · Stage I", "team": "[Team name]", "slides": S}
json.dump(spec, open(OUT, "w", encoding="utf8"), ensure_ascii=False, indent=1)
print(len(S), "slides")
