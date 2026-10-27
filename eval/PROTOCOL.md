# Evaluation protocol (first version written before any label or score existed; dated additions below)

Follows PRD ch. 21–24. Everything here was fixed before the threshold was chosen; the one addition made after
labelling (consistency pass, 19:17) is marked.

## Data
- Openly licensed real footage from Wikimedia Commons (CC0 / public domain / CC BY / CC BY-SA), listed with
  source URL, licence, author and SHA-256 in `datasets/manifests/commons_manifest.json`. Transcoded once to the
  first-version media path (MP4, H.264, 8-bit). Not self-shot: scenes vary more than a single café shoot would.
- Engineering fixtures (synthetic) are only used for the media and state tests in `tests/`.

## Split
- Clips are grouped by uploader/author (`artist`, else `credit`, else page title) so one shoot never sits on both
  sides. Groups are assigned to **dev** (about 40% of clips) or **test** (about 60%) by a hash of the group name,
  seed fixed in `eval/split.py`.
- The threshold and any tuning use **dev** only. **test** is scored once with frozen settings.
- Erratum (found after scoring): the grouping key is the raw author string, so "Max Duchardt, Katrin Engel" (022,
  dev) and "Max Duchardt , Katrin Engel" (025, test) became two groups. The split is kept as scored; Stage II
  normalises spaces and punctuation in the key.

## Labels (ground truth)
- Unit: for each clip and each requirement, the time intervals `[start_s, end_s)` where the requirement's visual
  content is clearly on screen, judged from 1-frame-per-second contact sheets with timestamps.
- Manual conditions (readable brand text, action actually completed, composition) are labelled separately as
  yes / no / cannot tell; they are not used to score the automatic retrieval.
- Two annotators label independently without seeing system output. Agreement is reported (interval IoU ≥ 0.5 or
  both empty). Disagreements are adjudicated by a third pass; the raw labels of both annotators are kept.
- Limitation stated up front: the annotators are separate AI sessions reading contact sheets, not people
  watching the footage; 1 fps sheets cannot resolve sub-second boundaries.

## Metrics on test (frozen)
- Recall@5: share of requirements with at least one gold interval in the test library whose top-5 candidates
  include one overlapping a gold interval (≥ 0.5 s overlap).
- Precision@5: share of returned candidates (up to 5) that overlap a gold interval.
- Project simulation: 8 mini-projects, each a seeded random subset of test clips. Per requirement, gold says
  "available" when a gold interval of the required continuous length exists in the subset.
  - gap recall = share of unavailable requirements the system reports as `not_found`.
  - wrong reshoot rate = share of available requirements the system reports as `not_found`.
  - unknown rate = share reported as `partial` or `unverifiable`.
  - false-ready rate: N/A, the system never auto-completes; human confirmation is required.
- Ablation (PRD 24.4): filename/title keyword match → single-frame semantic retrieval (no duration rule) → full
  system (semantic + continuous duration + densify).
- Wilson 95% intervals for every proportion.

## Performance (PRD 24, NFR-04/05)
- Per clip: decode + sampling time, embedding time, samples, on the desktop CPU and on the desktop GPU, labelled
  `cpu-reference` / `cuda-reference`. No UGen300 numbers exist; they are `not_run`.
- Search: p50/p95 latency for a text query over 10,000 indexed segments (text encode + similarity + ranking).
- New clip to first result (60 s clip).

## Threshold calibration (added 2026-10-26, still before any label exists)
- One global τ per model fingerprint (`semantic_threshold: {fingerprint: τ}`), chosen on **dev** only.
- Objective: sample-level F1 over every (dev sample, requirement) pair, where a sample is positive when its time
  falls inside a gold interval of that requirement. Grid 0.150–0.400, step 0.005; ties go to the higher τ.
- Prompts: `query_en` is written once per requirement before labelling ("a photo of …" style) and not edited after
  dev scores are seen. Any prompt change after that would need a new dev pass and is reported.
- Top-K stays 5, sampling 1 s, densify 250 ms, cut threshold 0.45: the shipped defaults, not tuned.
- Matching a candidate to gold: the candidate's interval is its conservative lower-bound interval, widened to at
  least one sampling period (1 s) around its start, because a single passing sample has a lower bound of ~0 ms.
  A match needs ≥ 0.5 s overlap with a gold interval of the same requirement in the same clip.
- Crop policy (added the same day, before labels): CLIP's default centre crop drops about 44% of a 16:9 frame's
  width. Both `center-crop` and `pad-square` (letterbox) are calibrated on dev; the one with the higher dev F1 is
  frozen (ties keep `center-crop`). The choice is part of `preprocess_id` and therefore of the model fingerprint.
- Review-load proxy (added before scoring): seconds of footage in the test library versus seconds a person would
  play to check every returned candidate once (each at its lower-bound length, at least 1 s, at most 10 s). This is
  not a user-time measurement; the user study of PRD 22 is not done.

## Label consistency pass (added 2026-10-26 19:17, after labelling, before any calibration or test score was computed)
- The third pass resolved disputed frames with written rules for wording the guide left open (R1–R8 in
  `eval/labels/adjudication_rules.json`: e.g. SH-11 "barista/worker" means a person in a commercial or service
  setting, SH-09 needs a group head/portafilter, SH-04 needs grounds visibly coming out).
