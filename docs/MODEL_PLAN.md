# SceneGap Edge: model and hardware plan

Target: ASUS UGen300 (Hailo-10H; vendor spec: 40 TOPS INT4 / 20 TOPS INT8, 8 GB LPDDR4, USB 3.1 Gen2 Type-C
10 Gbps, 2.5 W typical [S1]). Written 2026-10-26.

**Labels used in this document**
- **vendor**: a number published by Hailo or ASUS. The Hailo Model Zoo figures were measured on PCIe Gen3 ×4
  with an Intel i5-9400 host and DFC v5.4.0 [S2]. They were **not** measured on a UGen300 over USB.
- **estimate**: our arithmetic or judgement. It is not a measurement.
- **measured**: run by us. There are **no measured UGen300 numbers yet**, and every NPU cell is `not_run`
  until a real device run. CPU/GPU reference results are reported separately as `cpu-reference` /
  `cuda-reference` (`eval/PROTOCOL.md`).
- **unverified**: we could not confirm it from a source we opened.

---

## 1. Capability map

Status values: **implemented** (in code now), **planned** (designed, not coded), **manual** (a person
decides; the automatic verdict is UNKNOWN).

| Capability | Model | Runs on | Status in repo | Gate to become automatic | Fallback | License |
|---|---|---|---|---|---|---|
| Semantic retrieval | OpenAI CLIP ViT-B/32 (`openai/clip-vit-base-patch32`), 512-d, 224×224. Text and image towers come from the same checkpoint. | Now: host CPU/CUDA, fp32 (`cpu_clip.py`). Planned: image tower on UGen300 as zoo HEF `clip_vit_b_32_image_encoder` [S2,S3]; text tower on host CPU with the same HF weights. | implemented (reference); Hailo **planned**, `HailoClip` refuses to run | **G1** (§4) on a real device | stay on the CPU/GPU reference; then TinyCLIP-61M/32 or SigLIP2-B/32 HEF with its own reference (§3) | CLIP code: MIT (per repo; not re-checked). HEF redistribution terms: unverified |
| Chinese queries | Human-confirmed English `query_en` (ADR-003) | host | implemented (`query_en` is mandatory) | — | — | — |
| Co-occurrence ("two people", "person + cup") | v1: every CLIP query ≥ τ in the **same frame**. v2: YOLOv8s / YOLO11s (COCO-80) counts and classes in the same frame. | v1 host / UGen300 with CLIP. v2: UGen300 HEF `yolov8s` / `yolov11s` [S4] | v1 implemented (CLIP only); v2 planned | Per-class precision ≥ 0.90 and recall ≥ 0.70 at a confidence frozen on dev frames labelled with objects. Person-count accuracy ≥ 0.90 on dev | CLIP-only candidate; a person confirms | Ultralytics YOLO: **AGPL-3.0** or an enterprise licence [S16]. This is acceptable for an open-source entry but must be stated |
| Object presence ("cup visible") | v1: CLIP query. v2: COCO class from the detector (cup, bottle, laptop, …); non-COCO objects stay CLIP | as above | v1 implemented; v2 planned | as above, per class used in the scripts | CLIP + manual | as above |
| Continuous duration | Algorithm: conservative bounds + densify (`ALGORITHMS.md` §3.3, §3.6) | host | implemented | No false PASS on dev gold intervals. Report the false-FAIL rate caused by cut errors (risk C1) | UNKNOWN → playback | — |
| Shot boundaries | HSV-histogram Bhattacharyya distance, threshold 0.45 | host | implemented (uncalibrated) | Cut precision/recall ≥ 0.9 / 0.9 (±2 frames) on labelled dev cuts | report duration as UNKNOWN near weak cuts | OpenCV Apache-2.0 (not re-checked) |
| Quality | Laplacian variance (blur), clipped-pixel share (exposure) | host | implemented; thresholds uncalibrated; exposure not used in verdicts | Calibrate on dev frames labelled blurred / OK. Agreement ≥ 0.85 | soft warning only | — |
| Composition (left/right, framing) | Detector boxes on the **uncropped** frame → thirds / relative order | UGen300 (detector) + host geometry | **manual** | Precision ≥ 0.90 on dev composition labels | manual (the card shows the hint) | as detector |
| Readable brand text (OCR) | PP-OCRv5 mobile: detection on UGen300 (`paddle_ocr_v5_mobile_detection`, 544×960) [S5]; recognition: Hailo HEF `paddle_ocr_v5_mobile_recognition` (48×320) [S6] **only if** its output character set covers Traditional Chinese; otherwise PP-OCRv5 mobile rec on host CPU | UGen300 + host | **manual** | Test set built from the **target script's** brand strings in Traditional Chinese (§5). Exact-match ≥ 0.90, false-readable ≤ 0.02 | manual | PaddleOCR Apache-2.0 (not re-checked) |
| Action ("pouring", "grinding", "picking up a cup") | v1: multi-frame CLIP state sequence used **only to rank**. Stage II options: Qwen2-VL-2B yes/no verifier on UGen300 [S7]; pose heuristics (`yolov8s_pose`) [S8]; X-CLIP on host [S15] | UGen300 / host | **manual** (ADR-004) | Precision ≥ 0.95 (Wilson lower bound ≥ 0.85) at recall ≥ 0.5 on a labelled action set with hard negatives (holding vs pouring) | manual; the ranking aid still helps find the window | Qwen2-VL: Apache-2.0 (unverified); X-CLIP MIT [S15] |
| Script → requirements drafting | Optional LLM (e.g. Qwen2.5-1.5B-Instruct on UGen300, GenAI zoo [S7]) or a template form | UGen300 / host | **manual** (a person writes and confirms; unconfirmed = `draft`) | Drafts must always be confirmed. Measure edit rate and missed requirements against human lists on 5 scripts | template form | Qwen: Apache-2.0 (unverified) |

