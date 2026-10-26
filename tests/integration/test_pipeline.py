"""Pipeline on synthetic fixtures with the test-only colour backend (TC ids in names).
These prove media handling, state and versioning; they say nothing about visual accuracy."""
import hashlib
import os
import shutil

import pytest

from scenegap.backends.base import ModelMismatch, check_pair
from scenegap.media.probe import probe
from scenegap.service import Conflict, Invalid, SceneGap
from tests.conftest import MockColorBackend

RED = {"requirement_id": "SH-101", "source_text": "紅色字卡，連續 2 秒", "query_en": "red card", "required": True, "weight": 1,
       "min_duration_ms": 2000, "min_takes": 1, "confirmed": True,
       "constraints": [{"kind": "semantic", "capability": "auto", "params": {"query": "red card"}}]}
BLUE = {**RED, "requirement_id": "SH-102", "source_text": "藍天空景 3 秒", "query_en": "blue sky", "min_duration_ms": 3000,
        "constraints": [{"kind": "semantic", "capability": "auto", "params": {"query": "blue sky"}}]}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


@pytest.fixture
def media(tmp_path, fixtures_dir):
    root = tmp_path / "footage"
    root.mkdir()
    for n in ("two_shots.mp4", "plain.mp4", "plain_copy.mp4", "corrupt.mp4", "rotated_90.mp4", "vp9.webm"):
        if os.path.exists(os.path.join(fixtures_dir, n)):
            shutil.copy(os.path.join(fixtures_dir, n), root / n)
    return root


def make(tmp_path, backend=None):
    be = backend or MockColorBackend()
    return SceneGap(str(tmp_path / "work"), lambda: be, {"semantic_threshold": 0.95, "stable_wait_s": 0.05}), be


def test_closed_loop_TC001_and_originals_unchanged_TC024(tmp_path, media):
    before = {p.name: sha(p) for p in media.iterdir()}
    svc, be = make(tmp_path)
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    svc.set_requirement(pid, RED)
    svc.set_requirement(pid, BLUE)
    imp = svc.import_assets(pid, rid, ["two_shots.mp4"])
    assert imp["accepted"][0]["status"] == "pending"
    svc.analyze_assets(pid)
    run = svc.compute_run(pid)
    assert run["outcomes"]["SH-101"]["status"] == "candidate"        # red card 0-3 s
    c = run["outcomes"]["SH-101"]["candidates"][0]
    assert c["start_ms"] == 0 and c["end_ms"] >= 2000 and c["end_ms"] <= 3000
    assert run["outcomes"]["SH-102"]["status"] == "not_found"        # no blue sky anywhere
    view = svc.coverage_view(pid)
    assert view["coverage"]["human_confirmed"] == 0.0 and view["coverage"]["ai_candidate"] == 0.5
    svc.review(pid, "SH-101", 1, c["asset_id"], c["start_ms"], c["end_ms"], "accepted")
    assert svc.coverage_view(pid)["coverage"]["human_confirmed"] == 0.5
    cards = svc.reshoot_cards(pid)
    assert [x["requirement_id"] for x in cards] == ["SH-102"] and cards[0]["kind"] == "reshoot_proposed"
    after = {p.name: sha(p) for p in media.iterdir()}
    assert before == after


def test_requirement_change_marks_outdated_TC010_and_409_TC036(tmp_path, media):
    svc, _ = make(tmp_path)
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    svc.set_requirement(pid, RED)
    svc.import_assets(pid, rid, ["two_shots.mp4"])
    svc.analyze_assets(pid)
    svc.compute_run(pid)
    assert not svc.coverage_view(pid)["outdated"]
    with pytest.raises(Conflict):
        svc.set_requirement(pid, {**RED, "min_duration_ms": 5000}, expected_revision=7)
    svc.set_requirement(pid, {**RED, "min_duration_ms": 5000}, expected_revision=1)
    v = svc.coverage_view(pid)
    assert v["outdated"] and v["requirements"][0]["auto_outdated"] and v["coverage"]["ai_candidate"] is None
    run = svc.compute_run(pid)
    assert run["outcomes"]["SH-101"]["status"] == "partial"          # 3 s of red cannot satisfy 5 s


def test_failed_file_is_not_absence_TC004_and_duplicates_TC013(tmp_path, media):
    svc, _ = make(tmp_path)
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    svc.set_requirement(pid, BLUE)
    imp = svc.import_assets(pid, rid, ["plain.mp4", "plain_copy.mp4", "corrupt.mp4"])
    by = {a["path"]: a for a in imp["accepted"]}
    assert by["plain_copy.mp4"]["duplicate_of"] == by["plain.mp4"]["asset_id"]
    assert by["corrupt.mp4"]["status"] == "failed" and by["corrupt.mp4"]["error_code"] == "DECODE_FAILED"
    assert len(svc.assets(pid)) == 2
    svc.analyze_assets(pid)
    out = svc.compute_run(pid)["outcomes"]["SH-102"]
    assert out["status"] == "unverifiable" and "SCOPE_INCOMPLETE" in out["reasons"]


