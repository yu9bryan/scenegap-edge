"""Playback-interference proxy (PRD 24.3), on a desktop, without an NLE.

  python eval/interference.py --mp4 F:/sg_data/commons/mp4 --work F:/sg_data/_interf [--seconds 30] [--rounds 2]

A 1080p30 H.264 clip is decoded and converted to RGB at real-time pace (what a player must do). We count frames
that are ready more than one frame period after their presentation time ("late"), while SceneGap analyses footage
in a separate process: none (baseline), cpu-reference, cuda-reference. Conditions are interleaved over rounds.
This is a proxy for editing interference, not an NLE measurement; UGen300 is not_run.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

WORKER = r"""
import sys, os, time
sys.path.insert(0, {root!r})
from scenegap.service import SceneGap
from scenegap.backends.cpu_clip import ClipReference
be = ClipReference(device={dev!r})
print("ready", flush=True)
n = 0
while True:                                   # one clip per fresh workdir, so every clip is decoded and embedded again
    for clip in {clips!r}:
        work = os.path.join({work!r}, "w%d" % n); n += 1
        svc = SceneGap(work, lambda: be, {{"stable_wait_s": 0.0}})
        pid = svc.create_project("load"); rid = svc.add_root(pid, {mp4!r})
        svc.import_assets(pid, rid, [clip])
        r = svc.analyze_assets(pid)
        print("done", r["analyzed"], flush=True)
"""


def make_playback_clip(path, seconds):
    from scenegap.media.fixtures import ffmpeg_exe
    if os.path.exists(path):
        return
    subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size=1920x1080:rate=30:duration={seconds}", "-c:v", "libx264", "-preset", "medium",
                    "-pix_fmt", "yuv420p", path], check=True)


def playback(path):
    import av
    late, frames, worst, work = 0, 0, -1e9, []
    with av.open(path) as c:
        st = c.streams.video[0]
        period = 1 / float(st.average_rate)
        t0, first = None, None
        it = c.decode(st)
        while True:
            w0 = time.perf_counter()
            try:
                f = next(it)
            except StopIteration:
                break
            f.to_ndarray(format="rgb24")
            work.append((time.perf_counter() - w0) * 1000)
            pts = float(f.pts * st.time_base)
            now = time.perf_counter()
            if t0 is None:
                t0, first = now, pts
            due = t0 + (pts - first)
            lag = now - due
            frames += 1
            worst = max(worst, lag)
            if lag > period:
                late += 1
            elif lag < 0:
                time.sleep(-lag)
    import numpy as np
    return {"frames": frames, "late": late, "late_share": round(late / frames, 4), "worst_lag_ms": round(worst * 1000, 1),
            "frame_work_ms_p50": round(float(np.percentile(work, 50)), 2), "frame_work_ms_p95": round(float(np.percentile(work, 95)), 2),
            "frame_work_ms_max": round(float(max(work)), 2), "budget_ms": round(period * 1000, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp4", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--rounds", type=int, default=2)
    a = ap.parse_args()
    import torch
    os.makedirs(a.work, exist_ok=True)
    clip = os.path.join(a.work, "playback_1080p30.mp4")
    make_playback_clip(clip, a.seconds)
    load = sorted(f for f in os.listdir(a.mp4) if f.endswith(".mp4"))[:8]
    conds = ["none", "cpu"] + (["cuda"] if torch.cuda.is_available() else [])
    rows = []
    for r in range(a.rounds):
        order = conds if r % 2 == 0 else list(reversed(conds))
        for cond in order:
            proc = None
            if cond != "none":
                w = os.path.join(a.work, f"load_{cond}_{r}")
                shutil.rmtree(w, ignore_errors=True)
                code = WORKER.format(root=ROOT, dev=cond, work=w, mp4=a.mp4, clips=load)
                proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                while proc.stdout.readline().strip() != "ready":
                    pass
                done = []
                import threading
                threading.Thread(target=lambda: [done.append(l) for l in proc.stdout], daemon=True).start()
                time.sleep(3)                                     # let the analysis loop get going
            t0 = time.perf_counter()
            res = playback(clip)
            dur = time.perf_counter() - t0
            if proc:
                proc.kill()
                proc.wait()
            rows.append({"round": r, "analysis": cond, **res, "playback_s": round(dur, 1),
                         "load_clips_finished_during_run": sum(int(l.split()[1]) for l in done if l.startswith("done")) if proc else 0})
            print(rows[-1], flush=True)
    summary = {}
    for cond in conds:
        rs = [x for x in rows if x["analysis"] == cond]
        summary[cond] = {"late_share_mean": round(sum(x["late_share"] for x in rs) / len(rs), 4),
                         "worst_lag_ms_max": max(x["worst_lag_ms"] for x in rs),
                         "frame_work_ms_p95_max": max(x["frame_work_ms_p95"] for x in rs),
                         "load_clips_finished": sum(x["load_clips_finished_during_run"] for x in rs)}
    out = {"measured_at": time.strftime("%Y-%m-%d %H:%M:%S"), "playback": "1080p30 H.264, decode + RGB convert at real-time pace",
           "load": f"SceneGap analyse loop over {len(load)} clips in a separate process", "cpu": os.cpu_count(),
           "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "ugen300": "not_run",
           "note": "Proxy for PRD 24.3; not an NLE timeline test.", "rows": rows, "summary": summary}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "results", "interference.json"), "w", encoding="utf8"), indent=1)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
