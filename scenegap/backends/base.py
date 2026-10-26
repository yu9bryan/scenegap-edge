"""Inference backend contract (FR-HW-02). CPU reference and Hailo backends share inputs and outputs."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class ModelManifest:
    """PRD 18.3. Unknown values stay None; compatibility_verified is only set by a real device test."""
    model_id: str
    version: str
    purpose: str
    target_arch: str
    interface: str
    input_size: int
    embedding_dimension: int
    paired_text_encoder: str
    preprocess_id: str
    quantization: str
    artifact_sha256: str | None
    license_reference: str
    runtime_version: str
    compatibility_verified: bool = False

    @property
    def fingerprint(self) -> str:
        key = {k: getattr(self, k) for k in ("model_id", "version", "paired_text_encoder", "preprocess_id", "quantization", "embedding_dimension", "artifact_sha256")}
        return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]

    def to_dict(self):
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        return d


class ModelMismatch(Exception):
    code = "MODEL_MISMATCH"


class Backend:
    name = "abstract"           # provenance label written into every run: cpu-reference | cuda-reference | hailo | mock-test
    manifest: ModelManifest
    image_calls = 0             # counts images actually encoded (TC-028: old assets are not re-inferred)

    def encode_images(self, images) -> np.ndarray:
        raise NotImplementedError

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


def check_pair(index_fp: str, text_fp: str):
    """Text and image vectors must come from the same model fingerprint, not just the same dimension (TC-016)."""
    if index_fp != text_fp:
        raise ModelMismatch(f"index fingerprint {index_fp} != text encoder fingerprint {text_fp}")
