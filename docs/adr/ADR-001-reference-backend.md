# ADR-001: CLIP ViT-B/32 fp32 on host as the reference backend

Status: **Accepted** (2026-10-26). Implemented in `scenegap/backends/cpu_clip.py`.

## Context
- We need image-text retrieval that runs today, without a UGen300, and that produces numbers we can
  reproduce.
- Any NPU result must be compared with a known-good result from the **same** model. The product rules say
  NPU results are never claimed without a real device run, and that CPU/GPU results are reported
  separately.
- The Hailo-10H zoo ships an image encoder HEF (`clip_vit_b_32_image_encoder`) and a text encoder HEF
  (`clip_vit_b_32_text_encoder`) for exactly this checkpoint. Both are marked as used by hailo-apps. See
  MODEL_PLAN §2.1.

## Decision
- The reference backend is `openai/clip-vit-base-patch32` through Hugging Face Transformers, fp32, on host
  CPU or CUDA. The text and image towers come from one checkpoint (512-d, 224×224, CLIP tokenizer and
  preprocessing).
- Every run records a provenance label (`cpu-reference` or `cuda-reference`) and a model fingerprint. Indexes
  are stored per fingerprint and never mixed (TC-016, TC-030).
- No threshold is built in. `semantic_threshold` must be calibrated on the dev split, otherwise the run is
  refused.

## Consequences
- The product works end to end without the device. The NPU becomes an accelerator that is measured against
  this reference (G1 gate, ADR-002), not a dependency.
- CLIP ViT-B/32 is a mid-quality retriever. Fine detail, small text and actions are out of reach (ADR-004).
- Follow-ups (ALGORITHMS §5):
  - C8: CLIPProcessor center-crop drops about 44 % of a 16:9 frame. Choose a crop policy on dev.
  - C9: add `artifact_sha256` and prompt/text preprocessing to the fingerprint.
  - C10: assert that the output dimension is 512.
  - C5: key τ by fingerprint.
