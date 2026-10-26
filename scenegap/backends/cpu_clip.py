"""Reference backend: OpenAI CLIP ViT-B/32 through Hugging Face Transformers on the host (CPU or CUDA).

This is the reproducible reference the Hailo backend must be compared against (PRD 11.4 route A).
Its provenance label says where it really ran; it is never reported as NPU output.
"""
from __future__ import annotations

import os

import numpy as np

from .base import Backend, ModelManifest

MODEL_ID = os.environ.get("SG_CLIP_MODEL", "openai/clip-vit-base-patch32")
CROPS = ("center-crop", "pad-square")       # center-crop drops ~44% of a 16:9 frame's width; pad-square keeps all of it


def pad_square(img):
    """Letterbox to a square on CLIP's mean colour so the whole 16:9 frame reaches the encoder."""
    from PIL import Image
    w, h = img.size
    side = max(w, h)
    canvas = Image.new("RGB", (side, side), (122, 116, 104))
    canvas.paste(img.convert("RGB"), ((side - w) // 2, (side - h) // 2))
    return canvas


class ClipReference(Backend):
    def __init__(self, device: str | None = None, batch: int = 32, crop: str | None = None):
        import torch
        import transformers
        from transformers import CLIPModel, CLIPProcessor
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.name = f"{'cuda' if self.device.startswith('cuda') else 'cpu'}-reference"
        self.model = CLIPModel.from_pretrained(MODEL_ID).to(self.device).eval()
        self.proc = CLIPProcessor.from_pretrained(MODEL_ID)
        self.batch = batch
        self.crop = crop or os.environ.get("SG_CLIP_CROP", "center-crop")
        if self.crop not in CROPS:
            raise ValueError(f"crop must be one of {CROPS}")
        rev = getattr(self.model.config, "_commit_hash", None) or "unknown"
        dim = int(self.model.config.projection_dim)
        self.manifest = ModelManifest(
            model_id=MODEL_ID, version=str(rev), purpose="image-text retrieval", target_arch=self.device,
            interface="transformers", input_size=int(self.model.config.vision_config.image_size), embedding_dimension=dim,
            paired_text_encoder=MODEL_ID, preprocess_id=f"clip-processor-default+{self.crop}", quantization="fp32",
            artifact_sha256=None, license_reference="MIT (OpenAI CLIP)", runtime_version=f"torch {torch.__version__}; transformers {transformers.__version__}",
            compatibility_verified=False)

    def encode_images(self, images) -> np.ndarray:
        outs = []
        with self.torch.no_grad():
            for i in range(0, len(images), self.batch):
                chunk = images[i:i + self.batch]
                if self.crop == "pad-square":
                    chunk = [pad_square(im) for im in chunk]
                px = self.proc(images=chunk, return_tensors="pt")["pixel_values"].to(self.device)
                f = self.model.get_image_features(pixel_values=px)
                f = getattr(f, "pooler_output", f)
                outs.append(self.torch.nn.functional.normalize(f.float(), dim=-1).cpu().numpy())
        self.image_calls += len(images)
        return np.concatenate(outs) if outs else np.zeros((0, self.manifest.embedding_dimension), np.float32)

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        with self.torch.no_grad():
            t = self.proc(text=texts, return_tensors="pt", padding=True, truncation=True)
            f = self.model.get_text_features(input_ids=t["input_ids"].to(self.device), attention_mask=t["attention_mask"].to(self.device))
            f = getattr(f, "pooler_output", f)
            return self.torch.nn.functional.normalize(f.float(), dim=-1).cpu().numpy()
