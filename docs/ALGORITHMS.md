# SceneGap Edge: algorithms

Status: describes the code as of 2026-10-26 (`CODE_VERSION = "0.1.0"`). Every statement in Parts 1–3 is
taken from the code; file and line references are given so they can be re-checked. Part 4 lists planned
extensions, each with the test that must pass before it ships. Part 5 lists problems found while reading the
code.

All times are integer milliseconds on the original media timeline (PTS × time_base × 1000). Intervals are
half-open `[start_ms, end_ms)` (`domain/models.py` `Interval`).

---

## 1. Pipeline overview

```
import ─► probe ─► analyze_assets (per asset, cached)            compute_run (per project, on demand)
           │        │                                              │
           │        ├─ one full decode: PTS + HSV histogram         ├─ encode the confirmed English queries
           │        ├─ cut detection → shots                        ├─ cosine sims = frame emb · text emb
           │        ├─ 1 fps samples + shot-middle frames           ├─ candidate runs per requirement
           │        ├─ quality flags per sample                     ├─ conservative duration bounds
           │        └─ image embeddings → .npz index                ├─ densify UNKNOWN-duration shots, recompute
           │                                                        ├─ status per requirement (3-valued logic)
           │                                                        ├─ coverage (3 separate ratios)
           │                                                        └─ snapshot row in `runs`
           └─ sha256 = asset identity; capture_id = take identity
```

Where it runs today: everything on the host. Embeddings come from `ClipReference`
(`backends/cpu_clip.py`, OpenAI CLIP ViT-B/32 through Transformers, fp32, CPU or CUDA). The provenance label
is `cpu-reference` or `cuda-reference`. `HailoClip` (`backends/hailo.py`) always raises
`DeviceUnavailable`; no NPU output exists.

---

## 2. Analysis (per asset)

### 2.1 Decode and sampling (`shots/analyze.py` `analyze`)

1. One decode pass over every video frame (PyAV, `thread_type="AUTO"`). Frames with `pts is None` are skipped.
   `t_ms = int(pts × time_base × 1000)`. The stream start offset is not subtracted, so `t_ms` is the raw PTS
   time. The review API allows for this by adding `probe.start_ms` when it checks an interval.
2. Every decoded frame is converted to a 160×90 RGB array and reduced to an HSV histogram (16×8×8 bins,
   normalised).
3. **Coarse samples:** the first frame is kept, then the first frame with `t ≥ next_t`, where `next_t`
   advances in steps of `sample_every_ms` (default 1000 ms) from the first kept time. The kept frame is
   scaled so its short side is about 336 px (even dimensions) and rotated upright with
   `PIL.Image.rotate(probe.rotation, expand=True)`. Integration test TC-014 checks the 90° case.
4. Decode stats are written into the index metadata: frames decoded, samples, shots, end_ms.

### 2.2 Cut detection

- Histograms are ordered by `t_ms`. A cut is declared at frame *i* when the Bhattacharyya distance between
  the histograms of frames *i−1* and *i* is greater than `CUT_THRESHOLD = 0.45`, **and** at least
  `MIN_SHOT_MS = 400` ms have passed since the previous cut.
- Shots are `[cut_k, cut_{k+1})`. The last shot ends at `end_ms = last PTS + last frame interval` (33 ms if
  there is only one frame).
- This only compares adjacent frames, so it detects hard cuts. Dissolves, fades and whip pans are not
  modelled. The threshold is an uncalibrated starting value (module docstring).

### 2.3 Shot assignment and shot-middle frames

- Each coarse sample gets `shot_index = max k such that shot_k.start ≤ t_ms`.
- A shot that contains no coarse sample (shorter than about 1 s) gets one extra frame: the first decoded
  frame at or after the shot midpoint (`frames_at`, a second decode pass from the start of the file). Every
  shot therefore has at least one sample.

### 2.4 Quality flags (`quality_flags`)

Each sample is converted to grey and resized to 224 px wide.
- `blur = Var(Laplacian) < 60.0`
- `exposure_clipped = share of pixels < 6 or > 249 is greater than 0.40`

Both thresholds are uncalibrated starting points. `None` means "not computed" and is kept apart from
`False`.

