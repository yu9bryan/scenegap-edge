"""Shared fixtures. `MockColorBackend` is a TEST-ONLY backend (name "mock-test"): its vectors are frame colour
statistics, enough to drive the pipeline on synthetic clips. It is never used outside tests (FR-HW-02)."""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from scenegap.backends.base import Backend, ModelManifest  # noqa: E402


class MockColorBackend(Backend):
    name = "mock-test"

    def __init__(self, version="1"):
        self.image_calls = 0
        self.manifest = ModelManifest("mock-color", version, "test only", "cpu", "numpy", 0, 4, "mock-color", "mean-std",
                                      "fp32", None, "test fixture", "numpy", False)

    @staticmethod
    def _vec(img):
        a = np.asarray(img.convert("RGB"), np.float32) / 255.0
        v = np.array([a[..., 0].mean(), a[..., 1].mean(), a[..., 2].mean(), a.std(axis=(0, 1)).mean() * 2], np.float32)
        return v / (np.linalg.norm(v) + 1e-9)

    def encode_images(self, images):
        self.image_calls += len(images)
        return np.stack([self._vec(i) for i in images]) if images else np.zeros((0, 4), np.float32)

    def encode_texts(self, texts):
        table = {"red card": [1, 0, 0, 0], "colorful test pattern": [0.35, 0.35, 0.35, 0.8], "blue sky": [0, 0, 1, 0]}
        out = [np.array(table.get(t, [0.5, 0.5, 0.5, 0.0]), np.float32) for t in texts]
        return np.stack([v / np.linalg.norm(v) for v in out])


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory):
    from scenegap.media.fixtures import ffmpeg_exe, make_all
    if not ffmpeg_exe():
        pytest.skip("ffmpeg not available")
    d = tmp_path_factory.mktemp("fixtures")
    make_all(str(d))
    return str(d)


@pytest.fixture
def mock_backend():
    return MockColorBackend()
