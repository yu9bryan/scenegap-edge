"""Run the test suite and write the PRD 23 acceptance trace (eval/results/ACCEPTANCE.md).

  python scripts/acceptance.py
A TC id counts as passed only when every test whose name carries it passed in this run. TCs without an automated
test keep an explicit status and reason; nothing is filled in as a default success.
"""
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = {1: "Minimal closed loop", 2: "Empty library cannot claim missing", 3: "Pending assets protect the verdict",
         4: "Decode failure is not absence", 5: "Similar but too short", 6: "Not at the same time is not same frame",
         7: "One frame cannot prove an action", 8: "Unknown is never pass", 9: "Normal empty result",
         10: "Requirement edit invalidates old results", 11: "Denominator keeps unknown requirements",
         12: "Two segments cannot be added up", 13: "Duplicate file is not two takes", 14: "Original timeline and rotation",
         15: "Detector boxes mapped back to the frame", 16: "Incompatible model vectors", 17: "Quantization quality comparison",
         18: "Device unplugged and fallback", 19: "Core flow offline", 20: "Malicious text and paths", 21: "CSV formula injection",
         22: "Interrupted job and recovery", 23: "Disk full", 24: "Originals untouched", 25: "Manual exception traceable",
         26: "Manually found segment", 27: "Reshoot cards are not invented", 28: "New clip does not recompute old ones",
         29: "File still being written", 30: "Model update and cache invalidation", 31: "Report and relocation",
         32: "Search latency under load", 33: "Editing on the same machine", 34: "Accessibility and status understanding",
         35: "Clean environment rebuild", 36: "Validity version conflict"}
OTHER = {15: ("not_applicable", "no object detector in v1 (MODEL_PLAN: planned for Stage II)"),
         17: ("not_run", "needs a real UGen300 run (G1 gate)"),
         32: ("measured", "eval/results/perf.json: p50/p95 over 10,000 segments, text encoded per query (no cached answers)"),
         33: ("proxy", "eval/results/interference.json: playback proxy, not an NLE; UGen300 not_run"),
         34: ("manual_check", "UI uses icon + text for every status (docs/ui_preview); no user test yet"),
         35: ("see clean_env.json", "fresh venv install + test run: eval/results/clean_env.json; GitHub Actions config in .github/workflows")}


def main():
    xml = os.path.join(ROOT, "eval", "results", "pytest.xml")
    os.makedirs(os.path.dirname(xml), exist_ok=True)
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"], cwd=ROOT)
    tests = {}
    for tc in ET.parse(xml).getroot().iter("testcase"):
        ok = not any(ch.tag in ("failure", "error", "skipped") for ch in tc)
        tests[tc.get("classname") + "::" + tc.get("name")] = ok
    rows, total_ok = [], 0
    for n in range(1, 37):
        tag = f"TC{n:03d}"
        hits = {k: v for k, v in tests.items() if re.search(rf"{tag}(?!\d)", k)}
        if hits:
            st = "pass" if all(hits.values()) else "FAIL"
            ev = ", ".join(k.split("::")[-1] for k in hits)
            if n == 18 and st == "pass":                       # only the labelling half is testable without a device
                st, ev = "partial", ev + " (backend label never claims NPU; the unplug-during-run test needs a UGen300)"
        elif n == 35 and os.path.exists(os.path.join(ROOT, "eval", "results", "clean_env.json")):
            import json
            ce = json.load(open(os.path.join(ROOT, "eval", "results", "clean_env.json"), encoding="utf8"))
            st = "pass" if ce["pip_exit"] == 0 and ce["pytest_exit"] == 0 else "FAIL"
            ev = f"fresh venv ({ce['python']}, {ce['os']}) at {ce['run_at']}: {ce['pytest_summary'][0]} (scripts/clean_env.sh)"
        else:
            st, ev = OTHER.get(n, ("not_run", "no automated test yet"))
        total_ok += st == "pass"
        rows.append(f"| TC-{n:03d} | {NAMES[n]} | {st} | {ev} |")
    head = [f"# PRD 23 acceptance trace", "", f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `scripts/acceptance.py`. "
            f"{sum(tests.values())}/{len(tests)} tests passed; {total_ok}/36 TC ids pass by automated test (synthetic fixtures + test-only mock backend for model output).", "",
            "| TC | Scenario | Status | Evidence |", "|---|---|---|---|"]
    open(os.path.join(ROOT, "eval", "results", "ACCEPTANCE.md"), "w", encoding="utf8").write("\n".join(head + rows) + "\n")
    print("\n".join(head + rows))


if __name__ == "__main__":
    main()