### 2.5 Embedding and index (`service.py` `analyze_assets`, `_save_index`)

- All samples of an asset are encoded in batches of 32 with `CLIPProcessor` defaults, which means: resize
  the short side to 224, **center-crop 224×224**, CLIP mean/std. The output is L2-normalised.
- The index is `cache/<model fingerprint>/<sha256>_<sample_every_ms>.npz`. It holds t_ms, pts, shot index,
  blur/clipped (−1 = None), the shots array, embeddings as **float16**, and metadata (fingerprint, backend
  label, decode stats, densified count). It is written atomically.
- An index whose stored fingerprint differs from the active backend's is treated as missing, and the asset
  is analysed again (TC-030: model versions are never mixed). Assets with a valid index are not re-encoded
  (TC-028).
- A failure in one asset marks only that asset `failed` / `DECODE_FAILED` (FR-ING-06).

---

## 3. Run computation (per project, `service.py` `compute_run`)

### 3.1 Preconditions

- `semantic_threshold` (τ) must be set. If it is `None`, the run is refused with `UNCALIBRATED`. τ is chosen
  on the dev split and frozen before the test split is scored (`eval/PROTOCOL.md`).
- Queries are the union of every requirement's `query_en`, plus `co_occur.params.queries` and
  `semantic.params.query`. `query_en` is the English text a person confirmed; it is mandatory when a
  requirement is saved (`set_requirement`).
- Text is encoded raw (no prompt template) with the **same** backend object. Stored image fingerprints are
  compared with the text encoder's fingerprint (`check_pair`, TC-016).
- `sim[frame, query] = emb_frame · emb_text` (cosine, because both are unit vectors; frames were stored as
  float16).

### 3.2 Candidate runs (`domain/coverage.py` `_runs`, `candidates_for`)

1. **Query set for retrieval** (`_semantic_queries`): if the requirement has a `co_occur` constraint, its
   query list is used. Otherwise a `semantic` constraint's query is used. Otherwise `query_en`.
2. **Passing sample:** `all(sim[s, q] ≥ τ for q in queries)`. One global τ applies to every query.
   **Co-occurrence** therefore means every query passes *in the same sampled frame*, not just somewhere in
   the shot.
3. **Run:** a maximal sequence of consecutive samples (in time order) that all pass and share one
   `shot_index`. A run never crosses a cut, and one failing sample ends it (there is no hysteresis).
4. **ranking_score** = mean over the run of `min_q sim[s, q]`. It is a ranking value, not a probability.

### 3.3 Conservative duration bounds (`_bounds`)

Let the run cover samples `first..last` in shot *k*.

- **Lower bound (seen):** `lo = t[last] − t[first]`, the span between the first and the last passing
  sample. A single-sample run has `lo = 0`.
- **Upper bound (not excluded):** from the previous sample (`t[first−1]`) if it is in the same shot,
  otherwise the shot start, to the next sample (`t[last+1]`) if it is in the same shot, otherwise the shot
  end. The result is clamped to the shot. Because runs are maximal, the neighbouring samples in the same shot
  are known to fail, so the content cannot have lasted longer than `up = up_e − up_s`.
- The candidate's displayed interval is the lower-bound interval `[t[first], max(t[last], t[first]+1))`.

**Duration verdict** (`check_constraint`, `need = params.min_ms` or `req.min_duration_ms`):

| condition | verdict | meaning |
|---|---|---|
| `lo ≥ need` | PASS | seen continuously for at least `need` |
| `up < need` | FAIL | cannot have lasted `need`, even between samples |
| otherwise | UNKNOWN | densify or check by playback |

These bounds are conservative **only if the shot boundaries are right** (see risk C1).

If `min_duration_ms > 0` and the requirement has no explicit `duration` constraint, an AUTO duration
constraint is added.

### 3.4 Other constraint checks (`check_constraint`)

| kind | capability AUTO | MANUAL / UNSUPPORTED |
|---|---|---|
| `semantic`, `co_occur` | PASS ("semantic candidate"; the run exists) | UNKNOWN |
| `duration` | table above | UNKNOWN |
| `quality` | UNKNOWN if any run sample has `blur=None`; otherwise PASS if the blurred share is at most `max_blur_fraction` (default 0.5), else FAIL. `exposure_clipped` is **not** used. | UNKNOWN |
| `takes` | skipped per candidate; counted at requirement level | — |
| `readable_text`, `action`, `composition`, `forbidden`, anything else | UNKNOWN ("unknown condition type") | UNKNOWN ("needs manual check" / "not supported in this version") |