def test_unsupported_codec_is_reported(tmp_path, media):
    if not (media / "vp9.webm").exists():
        pytest.skip("no vp9 encoder in this ffmpeg")
    svc, _ = make(tmp_path)
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    a = svc.import_assets(pid, rid, ["vp9.webm"])["accepted"][0]
    assert a["status"] == "failed" and a["error_code"] == "UNSUPPORTED_CODEC"


def test_rotation_and_timeline_TC014(fixtures_dir):
    from scenegap.shots.analyze import analyze
    r = probe(os.path.join(fixtures_dir, "rotated_90.mp4"))
    assert r.rotation == 90
    _, frames, _ = analyze(os.path.join(fixtures_dir, "rotated_90.mp4"), r.rotation)
    assert frames[0].image.size[0] < frames[0].image.size[1]           # displayed upright as portrait
    p2997 = probe(os.path.join(fixtures_dir, "ntsc_2997.mp4"))
    _, fr, _ = analyze(os.path.join(fixtures_dir, "ntsc_2997.mp4"), 0)
    assert [f.t_ms for f in fr][:3] == [0, 1001, 2002] and p2997.time_base_den == 30000
    off = probe(os.path.join(fixtures_dir, "start_offset.mp4"))
    _, fr2, _ = analyze(os.path.join(fixtures_dir, "start_offset.mp4"), 0)
    assert off.start_ms == 10000 and fr2[0].t_ms == 10000
    vfr = probe(os.path.join(fixtures_dir, "vfr.mp4"))
    assert vfr.vfr_suspected


def test_incremental_analysis_TC028(tmp_path, media):
    svc, be = make(tmp_path)
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    svc.set_requirement(pid, RED)
    svc.import_assets(pid, rid, ["two_shots.mp4"])
    svc.analyze_assets(pid)
    svc.compute_run(pid)
    calls = be.image_calls
    svc.import_assets(pid, rid, ["plain.mp4"])
    svc.analyze_assets(pid)
    plain_samples = 2
    assert be.image_calls - calls == plain_samples                    # only the new clip was encoded


def test_resume_after_interruption_TC022(tmp_path, media):
    svc, be = make(tmp_path)
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    svc.import_assets(pid, rid, ["two_shots.mp4", "plain.mp4"])
    a = svc.assets(pid)[0]
    svc.db.x("UPDATE assets SET status='analyzing' WHERE asset_id=?", (a["asset_id"],))   # simulated crash mid-file
    svc2 = SceneGap(svc.workdir, lambda: be, svc.cfg)
    stats = svc2.analyze_assets(pid)
    assert stats["analyzed"] == 2 and all(x["status"] == "analyzed" for x in svc2.assets(pid))
    stats2 = svc2.analyze_assets(pid)
    assert stats2["todo"] == 0                                         # nothing re-done, no duplicates


def test_file_still_being_written_TC029(tmp_path, media):
    import threading
    import time
    svc, _ = make(tmp_path)
    svc.cfg["stable_wait_s"] = 0.5
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    target = media / "growing.mp4"
    data = (media / "two_shots.mp4").read_bytes()

    def writer():
        with open(target, "wb") as f:
            for i in range(0, len(data), 4096):
                f.write(data[i:i + 4096])
                f.flush()
                time.sleep(0.01)
    t = threading.Thread(target=writer)
    t.start()
    time.sleep(0.05)
    res = svc.import_assets(pid, rid, ["growing.mp4"])
    t.join()
    assert res["rejected"] and res["rejected"][0]["code"] == "FILE_UNSTABLE"
    assert svc.assets(pid) == []


def test_model_mismatch_TC016_and_cache_invalidation_TC030(tmp_path, media):
    with pytest.raises(ModelMismatch):
        check_pair("abc", "abd")
    svc, be = make(tmp_path)
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    svc.set_requirement(pid, RED)
    svc.import_assets(pid, rid, ["two_shots.mp4"])
    svc.analyze_assets(pid)
    svc.compute_run(pid)
    be2 = MockColorBackend(version="2")
    assert be2.manifest.fingerprint != be.manifest.fingerprint
    svc2 = SceneGap(svc.workdir, lambda: be2, svc.cfg)
    assert svc2.coverage_view(pid)["outdated"]                         # old run belongs to another model
    assert svc2._load_index(svc2.assets(pid)[0]["sha256"]) is None     # old vectors are not mixed in
    svc2.analyze_assets(pid)
    assert be2.image_calls > 0


def test_paths_must_stay_inside_root_TC020(tmp_path, media):
    svc, _ = make(tmp_path)
    pid = svc.create_project("demo")
    rid = svc.add_root(pid, str(media))
    for bad in ("../secret.mp4", "..\\secret.mp4", str(media / "plain.mp4"), "/etc/passwd"):
        res = svc.import_assets(pid, rid, [bad])
        assert res["rejected"][0]["code"] == "PATH_NOT_ALLOWED"


def test_uncalibrated_threshold_refuses(tmp_path):
    svc = SceneGap(str(tmp_path / "w"), MockColorBackend, {"semantic_threshold": None})
    pid = svc.create_project("x")
    with pytest.raises(Invalid):
        svc.compute_run(pid)