LLM, VLM and LoRA are **optional**. None is required for any status above.

---

## 2. Research findings (Hailo-10H)

### 2.1 CLIP-type encoders in the Hailo Model Zoo (HAILO10H, DFC v5.4.0, vendor)

Image encoders (zero-shot classification page; accuracy is zero-shot top-1 on CIFAR-100) [S2]:

| HEF | float / HW top-1 | FPS b=1 / b=8 | input | OPS (G) |
|---|---|---|---|---|
| `clip_vit_b_32_image_encoder` (marked as used by hailo-apps) | 65.3 / 64.5 | 81.5 / 350 | 224×224×3 | 8.8 |
| `clip_vit_b_16_image_encoder` | 68.6 / 64.6 | 51.5 / 158 | 224 | 35.1 |
| `clip_resnet_50x4_image_encoder` | 50.3 / 50.9 | 62.6 / 156 | 288 | 41.3 |
| `siglip2_b_32_256_image_encoder` | 74.7 / 70.4 | 64.7 / 221 | 256 | 11.5 |
| `tinyclip_vit_61m_32_text_29m_laion400m_image_encoder` | 72.8 / 69.8 | 101 / 388 | 224 | 6.18 |
| `tinyclip_vit_40m_32_text_19m_laion400m_image_encoder` | 69.7 / 68.0 | 127 / 467 | 224 | 4 |
| `clip_vit_l_14_laion2B_image_encoder` | 78.6 / 77.5 | 17.1 / 43.0 | 224 | 162 |

- The zoo config for `clip_vit_b_32_image_encoder` lists source `github.com/openai/CLIP`, ONNX
  `clip_vit_b_32.onnx`, output **1×1×512**, and `hailo10h` among the supported architectures [S3]. Because
  the output is 512-d, the projection is inside the HEF. It is the same model family and weights as our
  reference. Bit-level equality with the HF port's preprocessing still has to be confirmed in G1.
- Text encoders exist as HEFs too (text-image retrieval page, Retrieval@10 float/HW) [S9]:
  `clip_vit_b_32_text_encoder` (marked as used by hailo-apps), 90.6 / 89.3, **48.9 / 98.8 FPS**, input
  `1×77×512`, source `huggingface.co/openai/clip-vit-base-patch32`. Also SigLIP2-B/32-256 text (96.1 / 96.5,
  34.3 FPS, input `1×64×768`) and TinyCLIP text encoders.