The candidate's `overall` is the three-valued AND (`domain/logic.py`) over the **hard** constraints:
any FAIL gives FAIL; all PASS gives PASS; anything else, including an empty list, gives UNKNOWN. UNKNOWN is
never treated as PASS. Soft constraints are reported but do not affect `overall`. As a result, a
requirement with any **hard** MANUAL constraint (action, readable text, composition) can never get
`overall = PASS`, so it never becomes `candidate` and never counts towards `ai_candidate` coverage. It stays
`partial` [`NEEDS_MANUAL`] until a person accepts a segment. This is intended (ADR-004), but the UI has to
explain it. `NOT` exists in
`logic.py` and returns UNKNOWN unless the negative-evidence scope is complete. No constraint uses it yet.

### 3.5 Ranking and de-duplication

Candidates are sorted by `overall` (PASS, then UNKNOWN, then FAIL) and then by descending `ranking_score`.
At most `per_shot = 1` candidate is kept per (asset, shot), and the top `top_k = 5` are returned.

### 3.6 Densify loop (`service.py` `_densify`, FR-SEG-03)

For each confirmed requirement, and for each of its top-k candidates whose duration verdict is UNKNOWN:

1. Targets are every `densify_step_ms = 250` ms from the **start to the end of the candidate's whole shot**,
   skipping any target within 125 ms of an existing sample. (This is the whole shot, not only the
   uncertainty gaps around the run; see risk C2.)
2. `frames_at` decodes from the file start and returns the first frame at or after each target. Quality
   flags are computed, the frames are encoded, merged into the index in time order, and saved. The
   metadata's `densified` count increases.
3. After a pass over all requirements, indexes and sims are reloaded and candidates are recomputed. At most
   two passes run (`for _ in range(2)`). In practice the second pass finds no new targets in shots that were
   already densified.

With samples 250 ms apart, the gap between the lower and upper bound shrinks to at most about 500 ms. Most
UNKNOWN durations then resolve to PASS or FAIL. Any that remain stay UNKNOWN, and the reason says to check by
playback.

### 3.7 Takes

`distinct_takes(cands) = |{capture_id}|` over the candidates passed in. When an asset is imported,
`capture_id = sha256[:12]`, so every distinct file counts as its own take until a person groups copies with
`set_capture`. Byte-identical copies are a single asset already (same sha256, another location).

### 3.8 Requirement status (PRD 13.3; `requirement_status`)

Scope: `in_scope` = assets not `excluded`. `complete` = no in-scope asset is pending, analyzing, failed or
missing, and at least one is analysed. Rules are applied in this order; the first match wins.

1. Requirement not confirmed → `draft` [`NOT_CONFIRMED`]
2. No in-scope asset → `not_analyzed` [`NO_ASSETS`]
3. No analysed asset → `analyzing` if any asset is analyzing, `not_analyzed` if some are pending
   [`NOT_ANALYZED`], otherwise `failed` [`ANALYSIS_FAILED`]
4. Some candidates have `overall = PASS` **and** their distinct takes ≥ `max(1, min_takes)` → `candidate`
   (+ `SCOPE_INCOMPLETE` if the scope is not complete). This means "candidate, a person must confirm", not
   "done".
5. Any candidates (PASS with too few takes, UNKNOWN or FAIL) → `partial`, with reasons from every non-PASS
   constraint result: FAIL duration → `DURATION_SHORT`, FAIL quality → `QUALITY_WARNING`, other FAIL →
   `CONSTRAINT_FAILED`, UNKNOWN duration → `DURATION_UNKNOWN`, UNKNOWN on a MANUAL constraint →
   `NEEDS_MANUAL`, other UNKNOWN → `EVIDENCE_UNKNOWN`. Also `TAKES_SHORT` and `SCOPE_INCOMPLETE` where they
   apply.
