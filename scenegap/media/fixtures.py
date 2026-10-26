"""Engineering fixtures (PRD 21.1 tier 1): short synthetic clips for timestamps, cuts, rotation and failures.
They test the media path only; they say nothing about visual accuracy."""
from __future__ import annotations

import os
import shutil
import subprocess


def ffmpeg_exe() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _run(args: list[str]):
    exe = ffmpeg_exe()
    if not exe:
        raise RuntimeError("ffmpeg not found")
    subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y", *args], check=True, timeout=120, shell=False)


H264 = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast"]


def make_all(out_dir: str) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    p = lambda n: os.path.join(out_dir, n)
    # two shots: 3 s red card, then 3 s test pattern -> a cut at 3000 ms
    _run(["-f", "lavfi", "-i", "color=c=red:s=640x360:r=30:d=3", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=3",
          "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", *H264, p("two_shots.mp4")])
    _run(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=30000/1001:d=5", *H264, p("ntsc_2997.mp4")])
    # variable frame rate: 30 fps for 2 s, then 10 fps
    _run(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=4",
          "-vf", "select='lt(n,60)+not(mod(n,3))',setpts=N/FRAME_RATE/TB", "-fps_mode", "vfr", *H264, p("vfr_tmp.mp4")])
    _run(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=4", "-vf", "select='lt(n,60)+not(mod(n,3))'", "-fps_mode", "vfr", *H264, p("vfr.mp4")])
    os.remove(p("vfr_tmp.mp4"))
    _run(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=3", *H264, "-output_ts_offset", "10", p("start_offset.mp4")])
    _run(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=2", *H264, p("plain.mp4")])
    _run(["-display_rotation", "90", "-i", p("plain.mp4"), "-c", "copy", p("rotated_90.mp4")])
    shutil.copyfile(p("plain.mp4"), p("plain_copy.mp4"))                       # same content, other name
    with open(p("plain.mp4"), "rb") as f:
        data = f.read()
    with open(p("corrupt.mp4"), "wb") as f:
        f.write(data[: len(data) // 5])                                         # truncated -> undecodable
    with open(p("not_video.mp4"), "wb") as f:
        f.write(b"this is a text file pretending to be a video\n")
    try:
        _run(["-f", "lavfi", "-i", "testsrc2=s=320x240:r=25:d=2", "-c:v", "libvpx-vp9", "-b:v", "200k", p("vp9.webm")])
    except Exception:
        pass
    return {n: p(n) for n in sorted(os.listdir(out_dir))}


if __name__ == "__main__":
    import sys
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else "fixtures"))
