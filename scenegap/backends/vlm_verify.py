"""Second-stage check for candidate clips: a small vision-language model answers a yes/no question per frame.

CLIP ranks clips by how close a frame is to the query, but its score is not calibrated across shots, so almost
every shot finds something (eval/results/REPORT.md). The verifier asks the model directly, for example
"Does this image show coffee being poured into a cup? Answer yes or no.", and reads P(yes) from the next-token
logits. A shot is reported missing when none of its top candidates is confirmed (service.py).

Reference model: Qwen2-VL-2B-Instruct, the same model Hailo lists for Hailo-10H (planned device route).
The question comes from the person-confirmed English query, so there is no per-shot prompt tuning.
"""
from __future__ import annotations

import hashlib
import os
import re

MODEL_ID = os.environ.get("SG_VLM_MODEL", "Qwen/Qwen2-VL-2B-Instruct")


def question_for(query_en: str) -> str:
    """'a photo of coffee being poured into a cup' -> 'Does this image show coffee being poured into a cup? Answer yes or no.'"""
    q = re.sub(r"^(a|an)\s+(photo|picture|image)\s+of\s+", "", query_en.strip(), flags=re.I).rstrip(".")
    return f"Does this image show {q}? Answer yes or no."


class VlmVerifier:
    name = "qwen2-vl-2b"

    def __init__(self, device: str | None = None, max_pixels: int = 448 * 448):
        import torch
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(MODEL_ID, dtype=dtype).to(self.device).eval()
        self.proc = AutoProcessor.from_pretrained(MODEL_ID, min_pixels=224 * 224, max_pixels=max_pixels)
        tok = self.proc.tokenizer
        self.yes = [tok.encode(w, add_special_tokens=False)[0] for w in ("Yes", "yes")]
        self.no = [tok.encode(w, add_special_tokens=False)[0] for w in ("No", "no")]
        self.fingerprint = hashlib.sha256(f"{MODEL_ID}|{max_pixels}|v1".encode()).hexdigest()[:16]
        self.calls = 0

    def p_yes(self, image, question: str) -> float:
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": question}]}]
        text = self.proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inp = self.proc(text=[text], images=[image], return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            logits = self.model(**inp).logits[0, -1].float()
        y = self.torch.logsumexp(logits[self.yes], 0)
        n = self.torch.logsumexp(logits[self.no], 0)
        self.calls += 1
        return float(self.torch.sigmoid(y - n))


class MockVerifier:
    """Test double: answers from a dict {(asset_or_path, t_ms): p}, default 0."""
    name = "mock-verifier"
    fingerprint = "mock"

    def __init__(self, table=None):
        self.table = table or {}
        self.calls = 0

    def p_yes(self, image, question: str) -> float:
        self.calls += 1
        return float(self.table.get(image, 0.0))
