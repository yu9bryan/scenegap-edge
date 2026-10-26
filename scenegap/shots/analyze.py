"""Shot boundaries and layered sampling on original PTS (PRD 12.2, FR-SEG-01/03/05, FR-ANA-03).

One decode pass at low resolution gives every frame's PTS and an HSV histogram; a cut is declared when
the histogram distance jumps. Samples are taken about once per second plus each shot's middle frame,
and `frames_at` re-decodes chosen timestamps when a candidate needs denser checking.
The cut threshold is a starting value checked on fixtures, not a tuned optimum.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CUT_THRESHOLD = 0.45          # Bhattacharyya distance between consecutive HSV histograms
MIN_SHOT_MS = 400
BLUR_LAPLACIAN_VAR = 60.0     # below = blur warning (uncalibrated starting point)
CLIP_FRACTION = 0.40          # share of pixels at the extremes = exposure clipping warning


@dataclass
class Frame:
    t_ms: int
    pts: int
    image: object             # PIL.Image (rotated upright, about 336 px on the short side)
    shot_index: int = 0
    blur: bool | None = None
    exposure_clipped: bool | None = None


def _hist(arr) -> np.ndarray:
    import cv2
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    h = cv2.calcHist([hsv], [0, 1, 2], None, [16, 8, 8], [0, 180, 0, 256, 0, 256])
    return cv2.normalize(h, h).flatten()


def quality_flags(img) -> tuple[bool, bool]:
    import cv2
    g = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, (224, int(224 * g.shape[0] / g.shape[1])))
    blur = float(cv2.Laplacian(g, cv2.CV_64F).var()) < BLUR_LAPLACIAN_VAR
    clipped = float(((g < 6) | (g > 249)).mean()) > CLIP_FRACTION
    return blur, clipped


def _rotate(img, deg):
    # deg = PyAV frame.rotation (counter-clockwise); verified against ffmpeg autorotate
    return img.rotate(deg, expand=True) if deg else img


def analyze(path: str, rotation: int = 0, sample_every_ms: int = 1000, keep_px: int = 336):
    """Return (shots as [(start_ms, end_ms)], sampled Frames, decode stats)."""
    import av
    import cv2
    c = av.open(path)
    s = c.streams.video[0]
    s.thread_type = "AUTO"
    tb = s.time_base
    times, hists, kept = [], [], []
    next_t = None
    try:
        for fr in c.decode(video=0):
            if fr.pts is None:
                continue
            t = int(fr.pts * tb * 1000)
            small = fr.to_ndarray(format="rgb24", width=160, height=90)
            times.append(t)
            hists.append(_hist(small))
            if next_t is None or t >= next_t:
                w, h = fr.width, fr.height
                sc = keep_px / min(w, h)
                img = fr.to_image(width=max(2, int(w * sc) // 2 * 2), height=max(2, int(h * sc) // 2 * 2))
                kept.append(Frame(t, int(fr.pts), _rotate(img, rotation)))
                next_t = (t if next_t is None else next_t) + sample_every_ms
                while next_t <= t:
                    next_t += sample_every_ms
    finally:
        c.close()
    if not times:
        raise RuntimeError("no frames decoded")
    order = np.argsort(times)
    times = [times[i] for i in order]
    hists = [hists[i] for i in order]
    end_ms = times[-1] + (times[-1] - times[-2] if len(times) > 1 else 33)
    cuts = [times[0]]
    for i in range(1, len(times)):
        d = cv2.compareHist(hists[i - 1], hists[i], cv2.HISTCMP_BHATTACHARYYA)
        if d > CUT_THRESHOLD and times[i] - cuts[-1] >= MIN_SHOT_MS:
            cuts.append(times[i])
    shots = [(cuts[k], cuts[k + 1] if k + 1 < len(cuts) else end_ms) for k in range(len(cuts))]
    for f in kept:
        f.shot_index = max(k for k, (a, _) in enumerate(shots) if a <= f.t_ms)
        f.blur, f.exposure_clipped = quality_flags(f.image)
    # representative frame per shot: add the middle frame if no sample falls in that shot
    have = {f.shot_index for f in kept}
    missing = [k for k in range(len(shots)) if k not in have]
    if missing:
        mids = {k: (shots[k][0] + shots[k][1]) // 2 for k in missing}
        for k, fr in zip(missing, frames_at(path, list(mids.values()), rotation, keep_px)):
            fr.shot_index = k
            fr.blur, fr.exposure_clipped = quality_flags(fr.image)
            kept.append(fr)
        kept.sort(key=lambda f: f.t_ms)
    return shots, kept, {"frames_decoded": len(times), "samples": len(kept), "shots": len(shots), "end_ms": end_ms}


def frames_at(path: str, targets_ms: list[int], rotation: int = 0, keep_px: int = 336) -> list[Frame]:
    """First decoded frame at or after each target time (used for densifying candidate windows)."""
    import av
    want = sorted(set(targets_ms))
    out, j = [], 0
    c = av.open(path)
    s = c.streams.video[0]
    tb = s.time_base
    try:
        for fr in c.decode(video=0):
            if fr.pts is None:
                continue
            t = int(fr.pts * tb * 1000)
            while j < len(want) and t >= want[j]:
                w, h = fr.width, fr.height
                sc = keep_px / min(w, h)
                img = fr.to_image(width=max(2, int(w * sc) // 2 * 2), height=max(2, int(h * sc) // 2 * 2))
                out.append(Frame(t, int(fr.pts), _rotate(img, rotation)))
                j += 1
            if j >= len(want):
                break
    finally:
        c.close()
    return out