- The input `1×77×512` is the token **embeddings**, not the token ids. In hailo-apps `clip_text_utils.py`
  [S10], the host does tokenization (`clip_tokenizer.json`), the token-embedding lookup
  (`token_embedding_lut.npy`, 49408×512), EOT pooling, `text_projection.npy` and L2 normalisation. Only the
  transformer runs on Hailo. The code leaves the HF-weight transpose of the projection commented out, so the
  projection orientation is an integration hazard. Whether positional embeddings are inside the HEF is not
  stated (unverified).
- The hailo-apps CLIP pipeline README lists a CLIP ResNet-50x4 image encoder and describes the text
  embeddings as "pre-computed on CPU" [S11]. Its stated image input (640×640) conflicts with the zoo's 288×288
  for RN50x4 (unverified). The README states `--arch hailo8 | hailo8l | hailo10h`.
- No MobileCLIP HEF was found in the zoo pages we opened. MobileCLIP would have to be compiled with DFC v5.x
  ourselves (unverified effort).
- A community report on the Hailo-8L found compiled CLIP RN50 embeddings far from the OpenAI reference
  (unresolved). Staff pointed to the zoo model script (normalisation on chip, uint8 input, optimisation
  settings) [S12]. **This is why G1 exists.**

**Answer to "does the text encoder run on the host CPU?"** It can run either way. A HEF exists. The
reference hailo-apps pipeline precomputes text on the CPU. We recommend **host CPU with the same HF fp32
weights** for v1. Queries are few (tens per project), so latency does not matter. It also keeps quantization
error on one side only, and it removes the LUT/projection hazards.

### 2.2 Detection, pose, OCR, video (HAILO10H, vendor) [S4,S5,S6,S8,S13,S14]

| HEF | metric float / HW | FPS b=1 / b=8 | input |
|---|---|---|---|
| `yolov8s` (COCO mAP) | 44.6 / 44.1 | 166 / 252 | 640 |
| `yolov11s` | 46.3 / 45.5 | 142 / 223 | 640 |
| `yolov8n` | 37.0 / 36.4 | 375 / 370 | 640 |
| `yolov8s_pose` (COCO AP) | 59.2 / 56.8 | 161 / 217 | 640 |
| `yolo_world_v2s` (zero-shot det, COCO) | 36.4 / 31.9 | 46.6 / 63.8 | 640 |
| `paddle_ocr_v5_mobile_detection` (ICDAR15; metric unlabeled on page) | 4.59 / 4.26 | 22.5 / 40.8 | 544×960 |
| `paddle_ocr_v5_mobile_recognition` (ICDAR15 rec) | 62.3 / 60.1 | 127 / 399 | 48×320 |
| `r3d_18` (Kinetics-400 top-1) | 48.9 / 49.1 | 55.4 / 87.9 | 112×112×48 |

OCR caveat: the hailo-apps PaddleOCR decoder (`paddle_ocr_utils.py`) hard-codes a **Latin-only**
`CHARACTERS` list, and its optional corrector uses an English dictionary [S17]. The zoo evaluates
recognition on ICDAR15 (English). PaddleOCR's documentation says PP-OCRv5 recognition covers Simplified and
Traditional Chinese, English and Japanese in one model (search snippet of paddleocr.ai; the page was not
opened; we did not confirm this for the mobile variant). We therefore **assume the Hailo rec HEF is not
usable for Traditional Chinese** until its output class dimension is checked on the device.

### 2.3 GenAI zoo VLMs (HAILO10H, vendor) [S7]

| Model | Numerics | TTFT | TPS | Vision encoder FPS | Note |
|---|---|---|---|---|---|
| Qwen2-VL-2B-Instruct | A8W4 | 1.02 s | 7.04 | 3.00 (336×336) | image + text, HailoRT > 5.2.0 |
| Qwen3-VL-2B-Instruct | A16W4 | 1.47 s | 4.74 | 4.59 | video + text, HailoRT > 5.3.0. Community: expects **512×288** input, not 336×336; the wrong size fails with `HAILO_INVALID_OPERATION` [S18] |

Estimate for one yes/no verification over one frame with Qwen2-VL-2B: about 0.33 s vision + 1.02 s TTFT +
about 0.7 s for 5 tokens ≈ **2 s**. This is fine for re-checking the top 5 candidates, and too slow for
indexing.

---

