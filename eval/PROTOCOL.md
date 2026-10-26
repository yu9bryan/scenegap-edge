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
