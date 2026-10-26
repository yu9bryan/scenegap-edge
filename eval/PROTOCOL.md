# Evaluation protocol (written before any label or score exists)

Follows PRD ch. 21–24. Everything here is fixed before labels are produced and before the threshold is chosen.

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
  - gap recall = share of unavailable requirements the system reports as `not_found` (or with a reshoot card).
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

## Label consistency pass (added 2026-10-26 19:2x, after labelling, before any model output was looked at)
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
