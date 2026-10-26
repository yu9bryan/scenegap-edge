"""Track the top of one bar per frame and report how evenly it moves.
jerk = second difference of the per-frame speed; a smooth ease shows small, steady values, a jump shows a spike."""
import sys, subprocess, numpy as np
FF = r"F:\cg_lora\venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
src, x0, x1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
raw = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", src, "-t", "4.5", "-vf", "format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
fps = float(subprocess.run([FF, "-i", src], capture_output=True, text=True).stderr.split(" fps")[0].rsplit(" ", 1)[-1])
fr = np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920)
col = fr[:, 250:900, x0:x1].mean(axis=2)                       # mean brightness per row in the bar's column
top = np.array([np.argmax(c > 70) if (c > 70).any() else 650 for c in col]) + 250
h = 900 - top                                                  # bar height in pixels (from a fixed baseline)
v = np.diff(h) * fps                                           # px per second
start = np.argmax(h > h.min() + 3)
moving = v[max(start - 2, 0):][:int(2.6 * fps)]
jerk = np.abs(np.diff(moving, 2))
print(f"{src.split('/')[-1]}: {fps:.0f} fps, growth starts at frame {start}")
print(f"  peak speed {moving.max():.0f} px/s at {np.argmax(moving) / fps:.2f} s after start; speed in first 0.15 s: {moving[:max(1,int(0.15*fps))].mean():.0f} px/s")
print(f"  frame-to-frame speed jumps: median {np.median(np.abs(np.diff(moving))):.0f}, max {np.abs(np.diff(moving)).max():.0f} px/s")
print("  height every 0.1 s:", [int(x) for x in h[start:start + int(2.6 * fps):max(1, int(fps / 10))]])