## 3. Alternatives if the ViT-B/32 HEF fails G1

| Option | Hailo HEF | Pros | Cons |
|---|---|---|---|
| TinyCLIP ViT-61M/32 (LAION-400M) | image + text [S2,S9] | faster (101 / 388 FPS), higher CIFAR zero-shot (72.8) | different embedding space → new CPU reference, new τ, new dev evaluation |
| SigLIP2 B/32-256 | image + text [S2,S9] | **multilingual** (Gemma tokenizer; text lowercased, padded to 64 [S19]); strongest retrieval@10 | larger HW drop (74.7→70.4); sigmoid-trained scores need their own τ; 768-d |
| CLIP ViT-B/16 | image + text | finer detail | drop 68.6→64.6, 51.5 FPS |
| MobileCLIP | none found | strong on mobile CPU | must compile ourselves; risky before the deadline |
| Stay on the CPU/GPU reference | — | always available | no NPU story; labelled `cpu-reference` |

---

## 4. G1 gate: quantized embeddings vs the fp32 reference

Run only on a real UGen300 with a HAILO10H identity check (see code risk C15). Record the HEF sha256,
HailoRT and firmware versions, and the host OS.

**Input fairness:** the host produces the **same preprocessed uint8 224×224 tensors** (same crop policy,
code risk C8). They go to (a) the fp32 reference image tower and (b) the HEF. The frames are all dev-split
samples (≥ 2,000 frames). The queries are all dev requirements (≥ 40).

| ID | Metric | Pass criterion (proposed; freeze in `eval/PROTOCOL.md` before the run) |
|---|---|---|
| G1a | Cosine between fp32 and HEF embeddings, per frame | median ≥ 0.98, 5th percentile ≥ 0.95 |
| G1b | Ranking agreement per query: Spearman ρ between the fp32 and HEF similarity columns over all dev frames | median ρ ≥ 0.95, worst query ≥ 0.85 |
| G1c | Top-K overlap per query: \|TopK_fp32 ∩ TopK_hef\| / K for K = 5, 10, at segment level after per-shot de-duplication | mean ≥ 0.80 (K=5), ≥ 0.85 (K=10) |
| G1d | Task: dev Recall@5 and Precision@5 (PROTOCOL definitions), each backend with **its own τ calibrated on dev** | No dev shot lost from the top 5 compared with fp32 (with 11 dev shots, one shot is 9 points, so a 3-point bar could not be measured); Precision@5 ≥ fp32 − 5 points. Changed 2026-10-26 before any device run |
| G1e | Status agreement on the project simulation (dev) | ≥ 90 % same status; zero cases of `candidate` on HEF where fp32 says `not_found` *and* gold says unavailable |
| G1f | Throughput: measured frames/s at b=1 and b=8 over USB, and end-to-end time for a 60 s clip | reported, no pass bar; never replaced by vendor figures |

Rationale: the vendor's CIFAR-100 zero-shot drop for ViT-B/32 is small (65.3 → 64.5) [S2]. Retrieval
ranking is more sensitive than top-1 class, so we gate on ranking metrics directly. If G1 fails, apply in
order: (1) recompile with a project calibration set (dev frames) and the zoo model script settings; (2)
keep the last layers at 16-bit if DFC allows it (unverified); (3) switch to TinyCLIP-61M with a new
reference; (4) ship with `cpu-reference` and report the NPU result as failed G1, with its numbers.

τ is per fingerprint: the HEF backend gets a new fingerprint (quantization label **and** HEF sha256, code
risk C9), and its own τ is calibrated on dev and then frozen.

---

## 5. OCR validation for Traditional Chinese (gate for `readable_text`)

1. Collect every brand or prop string in the **target script** (e.g. shop name, cup print).
2. Build a test set of real footage of those exact strings. Vary size (text height 12–80 px at 1080p),
   angle (0–45°), motion blur, and exposure. Include negatives: similar-looking strings, partial occlusion,
   and Simplified-character variants.
3. Normalise before matching: NFKC, full-width to half-width for ASCII, whitespace. **Do not** fold
   Traditional and Simplified characters together (that would make a wrong-script print count as readable).
4. Metrics: CER, exact-match of the target string, and **false-readable rate** (system says readable, a
   person says not readable).
