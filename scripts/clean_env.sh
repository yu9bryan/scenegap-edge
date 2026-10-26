#!/usr/bin/env bash
# TC-035: install into a brand-new virtual environment from the public index and run the suite from a fresh copy.
set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)"
TMP="${1:-$(mktemp -d)}"
PY="${PYTHON:-python}"
rm -rf "$TMP"; mkdir -p "$TMP"
git -C "$SRC" archive HEAD | tar -x -C "$TMP/src" 2>/dev/null || { mkdir -p "$TMP/src"; git -C "$SRC" archive HEAD | tar -x -C "$TMP/src"; }
"$PY" -m venv "$TMP/venv"
if [ -x "$TMP/venv/Scripts/python" ]; then VP="$TMP/venv/Scripts/python"; else VP="$TMP/venv/bin/python"; fi
start=$(date +%s)
"$VP" -m pip install -q -r "$TMP/src/requirements-dev.txt" > "$TMP/pip.log" 2>&1; pip_rc=$?
(cd "$TMP/src" && "$VP" -m pytest -q -p no:cacheprovider > "$TMP/pytest.log" 2>&1); test_rc=$?
end=$(date +%s)
"$VP" - "$SRC/eval/results/clean_env.json" "$pip_rc" "$test_rc" "$((end-start))" "$TMP/pytest.log" <<'PYEOF'
import json, platform, subprocess, sys, time
out, pip_rc, test_rc, secs, log = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
tail = open(log, encoding="utf8", errors="replace").read().strip().splitlines()[-1:]
frz = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout.split()
json.dump({"run_at": time.strftime("%Y-%m-%d %H:%M:%S"), "python": platform.python_version(), "os": platform.platform(),
           "pip_exit": pip_rc, "pytest_exit": test_rc, "pytest_summary": tail, "seconds": secs, "packages": frz},
          open(out, "w", encoding="utf8"), indent=1)
print(tail, pip_rc, test_rc)
PYEOF