6. No candidate and scope incomplete → `unverifiable` [`NO_CANDIDATE`, `SCOPE_INCOMPLETE`]
7. No candidate, scope complete, and a `semantic`/`co_occur` constraint is UNSUPPORTED → `unverifiable`
   [`UNSUPPORTED_CORE`]
8. Otherwise → `not_found` [`NO_CANDIDATE`]. This means no frame in the analysed scope reached τ. It does
   **not** mean the shot is absent.

Human decisions are stored separately and never change the automatic status.

### 3.9 Human confirmation (`human_confirmed`)

A requirement counts as human-confirmed when there are decisions with: the same requirement id, the
**current** revision, an asset sha256 that is still in scope, and a decision of `accepted` or `overridden`
(overridden needs a non-empty reason). These decisions must cover at least `max(1, min_takes)` distinct
**asset sha256** values. `by_exception` is true if any of them is an override. Note that this counts takes by
sha256, while the automatic path counts them by capture_id (risk C6).

### 3.10 Coverage (PRD 8.4; `coverage`, `coverage_view`)

Denominator `D` = sum of `weight` over **active required** requirements: `confirmed ∧ required ∧ not
excluded`. Drafts, optional requirements and excluded requirements do not count.

| ratio | numerator | when outdated |
|---|---|---|
| `human_confirmed` | weight of requirements with `human_confirmed` true | always recomputed live from decisions |
| `ai_candidate` | weight of requirements whose auto status is `candidate` | set to `None` when the snapshot is outdated |
| `analysis_progress` | total duration of analysed assets ÷ total duration of all non-excluded assets (failed and missing count in the denominator) | from the snapshot |

`D = 0` gives `None` (N/A), never 0 % or 100 %. `unknown_count` = number of active required requirements in
`unverifiable`, `partial`, `not_analyzed` or `failed`.

A snapshot (`runs` row) records the backend label, model fingerprint, config hash, requirement revisions,
asset scope and code version. `coverage_view` marks it **outdated** when the revisions, the scope or the
model fingerprint differ from the current ones. Outcomes for a revision that has changed are hidden
(`auto_outdated`).

### 3.11 Reshoot / review cards (PRD ch. 14; `domain/reshoot.py`, `service.reshoot_cards`)

- A card is made for each active required requirement that is **not** human-confirmed and whose current
  outcome is not `draft` and not `candidate`. Candidates are reviewed in the evidence viewer, not reshot. A
  stale outcome (revision changed) gets no card until it is re-analysed.
- `not_found` → `reshoot_proposed`. Every other status (`partial`, `unverifiable`, `not_analyzed`,
  `analyzing`, `failed`) → `review_first`. Review-first cards are listed first (FR-RET-02).
- Card fields come only from the confirmed requirement and the recorded evidence: source text, reasons (code
  and Chinese text), best candidate (asset, interval, non-pass condition reasons), minimum continuous
  seconds, handles (`handles_ms`), composition notes, props, and how to verify. The verify text is "re-import,
  automatic semantic and duration check, then playback by a person", plus the list of manual constraint
  kinds. No text is generated.
- Card workflow status is `proposed → confirmed → shooting → done | dismissed`, keyed by (requirement,
  revision). Only a person changes it.

---

## 4. Planned extensions and how each is verified

None of these exist in the code yet. Each stays `manual` or `unknown` until its gate passes on the **dev**
split. Every threshold is then frozen and the **test** split is scored once. Model details are in
`MODEL_PLAN.md`.

