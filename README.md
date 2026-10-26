# SceneGap Edge

**Know which must-have shots you already have, and which to reshoot, before the crew leaves the location.**

SceneGap Edge is a local-first shot-coverage assistant for small video crews and freelance editors. You write the
shot list ("3 s of latte being poured", "two takes of the barista", "readable brand on the bag"). SceneGap indexes
the footage on your own computer, finds candidate segments with original timecodes, checks duration, same-frame
co-occurrence and takes, and tells you, per requirement, what it found and what it could not decide. A person
confirms every result. Missing shots turn into reshoot cards.

Built for the ASUS UGen AI League (Creator AI, Lightning track, ASUS UGen300 with Hailo-10H).

<!-- RESULTS:BEGIN -->
Results are filled in from `eval/results/REPORT.md` once the test split has been scored.
<!-- RESULTS:END -->

## What is real today, and what is not

| Part | Status |
|---|---|
| Requirement → constraint → evidence → decision pipeline, three-valued logic, coverage, reshoot cards | Implemented, 41 automated tests |
| Media path: MP4/MOV H.264 8-bit, rotation, VFR, start offsets, corrupt and unsupported files | Implemented, tested on synthetic fixtures |
| Semantic retrieval | OpenAI CLIP ViT-B/32 on host **CPU or CUDA** (`cpu-reference` / `cuda-reference`) |
| UGen300 / Hailo-10H | **Not run.** Device check only; the Hailo backend refuses to run until the G1 gate passes on a real device (`docs/MODEL_PLAN.md`) |
| Accuracy | Measured once on a held-out split of openly licensed Wikimedia Commons clips (not self-shot), labelled by two independent AI annotators plus a third pass. See `eval/` |
| Actions, readable text, composition | Manual: the system ranks where to look, a person decides (ADR-004) |
| User study, power, NLE interference | Not done yet. A playback-interference proxy is in `eval/interference.py` |

## Quick start

```bash
python -m pip install -r requirements-ml.txt
python -m scenegap --workdir ./sg_work
```

Open the printed address (`http://127.0.0.1:8765/`). The service binds to this computer only and creates a new
session token on every start. Without `eval/results/calibration.json` the threshold is unknown and analysis
answers `UNCALIBRATED`: SceneGap does not guess a threshold.

Docker (CPU):

```bash
docker build -t scenegap-edge .
docker run --rm -p 127.0.0.1:8765:8765 -v "$PWD/footage:/footage:ro" -v sg_work:/work scenegap-edge --host 0.0.0.0
```

Tests (no model download needed; the test backend is a colour-statistics mock that proves state handling only):

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## How it decides

1. **Requirements** are written in Chinese by the user, with an English retrieval query a person confirms
   (`query_en`; ADR-003). Every edit creates a new revision; old results become `outdated`, never silently reused.
2. **Media**: probe first, hash (SHA-256; duplicates become extra locations), cut shots, sample about 1 frame per
   second on the original presentation timestamps. Times are half-open intervals in ms of the original PTS.
3. **Evidence**: CLIP image embeddings per sample; a text query passes a sample when cosine ≥ τ. τ is calibrated
   on the dev split per model fingerprint and frozen.
4. **Constraints**: consecutive passing samples in one shot form a run. Duration uses conservative bounds (lower
   = span of passing samples; upper = up to the neighbouring failing samples or shot edges). When undecided, the
   window is sampled every 250 ms. Co-occurrence needs all queries in the same frame. Takes are counted by capture.
5. **Status** (automatic, never "done"): `candidate`, `partial`, `not_found`, `unverifiable`, `failed`,
   `not_analyzed`. `not_found` means "nothing reached τ in the analysed scope", not proof of absence.
   Human decisions (`accepted`, `rejected`, `overridden` with a reason) are stored separately; the latest decision
   on a segment wins. Coverage shows human-confirmed and AI-candidate shares separately; N/A when there is nothing
   to count.

Details with file and line references: `docs/ALGORITHMS.md`. Model and hardware plan: `docs/MODEL_PLAN.md`.

## Validation

- `eval/PROTOCOL.md` was committed before any label or threshold existed; its later additions are dated and also
  precede the labels (see `git log -- eval/PROTOCOL.md`).
- `eval/requirements.json`: 11 café-promo requirements, written before any frame was seen.
- `datasets/manifests/commons_manifest.json`: every clip with Commons page, author, licence and SHA-256 of the
  original and of the transcode. Rebuild with `scripts/fetch_commons.py`.
- `eval/LABEL_GUIDE.md`, `eval/adjudicate.py`: two independent annotators on 1 fps contact sheets, a third pass on
  every disagreement, agreement and Cohen's κ reported.
- `eval/evaluate.py calibrate | test | perf`: dev-only calibration (τ and crop policy), one scoring of the test
  split (the script refuses a second run), ablation (title keywords → single-frame semantic → full system), Wilson
  95% intervals, CPU vs GPU timings.
- `eval/report.py` renders `eval/results/REPORT.md` from the result files.

## Security and privacy

Loopback only; random per-run token in a header (media requests may use an HttpOnly SameSite=Strict cookie);
Origin and Host checks (DNS rebinding); footage is read from folders you authorise, by relative path only; nothing
is uploaded; CSV exports neutralise spreadsheet formulas; HTML exports escape all text. Originals are never
modified (tested).

## Repository

```
scenegap/   domain (logic, coverage, reshoot), media (probe, fixtures), shots, backends (CLIP, Hailo check),
            store (SQLite, jobs), export, api (FastAPI), service.py, __main__.py
web/        single-page UI (vanilla JS)
eval/       protocol, requirements, labelling, adjudication, evaluation, interference, results
scripts/    Commons download and transcode, contact sheets
docs/       ALGORITHMS, MODEL_PLAN, ADRs, UI design notes and previews
tests/      unit, integration (real media fixtures), API
```

## Licence

Code: Apache-2.0 (`LICENSE`, `NOTICE`). Footage is not included; each clip keeps its own Commons licence (CC0,
public domain, CC BY, CC BY-SA). Not affiliated with or endorsed by ASUS or Hailo.
