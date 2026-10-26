"""Start SceneGap Edge on this computer only.

  python -m scenegap --workdir ./sg_work [--port 8765] [--device cpu|cuda] [--calibration eval/results/calibration.json]

Binds to 127.0.0.1, creates a random session token for this run and prints the local address. The threshold is
read from the dev calibration file (keyed by model fingerprint); without it, analysis is refused (UNCALIBRATED).
"""
from __future__ import annotations

import argparse
import json
import os
import secrets


def main():
    ap = argparse.ArgumentParser(prog="scenegap")
    ap.add_argument("--workdir", default=os.environ.get("SG_WORKDIR", "./sg_work"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("SG_PORT", "8765")))
    ap.add_argument("--device", default=os.environ.get("SG_DEVICE"), help="cpu or cuda (default: cuda when available)")
    ap.add_argument("--calibration", default=os.environ.get("SG_CALIBRATION", "eval/results/calibration.json"))
    ap.add_argument("--host", default="127.0.0.1", help="keep the default; the service is meant for this computer only")
    a = ap.parse_args()
    os.environ["SG_PORT"] = str(a.port)
    import faulthandler
    faulthandler.enable()                                    # a native crash (decoder, driver) prints its Python stack

    from .api.app import create_app
    from .backends.cpu_clip import ClipReference

    cfg, crop = {}, None
    if os.path.exists(a.calibration):
        cal = json.load(open(a.calibration, encoding="utf8"))
        cfg["semantic_threshold"] = {cal["fingerprint"]: cal["chosen"]["tau"]}
        crop = cal.get("crop")
        print(f"threshold {cal['chosen']['tau']} for model {cal['fingerprint']} ({crop}), calibrated on the dev split")
    else:
        print("no calibration file: search and analysis will answer UNCALIBRATED")
    _be = {}

    def factory():
        if "b" not in _be:
            _be["b"] = ClipReference(device=a.device, crop=crop)
        return _be["b"]

    token = secrets.token_urlsafe(24)
    app = create_app(a.workdir, factory, cfg, token=token)
    import threading
    threading.Thread(target=lambda: app.state.svc.backend, daemon=True).start()   # load the model while the page opens
    import uvicorn
    print(f"SceneGap Edge: http://{a.host}:{a.port}/   (workdir {os.path.abspath(a.workdir)})")
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