- Some frames both annotators agreed on break those same rules. So that one rule holds across the gold, the same
  adjudicator re-checked every agreed-positive frame of SH-03, SH-04, SH-09 and SH-11 under its rules, blind to who
  labelled what. Frames that clearly fail a rule are removed; all removals are listed in
  `eval/labels/consistency.json` and counted in `agreement.json`. Raw labels of both annotators stay unchanged in
  `eval/labels/raw/`. No calibration or test result existed when this was decided.
- Result of the consistency pass: 78 of 238 agreed positives removed (65 of them SH-11 home or studio prep under
  rule R3). Because this applies a stricter reading than the annotators were given, both are reported:
  **primary gold** = agreed + third pass + consistency pass (`gold.json`), used for dev calibration and test;
  **sensitivity gold** = agreed + third pass only (`gold_lenient.json`), scored in the same single test run.

## Stage 1.5: missing-shot verifier and test-2 (added 2026-10-27 00:14, before any test-2 label or score)

Why: on test, missing-shot detection caught 0 of 38 (the CLIP threshold lets almost every shot find something).
The first test split has been scored and its missing shots are known to us, so it cannot judge a new method.

Method (frozen now, chosen on dev only by `eval/verify_eval.py dev`):
- The full system runs unchanged. For each shot, its top K = 3 candidates go to a verifier,
  Qwen2-VL-2B-Instruct (fingerprint `50c2f0ae4c535c51`), which answers "Does this image show <query>?
  Answer yes or no." for the 3 best-matching frames of each candidate; P(yes) is read from the
  next-token logits and a candidate's score is the maximum over its frames.
- A shot is reported `not_found` when no top-K candidate reaches θ = 0.35; otherwise the system's status stays.
- The question is built from the person-confirmed English query; no per-shot prompt tuning.
- Dev (20 projects × 8 clips): system alone 5/89 missing shots
  caught, 0/131 wrong reshoots; with the verifier
  37/89 caught, 6/131 wrong reshoots.
  Selection rule: most missing shots caught with wrong reshoots ≤ 5% on dev; ties → higher θ, then smaller K.

Test-2 (new held-out footage):
- 24 Wikimedia Commons videos not in the first dataset, chosen by `scripts/search_commons.py` from metadata only
  (search rank over 12 coffee/café terms, licence, 5–120 s, ≤ 80 MB), never from frames.
- Labels: the same 11 shots and `eval/LABEL_GUIDE.md` rules (including the third-pass rules R1–R8 and the brand
  rule), two independent AI annotator passes on 1 fps contact sheets, a third pass on every disagreement.
  Labels are made without access to any system or verifier output. Stored in `eval/labels/test2/`.
