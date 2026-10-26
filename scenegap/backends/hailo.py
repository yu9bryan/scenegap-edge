"""UGen300 / Hailo-10H device check and backend adapter (FR-HW-01/03/05, PRD 11.4 route A).

Status in this repository: the device check is real; the inference path is NOT implemented because no
UGen300 and no Hailo-10H CLIP HEF were available. `HailoClip` therefore refuses to run instead of
pretending. Nothing here ever reports "NPU active" unless a device answered the scan.
"""
from __future__ import annotations

import shutil
import subprocess


def device_status() -> dict:
    info = {"available": False, "backend": "hailo", "model": None, "interface": None, "driver": None,
            "firmware": None, "runtime": None, "reason": "", "compatibility_verified": False}
    try:
        import hailo_platform as hp            # HailoRT Python package
        info["runtime"] = getattr(hp, "__version__", "unknown")
    except Exception:
        info["reason"] = "未安裝 HailoRT（hailo_platform）"
        hp = None
    cli = shutil.which("hailortcli")
    if hp is not None:
        try:
            ids = hp.Device.scan()
            if ids:
                info.update(available=True, model="Hailo device", interface=str(ids[0]))
            else:
                info["reason"] = "找不到 Hailo 裝置"
        except Exception as e:
            info["reason"] = f"裝置掃描失敗：{e}"
    elif cli:
        try:
            r = subprocess.run([cli, "scan"], capture_output=True, text=True, timeout=10, shell=False)
            if "Device" in r.stdout:
                info.update(available=True, model="Hailo device (hailortcli)", interface=r.stdout.strip().splitlines()[-1])
                info["reason"] = "hailortcli 看得到裝置，但缺 Python 執行環境"
            else:
                info["reason"] = "hailortcli 找不到裝置"
        except Exception as e:
            info["reason"] = f"hailortcli 掃描失敗：{e}"
    return info


class DeviceUnavailable(Exception):
    code = "DEVICE_UNAVAILABLE"


class HailoClip:
    """Placeholder adapter with the same contract as ClipReference. It never fakes output."""
    name = "hailo"

    def __init__(self):
        st = device_status()
        if not st["available"]:
            raise DeviceUnavailable(f"UGen300 not available: {st['reason']}")
        raise DeviceUnavailable("Hailo-10H CLIP HEF and its paired text encoder are not validated yet (PRD G1 gate)")
