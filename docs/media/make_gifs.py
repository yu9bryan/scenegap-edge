"""Cut the README / site GIFs from the live-app screen recordings made by docs/video/record_demo.py.

  python docs/media/make_gifs.py <recordings dir> [out dir] [name ...]

Each GIF is a list of (start_s, end_s, speed) segments from one recording. Speed 1.0 = real time; anything else is
sped up and the caption in README.md says so. ffmpeg comes from $FFMPEG, else imageio-ffmpeg, else PATH.
"""
import os
import shutil
import subprocess
import sys

JOBS = {  # name: (recording, segments, hold last frame s, (width, palette colours, bayer scale))
    "import-analyse": ("06_import", [(7.6, 15.2, 2.0), (16.8, 45.6, 6.0)], 1.2, (960, 192, 4)),
    "coverage-board": ("07_coverage", [(1.5, 15.2, 1.5)], 0.8, (800, 192, 4)),
    "review-reject-accept": ("08_sh05", [(11.9, 16.8, 1.0), (19.4, 20.2, 1.0), (23.0, 24.4, 1.0), (26.1, 28.4, 1.0)],
                             0.6, (768, 128, 5)),
    "reshoot-add": ("09_reshoot", [(7.8, 15.9, 1.0)], 1.0, (960, 192, 4)),
    "new-clip-accept": ("10_new_clip", [(7.8, 16.5, 3.0), (17.6, 22.0, 2.0), (25.8, 31.6, 1.5)], 1.0, (960, 192, 4)),
}
FPS = 12


def ffmpeg():
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


def main():
    rec = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
    for name in sys.argv[3:] or list(JOBS):
        src, segs, hold, (w, colours, bayer) = JOBS[name]
        parts = [f"[0:v]trim={a}:{b},setpts=(PTS-STARTPTS)/{sp},fps={FPS}[s{i}]" for i, (a, b, sp) in enumerate(segs)]
        graph = (";".join(parts) + ";" + "".join(f"[s{i}]" for i in range(len(segs)))
                 + f"concat=n={len(segs)}:v=1:a=0,tpad=stop_mode=clone:stop_duration={hold},"
                 f"scale={w}:-2:flags=lanczos,split[x][y];[x]palettegen=max_colors={colours}:stats_mode=diff[p];"
                 f"[y][p]paletteuse=dither=bayer:bayer_scale={bayer}:diff_mode=rectangle")
        dst = os.path.join(out, name + ".gif")
        subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.join(rec, src + ".mp4"),
                        "-filter_complex", graph, "-loop", "0", dst], check=True)
        dur = sum((b - a) / sp for a, b, sp in segs) + hold
        print(f"{name}: {os.path.getsize(dst) / 1e6:.2f} MB, {dur:.1f} s")


if __name__ == "__main__":
    main()
