# ADR-002: Hailo route A (zoo CLIP ViT-B/32 image HEF on UGen300, text on host)

Status: **Proposed**. The implementation is blocked on hardware: `HailoClip` raises `DeviceUnavailable`
until a UGen300 is attached and G1 passes.

## Context
- UGen300 = Hailo-10H, 40 TOPS INT4 / 20 TOPS INT8, 8 GB, USB 3.1 Gen2, 2.5 W typical (ASUS spec).
- The Hailo Model Zoo (HAILO10H, DFC v5.4.0) lists `clip_vit_b_32_image_encoder`. Vendor numbers: 224×224
  input, 512-d output with the projection included, 81.5 FPS at batch 1 / 350 FPS at batch 8, measured on
  PCIe, not USB. CIFAR-100 zero-shot top-1 is 65.3 float vs 64.5 on hardware. Its source is the original
  OpenAI CLIP, which is our reference model.
- A text encoder HEF also exists. It needs host-side tokenization, a token-embedding LUT, EOT pooling and a
  projection, and hailo-apps leaves a projection-orientation detail commented out. The hailo-apps CLIP
  pipeline precomputes text embeddings on the CPU.
- A community report shows compiled CLIP embeddings far from the reference when preprocessing or
  quantization settings differ.

## Decision
- Route A: run **only the image encoder** on the UGen300, using the zoo HEF. Text uses the same fp32 HF
  weights on the host CPU, so the pair stays matched: same checkpoint, tokenizer, projection and dimension.
  Quantization error then sits on one side only, and G1 measures it.
- The host does the decode and preprocessing. The NPU receives the identical uint8 224×224 tensor that the
  reference receives.
- The Hailo backend gets its own fingerprint (quantization label + HEF sha256) and its own τ calibrated on
  dev.
- A run is labelled `hailo` only if the device identifies as HAILO10H and the HEF actually ran. Otherwise the
  NPU column says `not_run`.
- Enable it for users only after **G1** passes (MODEL_PLAN §4): per-frame cosine, per-query Spearman ρ,
  top-K overlap, and dev Recall@5 / Precision@5 within tolerance.

## Consequences
- The NPU mainly offloads embedding. Host decode remains, so the end-to-end speedup has to be measured,
  not assumed from vendor FPS.
- If G1 fails, the fallback order is: (1) recompile with a dev calibration set, (2) keep the last layers at
  higher precision (if the DFC allows), (3) TinyCLIP-61M/32 or SigLIP2-B/32 HEFs with a new CPU reference,
  (4) ship on the CPU/GPU reference and publish the failed G1 numbers.
- Optional later: `yolov8s` on the same device as a second model for co-occurrence and composition hints.
  Its verdicts stay gated separately.
