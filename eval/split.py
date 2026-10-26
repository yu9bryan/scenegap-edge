"""Dev/test split by uploader group (eval/PROTOCOL.md). Deterministic: hash of the group name with a fixed seed."""
import hashlib

SEED = "scenegap-split-2026-10-26"
DEV_SHARE = 0.40


def group_of(clip: dict) -> str:
    return (clip.get("artist") or clip.get("credit") or clip.get("title") or clip["clip"]).strip().lower()


def split(clips: list[dict]) -> dict[str, str]:
    groups = sorted({group_of(c) for c in clips}, key=lambda g: hashlib.sha256((SEED + g).encode()).hexdigest())
    target = DEV_SHARE * len(clips)
    dev_groups, n = set(), 0
    for g in groups:
        if n >= target:
            break
        dev_groups.add(g)
        n += sum(1 for c in clips if group_of(c) == g)
    return {c["clip"]: ("dev" if group_of(c) in dev_groups else "test") for c in clips}
