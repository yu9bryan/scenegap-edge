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


def check_questions(req) -> list[str]:
    """The person-confirmed check questions of a requirement (main first, then conditions), or one built from query_en."""
    qs = [q.strip() for q in (getattr(req, "check_questions", None) or []) if q and q.strip()]
    if not qs:
        return [question_for(req.query_en)]
    return [q if q.lower().endswith("answer yes or no.") else q.rstrip() + " Answer yes or no." for q in qs]


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

    def p_yes_many(self, image, questions: list[str]) -> list[float]:
        """P(yes) for several questions about one image in one batch (left padding, last-token logits)."""
        tok = self.proc.tokenizer
        tok.padding_side = "left"
        texts = [self.proc.apply_chat_template([{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": q}]}],
                                               tokenize=False, add_generation_prompt=True) for q in questions]
        inp = self.proc(text=texts, images=[image] * len(texts), return_tensors="pt", padding=True).to(self.device)
        with self.torch.no_grad():
            logits = self.model(**inp).logits[:, -1].float()
        y = self.torch.logsumexp(logits[:, self.yes], 1)
        n = self.torch.logsumexp(logits[:, self.no], 1)
        self.calls += len(questions)
        return [float(x) for x in self.torch.sigmoid(y - n)]


def frame_at(path: str, t_ms: int):
    """One RGB frame at t_ms (original timestamps), decoded with PyAV."""
    import av
    with av.open(path) as c:
        st = c.streams.video[0]
        c.seek(int(t_ms / 1000 / st.time_base), stream=st, backward=True)
        last = None
        for f in c.decode(st):
            last = f
            if f.time is not None and f.time * 1000 >= t_ms - 1:
                break
        return last.to_image() if last is not None else None


class MockVerifier:
    """Test double: the same P(yes) for every frame, or p(image, question) when p is a function."""
    name = "mock-verifier"
    fingerprint = "mock"

    def __init__(self, p=0.0):
        self.p = p
        self.calls = 0

    def p_yes(self, image, question: str) -> float:
        self.calls += 1
        return self.p(image, question) if callable(self.p) else self.p

    def p_yes_many(self, image, questions: list[str]) -> list[float]:
        return [self.p_yes(image, q) for q in questions]