5. Freeze the confidence and edit-distance thresholds on dev, then score once on test. Until it passes,
   `readable_text` stays MANUAL. OCR output is shown only as a hint.

---

## 6. Throughput budget for one 60 s clip at 1 fps

About 60 coarse samples, plus shot-middle frames, plus densify (≤ 4 frames per second of uncertain shot).

| Stage | UGen300 (vendor FPS, PCIe; USB not_run) | Host CPU | Host GPU |
|---|---|---|---|
| Full decode + histograms (host, all frames) | host only | **measure** (no published number) | — |
| CLIP B/32 image, 60 frames | 0.74 s (b=1) / 0.17 s (b=8), vendor | **estimate** 1–5 s (8.8 GOPs/frame [S2] at an assumed 100–500 GFLOP/s effective) | **estimate** < 0.5 s |
| Densify, worst case of one 60 s shot (+240 frames) | 2.9 s / 0.69 s, vendor | estimate 5–20 s | estimate < 1 s |
| Text query (one) | 20 ms (48.9 FPS), vendor, if the HEF is used | estimate tens of ms | — |
| YOLOv8s on 60 frames | 0.36 s / 0.24 s, vendor | — | — |
| OCR detection on 10 candidate frames | 0.44 s (22.5 FPS), vendor | — | — |
| VLM yes/no on 5 candidates (Qwen2-VL-2B) | about 10 s, estimate from vendor TTFT/TPS | — | — |

USB 10 Gbps transport: 60 × 224×224×3 bytes ≈ 9 MB (estimate), which is not a bottleneck on paper. The
real cost is host decode and preprocessing, so the NPU mostly frees the CPU rather than shortening the
total. Fill every `measure` cell from `eval/` runs. Vendor cells are never relabelled as measured.

---

## 7. First version on the device (recommendation)

1. **One model on the NPU:** the zoo HEF `clip_vit_b_32_image_encoder` (it matches the reference weights).
   Text runs on host CPU with the same HF weights. Batch 8. A new `HailoClip` manifest records `target_arch =
   hailo10h`, `quantization = "hailo-int8 (zoo)"`, `artifact_sha256 = HEF hash`, and `compatibility_verified
   = true` only after G1 passes.
2. Same host preprocessing as the reference, chosen by the crop experiment E2 first, so that G1 compares
   like with like.
3. Everything else stays on the host: decode, cuts, duration, quality, status, cards.
4. Optional second NPU model, shown as **hints only**: `yolov8s` for person count and object boxes. It uses
   the same frames and the HailoRT scheduler (hailo-apps runs detection and CLIP together this way [S11]).
   Verdicts for co-occurrence and composition stay as they are until their own gate passes.
5. Report CPU, GPU and NPU numbers in **separate columns**. If no device run happened, the NPU column says
   `not_run`.

---

## 8. Stage II plan and exit criteria

| Step | Work | Exit criterion (measurable) |
|---|---|---|
| S2-0 | Fix code risks C1, C5, C6, C7, C8 (ALGORITHMS §5) before any blind test | unit tests for each; dev numbers recomputed |
| S2-1 | Device bring-up: UGen300 identified as HAILO10H, HEF loads, b=1/b=8 timing over USB | log with HailoRT and firmware versions, HEF sha256, measured FPS |
| S2-2 | G1 on dev | all G1a–G1e pass, or a documented failure and fallback |
| S2-3 | Detector hints → co-occurrence / object constraints | per-class precision ≥ 0.90, person-count accuracy ≥ 0.90 on dev; then one test-split score |
| S2-4 | Composition from boxes | precision ≥ 0.90 on dev composition labels |
| S2-5 | OCR, Traditional Chinese (§5) | exact-match ≥ 0.90, false-readable ≤ 0.02 on the target-script test set |
| S2-6 | Action aid (and optional VLM verifier) | aid: dev Precision@5 of action windows ≥ 0.6. Verifier (optional): precision ≥ 0.95 with Wilson lower bound ≥ 0.85 at recall ≥ 0.5, else it stays MANUAL |
| S2-7 | Frozen end-to-end on the test split (PROTOCOL), run once | Recall@5, Precision@5, gap recall, wrong-reshoot rate, unknown rate with Wilson 95 % CIs; CPU / GPU / NPU latency and NPU power reported separately |