- Scoring: 12 simulated projects × 8 clips (seeds `test2-0` … `test2-11`), run once by
  `eval/verify_eval.py test2`, which refuses a second run. Same metrics as the first test (missing shots caught,
  wrong reshoot, couldn't decide, 'found' when absent), plus Hit@5 on the whole test-2 library as ranked by the
  system and as re-ranked by the verifier.
- Success criteria, fixed now: wrong reshoot ≤ 5% (PRD 21.5, point estimate) **and** missing shots caught ≥ 30%
  (at least five times the system alone on dev). Both are reported whatever the outcome.

## Stage 1.6: the verifier decides, and test-3 (added 2026-10-27 05:48, before any test-3 label or score)

Why: test-2 met the missing-shot target (32/91) but not the wrong-reshoot cap (3/41 = 7.3%). Diagnosis on dev and
test-2: wrong reshoots happen when the right clip is not among the top 3 candidates, or is ranked 4th–5th; missed
gaps happen when the Stage 1.5 question accepts a clip the shot definition excludes (a home espresso routine as
"barista", a capsule machine as "espresso machine"). Test-1 and test-2 have both been scored and their errors seen,
so from here on they are development data; only new footage can judge Stage 1.6.

Method family (`eval/verify16.py`, chosen on dev + test-1 + test-2 only):
- The verifier (Qwen2-VL-2B-Instruct, same fingerprint) scores every 1 s sample with P(yes) (`eval/verify_dense.py`).
- Check questions per shot (`eval/verify_questions.json`, written 05:41 from `eval/LABEL_GUIDE.md` and rules
  R1–R8, before any test-3 footage existed). SH-08 and SH-11 add one extra condition (inside a café; a commercial
  setting); a frame's score is then the minimum. In the product these are drafted from the shot text and confirmed
  by the person, like `query_en`.
- Grid: question set {Stage 1.5 question, check question, check question + conditions} × frames looked at {all,
  CLIP top 8, 16, 32 samples of the project} × run length {1, 2, the shot's own minimum seconds} × θ 0.05…0.95.
  A shot is present when one clip and one detected shot holds a run of looked-at samples with P(yes) ≥ θ of that
  length; otherwise `not_found`.
- Selection rule, fixed now: pooled wrong reshoot ≤ 3% **and** ≤ 5% in each of dev, test-1 and test-2; among those,
  most missing shots caught; ties → fewer verifier calls, then higher θ. If nothing qualifies, test-3 is not scored.

Test-3 (new held-out footage):
- 40 Wikimedia Commons videos in none of the earlier sets, chosen by `scripts/search_commons.py` from metadata
  only with 12 new search terms (coffee machine, cappuccino, coffee preparation, coffee making, kaffee, koffie,
  cafetería, moka pot, coffeehouse, coffee bar, espresso machine, café), round robin in Commons' relevance order;
  manifest `datasets/manifests/test3_manifest.json`. Many are not about coffee; they make real missing shots.
- Labels: same guide and rules R1–R8, two independent AI annotator passes on 1 fps contact sheets, a blind third
  pass on every disagreement, no access to any system or verifier output; stored in `eval/labels/test3/` and
  committed before scoring.
- Scoring: 20 simulated projects × 8 clips (seeds `test3-0` … `test3-19`), run once by `eval/verify16.py test3`,
  which refuses a second run.
- Success criteria (unchanged from Stage 1.5): wrong reshoot ≤ 5% **and** missing shots caught ≥ 30%. Reported
  whatever the outcome. If they are missed, the next change is again chosen on all scored data and judged on a
  new test set; test-3 is never re-scored.

### Stage 1.6 results (test-3 scored once, 2026-10-27 07:38)
- Frozen on earlier data (`eval/results/verify16_dev.json`): check question + conditions, every 1 s sample, run of 2,
  θ 0.5. Earlier data pooled: 80/218 missing shots caught, 6/222 wrong reshoots.
- Test-3 (`eval/results/test3_metrics.json`, 20 projects × 8 of 39 clips): missing shots caught **76/152 (50%)**,
  target met; wrong reshoot **8/68 (11.8%, 95% CI 6.1–21.5%)**, target **not met**. The 8 are borderline frames
  (P(yes) 0.3–0.6): café interiors in an old black-and-white film and a cat café (SH-02 ×5), a K-cup pod as a
  coffee package (SH-10 ×2), a mug on a drip tray (SH-06 ×1).
- Leave-one-set-out over the four scored sets (`eval/results/verify_loso.json` via `eval/verify16.py loso`; selection on
  three, report on the fourth, same rule): held-out pooled 110/370 caught, 12/290 wrong reshoots (4.1%), but the
  test-3 fold alone is 8/68. The choice does not transfer reliably from set to set.
- Post hoc, defined after test-3 was scored (`eval/verify16_evidence.py`): each missing-shot alert now shows the 3
  frames the verifier found most likely, one per clip. In 12 of the 14 wrong reshoots over all four sets one of
  those frames is a gold frame; on test-3, 2/68 (2.9%) would survive a person's look at the 3 frames. This assumes the
  person recognises the shot and needs a prospective test on new footage.
- Next: Wikimedia Commons has no further coffee footage (a search with 12 more terms returned mostly unrelated
  clips), so a test-4 needs footage from elsewhere (a real shoot, or another openly licensed source used within its
  terms). Test-3 is not re-scored.

## Stage 1.7: test-4 on a real café shoot, and the 3-frame look as a metric (added 2026-10-27 11:18, before any test-4 footage exists)

Why: Stage 1.6 met the missing-shot target on test-3 but not the wrong-reshoot cap; the 3-frame look was defined
after test-3 was scored, so it needs a prospective test.

- System: Stage 1.6 exactly as frozen (`--verifier`: check question + conditions, every 1 s sample, run of 2, θ 0.5,
  same verifier fingerprint and `eval/verify_questions.json`). Nothing is tuned on test-4.
- Footage: a team member shoots about 45 clips in a café from the shot list `docs/TEST4_SHOOTING_zh.md` (written now):
  each of the 11 shots × 3 varied clips, 6 near-misses that the shot definitions exclude, 6 unrelated clips. Every
  clip received is used, except one the transcoder cannot read (reason recorded). Original files are hashed and
  renamed in shuffled order before labelling; manifest `datasets/manifests/test4_manifest.json`.
- Labels: same guide and rules R1–R8, two independent AI annotator passes on 1 fps contact sheets, a blind third pass
  on every disagreement, no access to the shot list's intent, filenames, or any system or verifier output; stored in
  `eval/labels/test4/` and committed before scoring.
- Scoring: 30 simulated projects × 8 clips (seeds `test4-0` … `test4-29`), run once; the scorer refuses a second run.
- Primary criteria (unchanged): wrong reshoot ≤ 5% **and** missing shots caught ≥ 30%.
- Secondary criterion (Stage 1.7): wrong reshoot after the 3-frame look ≤ 5%. A wrong reshoot is cleared when at
  least one of its 3 evidence frames (the verifier's most likely sample per clip, top 3 clips, as shown on the
  reshoot card) lies inside a gold segment of that shot, ±0.5 s. This assumes the person judges the frame as the gold
  labels do; under the same assumption a correct alert is never cleared, so missing shots caught is unchanged.
- All three numbers are reported with Wilson 95% CIs whatever the outcome. Test-4 is never re-scored.
