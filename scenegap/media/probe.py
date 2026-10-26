"""Media probing on the original timeline (PRD 12.1, FR-ING-02/03, FR-SEG-02).

PyAV exposes each stream's time_base and every frame's PTS, so times come from PTS, never frame/fps.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass, field

SUPPORTED = {("h264", 8)}            # first-version main path (PRD 6.2): H.264, 8-bit SDR
CONTAINERS = {"mov,mp4,m4a,3gp,3g2,mj2"}


class MediaError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class ProbeResult:
    container: str
    codec: str
    bit_depth: int
    width: int
    height: int
    rotation: int                    # degrees clockwise to display upright
    time_base_num: int
    time_base_den: int
    start_pts: int
    start_ms: int
    duration_ms: int
    avg_fps: float | None
    vfr_suspected: bool
    audio_streams: int
    supported: bool
    unsupported_reason: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def _rotation_from_frame(frame) -> int:
    """Degrees counter-clockwise to display upright (PyAV reads the display matrix per frame).
    Checked against ffmpeg's autorotate on a fixture: PIL `img.rotate(r, expand=True)` matches exactly."""
    try:
        return int(round(frame.rotation or 0)) % 360
    except Exception:
        return 0


def probe(path: str, check_frames: int = 120) -> ProbeResult:
    import av
    if not os.path.isfile(path):
        raise MediaError("ASSET_MISSING", f"file not found: {path}")
    try:
        c = av.open(path)
    except Exception as e:                            # corrupt or not a media file
        raise MediaError("DECODE_FAILED", f"cannot open: {e}") from e
    try:
        vs = [s for s in c.streams if s.type == "video"]
        if not vs:
            raise MediaError("NO_VIDEO_STREAM", "no video stream")
        s = vs[0]
        cc = s.codec_context
        fmt = cc.format.name if cc.format else ""
        depth = 10 if ("10" in fmt or "p010" in fmt) else 12 if "12" in fmt else 8
        tb = s.time_base
        start_pts = s.start_time if s.start_time is not None else 0
        dur = s.duration
        duration_ms = int(dur * tb * 1000) if dur else int((c.duration or 0) / 1000)
        # VFR check on the first frames: spread of PTS deltas
        deltas, last, n, rotation = [], None, 0, 0
        try:
            for fr in c.decode(video=0):
                if n == 0:
                    rotation = _rotation_from_frame(fr)
                if fr.pts is not None:
                    if last is not None:
                        deltas.append(fr.pts - last)
                    last = fr.pts
                n += 1
                if n >= check_frames:
                    break
        except Exception as e:
            raise MediaError("DECODE_FAILED", f"decode error near start: {e}") from e
        if n == 0:
            raise MediaError("DECODE_FAILED", "no decodable frames")
        vfr = bool(deltas) and (max(deltas) - min(deltas)) > max(1, 0.02 * (sum(deltas) / len(deltas)))
        codec = cc.name
        supported = (codec, depth) in SUPPORTED and c.format.name in CONTAINERS
        reason = "" if supported else f"{c.format.name}/{codec}/{depth}-bit is not on the tested path (MP4/MOV, H.264, 8-bit); transcode first"
        warnings = []
        if start_pts:
            warnings.append("non-zero start time")
        if vfr:
            warnings.append("variable frame rate suspected; timestamps use PTS")
        return ProbeResult(container=c.format.name, codec=codec, bit_depth=depth, width=cc.width, height=cc.height,
                           rotation=rotation, time_base_num=tb.numerator, time_base_den=tb.denominator,
                           start_pts=int(start_pts), start_ms=int(start_pts * tb * 1000), duration_ms=duration_ms,
                           avg_fps=float(s.average_rate) if s.average_rate else None, vfr_suspected=vfr,
                           audio_streams=sum(1 for x in c.streams if x.type == "audio"), supported=supported,
                           unsupported_reason=reason, warnings=warnings)
    finally:
        c.close()


def is_stable(path: str, wait_s: float = 1.0) -> bool:
    """A file still being written is not analysed (FR-ING-05, TC-029): size and mtime must hold still."""
    import time
    try:
        a = os.stat(path)
        time.sleep(wait_s)
        b = os.stat(path)
    except OSError:
        return False
    return a.st_size == b.st_size and a.st_mtime == b.st_mtime and a.st_size > 0