---

## Sources (opened while writing this document)

- [S1] ASUS UGen300 tech spec: https://www.asus.com/motherboards-components/ai-accelerator/ugen/ugen300-usb-8g/techspec/
- [S2] Hailo Model Zoo, HAILO10H zero-shot classification: https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO10H/HAILO10H_zero_shot_classification.rst
- [S3] Zoo config `clip_vit_b_32_image_encoder.yaml`: https://raw.githubusercontent.com/hailo-ai/hailo_model_zoo/master/hailo_model_zoo/cfg/networks/clip_vit_b_32_image_encoder.yaml
- [S4] HAILO10H object detection: https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO10H/HAILO10H_object_detection.rst
- [S5] HAILO10H text detection: https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO10H/HAILO10H_text_detection.rst
- [S6] HAILO10H text recognition: https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO10H/HAILO10H_text_recognition.rst
- [S7] Hailo GenAI Model Zoo models: https://github.com/hailo-ai/hailo_model_zoo_genai/blob/main/docs/MODELS.rst
- [S8] HAILO10H pose estimation: https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO10H/HAILO10H_pose_estimation.rst
- [S9] HAILO10H text-image retrieval (text encoders): https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO10H/HAILO10H_text_image_retrieval.rst
- [S10] hailo-apps `clip_text_utils.py`: https://raw.githubusercontent.com/hailo-ai/hailo-apps/main/hailo_apps/python/pipeline_apps/clip/clip_text_utils.py
- [S11] hailo-apps CLIP app README: https://raw.githubusercontent.com/hailo-ai/hailo-apps/main/hailo_apps/python/pipeline_apps/clip/README.md (directory: https://github.com/hailo-ai/hailo-apps/tree/main/hailo_apps/python/pipeline_apps/clip)
- [S12] Hailo community, "Large difference between compiled model for CLIP": https://community.hailo.ai/t/large-difference-between-compiled-model-for-clip/5126
- [S13] HAILO10H video classification: https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO10H/HAILO10H_video_classification.rst
- [S14] HAILO10H zero-shot object detection: https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO10H/HAILO10H_zero_shot_object_detection.rst
- [S15] X-CLIP base/32 model card: https://huggingface.co/microsoft/xclip-base-patch32
- [S16] Ultralytics licence: https://github.com/ultralytics/ultralytics
- [S17] hailo-apps PaddleOCR utils: https://raw.githubusercontent.com/hailo-ai/hailo-apps/main/hailo_apps/python/standalone_apps/paddle_ocr/paddle_ocr_utils.py (app: https://github.com/hailo-ai/hailo-apps/tree/main/hailo_apps/python/standalone_apps/paddle_ocr)
- [S18] Hailo community, Qwen3-VL-2B input size: https://community.hailo.ai/t/qwen3-vl-2b-instruct-hef-fails-with-hailo-invalid-operation-6-on-hailort-5-3-0-generate-impl-fails-despite-successful-model-load/19104
- [S19] SigLIP2 in Transformers (lowercase, max_length 64): https://huggingface.co/docs/transformers/en/model_doc/siglip2 ; model card (Apache-2.0): https://huggingface.co/google/siglip2-base-patch32-256
- [S20] Multilingual text encoders: https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1 (Apache-2.0, zh-cn/zh-tw, student of clip-ViT-B-32) ; https://huggingface.co/M-CLIP/XLM-Roberta-Large-Vit-B-32 (pairs with OpenAI ViT-B/32; Zh text→image R@10 89.3 on translated MS-COCO; licence not stated on the card)
- Also opened: https://github.com/hailo-ai/hailo-apps , https://github.com/hailo-ai/hailo_model_zoo/tree/master/docs/public_models/HAILO10H , https://github.com/hailo-ai/hailo-apps/tree/main/hailo_apps/python/gen_ai_apps , https://github.com/hailo-ai/hailo-apps/blob/main/hailo_apps/python/gen_ai_apps/vlm_chat/README.md (names no model)

Not opened (search snippets only, treat as unverified): PaddleOCR text-recognition docs (paddleocr.ai) on the
PP-OCRv5 language coverage; CNX Software UGen300 article.
