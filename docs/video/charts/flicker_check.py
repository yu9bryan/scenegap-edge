"""Frame-to-frame flicker score in a region: high-frequency changes that a smooth camera sway would not cause.
We take |f[t+1] - 2 f[t] + f[t-1]| (second difference) so steady motion cancels and flicker remains."""
import sys, subprocess, numpy as np
FF = r"F:\cg_lora\venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
src, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
W, H = 960, 540
raw = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", src,
                      "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
regions = {"bar bases (y 340-420)": (340, 420), "whole chart (y 120-450)": (120, 450)}
for name, (a, b) in regions.items():
    r = fr[:, a:b, 100:860]
    d2 = np.abs(r[2:] - 2 * r[1:-1] + r[:-2])
    per = (d2 > 25).mean(axis=(1, 2)) * 100        # % of pixels flickering per frame
    print(f"{name}: frames {len(fr)}  mean {per.mean():.3f}%  p95 {np.percentile(per, 95):.3f}%  max {per.max():.3f}%")