| # | Extension | Algorithm | Verification (gate) |
|---|---|---|---|
| E1 | Hailo image encoder (route A) | `clip_vit_b_32_image_encoder` HEF on the UGen300. Text stays on host CPU with the same HF weights. Preprocessing is identical to the reference (same resize/crop on host, uint8 into the HEF). A new fingerprint and a new τ are used. | **G1** (MODEL_PLAN §4): per-frame cosine to fp32, per-query Spearman ρ, top-K overlap, task Recall@5 within tolerance. Only a real device run counts. |
| E2 | Crop policy | Compare center-crop with letterbox and with 3-crop (left/center/right, max-pooled sim) on dev. | dev Recall@5 and Precision@5 per policy. Pick one and freeze it. Record it in `preprocess_id`. |
| E3 | Prompt templates | Average the embeddings of K templates ("a photo of {q}", "a video frame of {q}", …). | dev Recall@5. The template set is part of the fingerprint. |
| E4 | Restricted densify | Densify only `[up_s, t[first])` and `(t[last], up_e]` at 250 ms, and use seek instead of decoding from frame 0. | Unit test: same verdicts as whole-shot densify on fixtures. Count of frames encoded drops. |
| E5 | Object co-occurrence | YOLO (COCO) per sample. `count(person, conf ≥ c) ≥ 2` and `cup` present in the **same frame**, for ≥ m consecutive samples. Detector evidence AND CLIP run. | Per-constraint precision/recall on dev frames that carry object labels. Negative verdicts only through `NOT(…, negative_scope_complete)`. |
| E6 | Composition | From detector boxes on the **uncropped** frame: normalised box centre x → left / centre / right thirds, or relative order of two boxes. Rotation is applied before detection. | Labelled composition yes/no on dev: precision ≥ gate. Until then the result is shown as a hint, and the verdict stays UNKNOWN. |
| E7 | Readable text (OCR) | PP-OCRv5 detection, then recognition, on the frames of the candidate run. PASS needs the normalised target string within edit distance k and confidence ≥ c in ≥ 2 samples. | Traditional Chinese test set built from the **target script's** brand strings. CER, exact-match, and false-readable rate. Automatic only after it passes. |
| E8 | Action aid | Multi-frame state sequence (e.g. "hand holding kettle over cup" then "liquid in cup") over 250 ms samples with temporal order. The result is a **retrieval aid only**, never PASS. | Precision@5 of action windows on dev. The constraint verdict stays UNKNOWN / MANUAL (ADR-004). |
| E9 | Low-score review before reshoot | For `not_found`, attach the top-N below-τ frames to the card for a quick look. | Wrong-reshoot rate on the project simulation (PROTOCOL). |
| E10 | Gradual-transition cuts | Add a windowed histogram difference (and optionally a learned detector) and evaluate on labelled cuts. | Cut precision/recall within ±2 frames on dev clips. Measure how false cuts change duration FAIL verdicts. |

---

## 5. Problems found in the current code

Severity: **H** can produce a wrong PASS/FAIL or a wrong reshoot; **M** affects reproducibility, cost or
honesty of reporting; **L** is minor or cosmetic.

