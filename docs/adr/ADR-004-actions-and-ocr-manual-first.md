# ADR-004: Actions, readable text and composition are manual first

Status: **Accepted** (implemented: non-AUTO constraints return UNKNOWN with `NEEDS_MANUAL`; unknown AUTO
kinds also return UNKNOWN).

## Context
- A single frame cannot prove an action. "Pouring" and "holding a kettle over a cup" look the same in one
  frame. Frame-level CLIP similarity can find *where to look*, but it cannot verify that an action happened.
- Device options for actions are limited:
  - `r3d_18` (Kinetics-400, 112×112, 49.1 % top-1 on HW) is closed-set.
  - Qwen2-VL-2B / Qwen3-VL-2B run on Hailo-10H. Vendor TTFT is 1.0–1.5 s and 4.7–7 tokens/s, so a yes/no
    check takes about 2 s per candidate.
  - Pose (`yolov8s_pose`) gives wrist tracks, but every action needs its own hand-made rule.
  - X-CLIP (8 frames, MIT) would run on the host only.
  None of these has been evaluated on our footage.
- OCR: Hailo ships PP-OCRv5 mobile detection and recognition HEFs, but the hailo-apps decoder is Latin-only
  and the zoo evaluates on English ICDAR15. Traditional Chinese brand text is unverified on the device.
- Product rules: OCR is automatic only after testing on the target script (Traditional Chinese), and single-
  frame similarity never proves an action.

## Decision
- `action`, `readable_text` and `composition` constraints are **MANUAL** in v1. Their automatic verdict is
  always UNKNOWN. With the current AND logic, a requirement with a **hard** manual constraint can never
  reach `candidate`: it stays `partial` [`NEEDS_MANUAL`] until a person accepts a segment. A soft manual
  constraint lets the requirement reach `candidate`, with the manual check listed. Choosing hard or soft is
  part of confirming the requirement.
- Planned v1.x aid (actions): rank windows by an ordered multi-frame CLIP state sequence over 250 ms samples,
  using prompt ensembles and requiring temporal order and persistence. The output is used **only to rank
  where the person should look**. The verdict stays UNKNOWN.
- Each capability becomes AUTO only after its own gate (MODEL_PLAN §1, §5, §8):
  - Actions: precision ≥ 0.95 (Wilson lower bound ≥ 0.85) at recall ≥ 0.5 on a labelled set with hard
    negatives.
  - OCR: exact-match ≥ 0.90 and false-readable ≤ 0.02 on a test set built from the target script's
    Traditional Chinese strings.
  - Composition: precision ≥ 0.90 on dev labels.
- A VLM, if used, is a re-checker on the top candidates, never the indexer. It is never required.

## Consequences
- The reviewer, not the model, decides these conditions, and reshoot cards list
  them under "confirmed by a person".
- Lower automation for action-heavy scripts. The ranking aid and the evidence viewer have to make manual
  checks fast (jump to the window, loop playback).
- Adding automatic checks later does not change the status logic. A constraint's capability simply moves
  from MANUAL to AUTO, with a new fingerprint and frozen thresholds.