| id | sev | where | finding | suggested fix |
|---|---|---|---|---|
| C1 | H | `shots/analyze.py:88`, `domain/coverage.py:77-79,93` | The duration bounds trust the shot boundaries. A **false cut** (flash, fast pan, lighting change) caps the upper bound at the false edge, so a continuous take can get a **false FAIL** (`DURATION_SHORT`, and possibly a reshoot card). A **missed cut** lets a run span two shots that both match, so the lower bound can give a **false PASS**. | Evaluate the cut detector (E10). When a run ends at a cut whose histogram distance is close to the threshold, return UNKNOWN instead of FAIL. Show the cut in the evidence viewer. |
| C2 | M | `service.py:293`, `analyze.py:107-130` | Densify samples the **whole shot**, not the uncertainty gaps, and `frames_at` decodes from the file start every time. A 10-minute single take with an UNKNOWN candidate adds about 2,400 frames to encode and a full decode. | E4: restrict to `[up_s, t_first)` ∪ `(t_last, up_e]`, seek to keyframes, and cap targets per run. |
| C3 | M | `service.py:315`, `service.py:84` | Densified frames persist in the index, but `config_hash` and the run record do not capture densification state. The same config can give different samples, scores and verdicts depending on which queries were run earlier. | Record `densified` and the sample count per asset in the run snapshot, or keep densified samples in a per-run overlay. |
| C4 | M | `service.py:383` | `coverage_view` checks revisions, scope and fingerprint, but **not** `config_hash`. Changing τ or `sample_every_ms` leaves an old snapshot looking current. | Add `run.config_hash != self.config_hash()` to `outdated`. |
| C5 | H | `service.py:31`, `coverage.py:60` | A single global τ is used for every query and every backend. CLIP cosine scales differ between queries, and after INT8 quantization they differ between backends. A τ calibrated on fp32 must not be reused on Hailo. | Key τ by model fingerprint (and preferably by query family). Re-calibrate on dev for every new fingerprint. |
| C6 | H | `coverage.py:138` vs `coverage.py:187`, `service.py:182` | Take identity is inconsistent. The automatic path counts `capture_id`, which defaults to a **sha256 prefix**, so a proxy or re-encode of the same take counts as a second take. The human path counts `asset_sha256`. Both can overstate `min_takes`. | Use capture_id in both places. Mark ungrouped assets as "take identity unconfirmed" and report `TAKES_UNCONFIRMED` instead of counting them as independent. |
| C7 | H | `coverage.py:184-189` | `human_confirmed` ignores later decisions. If an interval is accepted and later rejected, the accept still counts, so the requirement stays human-confirmed and no card is generated. | Reduce decisions to the latest per (requirement, revision, asset, interval) before counting. |
| C8 | H | `backends/cpu_clip.py:41` (CLIPProcessor defaults) | Center-crop to 224×224 discards about **44 %** of the width of a 16:9 frame (224/398 of the resized width is kept). Subjects at the frame edges, two people standing apart, and left/right composition are cut out of the embedding. The Hailo path must use exactly the same crop or G1 compares different inputs. | E2: evaluate letterbox and 3-crop on dev. Put the chosen policy in `preprocess_id`, which feeds the fingerprint. |
| C9 | M | `backends/base.py:31`, `cpu_clip.py:28` | The fingerprint leaves out `artifact_sha256`, `target_arch` and runtime. `version` can be `"unknown"`. Two HEF builds with different calibration sets (same `quantization` label) would share a fingerprint and reuse each other's cached index and τ. | Include `artifact_sha256` (HEF or weights hash) and the text-side preprocessing (template, lowercasing) in the fingerprint. Refuse `version="unknown"`. |
| C10 | M | `cpu_clip.py:43,52` | `getattr(f, "pooler_output", f)` handles Transformers versions where `get_*_features` returns an output object. No check confirms that the result is the **projected** 512-d vector. | Assert `emb.shape[1] == manifest.embedding_dimension` after encoding and pin the Transformers version. |
| C11 | M | `domain/reshoot.py:47` | `not_found` goes straight to `reshoot_proposed`, but `not_found` only means nothing in scope reached τ. A CLIP miss can trigger an unnecessary reshoot. | E9: put the below-τ top-N on the card, and measure the wrong-reshoot rate before a card can say "reshoot". |
| C12 | L | `coverage.py:96-101` | The quality check uses only `blur`. `exposure_clipped` is computed but never affects a verdict. Both thresholds are uncalibrated. | Add exposure as a separate soft constraint after calibrating on dev. |
| C13 | L | `coverage.py:211-212` | `unknown_count` leaves out `analyzing`, while `not_analyzed` is included. | Include `analyzing`, or document why it is left out. |
| C14 | L | `service.py:300-301`, `analyze.py:120-125` | `frames_at` returns the first frame **at or after** a target. For the last target of a shot this frame can lie after the cut, yet it is labelled with the current shot. For low-fps or VFR media, one frame can be returned for several targets (duplicate `t_ms`). | Drop frames with `t ≥ shot.end` and de-duplicate by `t_ms`. |
| C15 | L | `backends/hailo.py:27` | `device_status` reports a generic "Hailo device" from `Device.scan()` without checking that the device is a Hailo-10H. A Hailo-8 would also report available. | Read the device architecture (e.g. `hailortcli fw-control identify`) and require HAILO10H before labelling a run `hailo`/UGen300. |
| C16 | L | `media/probe.py:28` vs `shots/analyze.py:47` | The probe field comment says "degrees clockwise". The analyze comment says the value is PyAV `frame.rotation` (counter-clockwise) passed to PIL's counter-clockwise rotate. TC-014 only asserts `rotation == 90`. | Add a 270° fixture and an assertion on the resulting image orientation. Fix the comment. |
| C17 | L | `coverage.py:46-53` | When a `co_occur` constraint exists, `query_en` is not used for retrieval (only the co-occur queries are). This may be intended, but it is undocumented. | Document it, or AND `query_en` in. |
