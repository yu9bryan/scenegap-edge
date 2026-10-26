"""API contract and security (TC-018, TC-020, TC-021, TC-036)."""
import shutil
import time

import pytest
from fastapi.testclient import TestClient

from scenegap.api.app import create_app
from scenegap.export.report import csv_safe, to_html
from tests.conftest import MockColorBackend

TOKEN = "test-token"
H = {"X-SG-Token": TOKEN}


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "work"), MockColorBackend, {"semantic_threshold": 0.95, "stable_wait_s": 0.05}, token=TOKEN)
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        yield c
    app.state.runner.stop()


def test_token_and_origin_required_TC020(client):
    assert client.get("/api/v1/health").status_code == 200                 # health is public
    r = client.post("/api/v1/projects", json={"name": "x"})
    assert r.status_code == 401 and r.json()["code"] == "UNAUTHORIZED"
    r = client.post("/api/v1/projects", json={"name": "x"}, headers={**H, "Origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["code"] == "ORIGIN_REJECTED"
    assert client.post("/api/v1/projects", json={"name": "x"}, headers=H).status_code == 200


def test_device_status_never_claims_npu_TC018(client):
    d = client.get("/api/v1/device/status", headers=H).json()
    if not d["device"]["available"]:
        assert client.get("/api/v1/health").json()["npu_active"] is False
    assert d["active_backend"] in ("not loaded", "mock-test")


def test_end_to_end_api_TC001(client, tmp_path, fixtures_dir):
    media = tmp_path / "m"
    media.mkdir()
    shutil.copy(f"{fixtures_dir}/two_shots.mp4", media / "two_shots.mp4")
    pid = client.post("/api/v1/projects", json={"name": "demo"}, headers=H).json()["project_id"]
    rid = client.post(f"/api/v1/projects/{pid}/roots", json={"path": str(media)}, headers=H).json()["root_id"]
    req = {"requirement_id": "SH-101", "source_text": "紅色字卡 2 秒", "query_en": "red card", "min_duration_ms": 2000,
           "confirmed": True, "constraints": [{"kind": "semantic", "capability": "auto", "params": {"query": "red card"}}]}
    assert client.post(f"/api/v1/projects/{pid}/requirements", json={"data": req}, headers=H).json()["revision"] == 1
    r = client.post(f"/api/v1/projects/{pid}/assets/import", json={"root_id": rid, "rel_paths": ["../x.mp4"]}, headers=H).json()
    assert r["rejected"][0]["code"] == "PATH_NOT_ALLOWED"
    client.post(f"/api/v1/projects/{pid}/assets/import", json={"root_id": rid, "rel_paths": None}, headers=H)
    j = client.post(f"/api/v1/projects/{pid}/analyze", headers=H)
    assert j.status_code == 202
    jid = j.json()["job_id"]
    for _ in range(100):
        st = client.get(f"/api/v1/jobs/{jid}", headers=H).json()
        if st["state"] in ("done", "failed"):
            break
        time.sleep(0.1)
    assert st["state"] == "done", st
    cov = client.get(f"/api/v1/projects/{pid}/coverage", headers=H).json()
    row = cov["requirements"][0]
    assert row["auto"]["status"] == "candidate" and cov["run"]["backend"] == "mock-test"
    c = row["auto"]["candidates"][0]
    bad = client.post(f"/api/v1/projects/{pid}/review", json={"requirement_id": "SH-101", "revision": 3, "asset_id": c["asset_id"],
                                                              "start_ms": c["start_ms"], "end_ms": c["end_ms"], "decision": "accepted"}, headers=H)
    assert bad.status_code == 409 and bad.json()["code"] == "STALE_REVISION"
    ok = client.post(f"/api/v1/projects/{pid}/review", json={"requirement_id": "SH-101", "revision": 1, "asset_id": c["asset_id"],
                                                             "start_ms": c["start_ms"], "end_ms": c["end_ms"], "decision": "accepted"}, headers=H)
    assert ok.status_code == 200
    r409 = client.patch(f"/api/v1/projects/{pid}/requirements/SH-101", json={"data": {**req, "min_duration_ms": 9000}, "expected_revision": 5}, headers=H)
    assert r409.status_code == 409
    media_resp = client.get(f"/api/v1/assets/{c['asset_id']}/media", headers={**H, "Range": "bytes=0-99"})
    assert media_resp.status_code == 206 and len(media_resp.content) == 100
    for fmt in ("json", "csv", "html"):
        assert client.get(f"/api/v1/projects/{pid}/exports/{fmt}", headers=H).status_code == 200


def test_csv_formula_injection_TC021():
    assert csv_safe("=HYPERLINK(\"http://x\")").startswith("'=")
    assert csv_safe("+1") == "'+1" and csv_safe("@SUM(A1)") == "'@SUM(A1)" and csv_safe("咖啡") == "咖啡"


def test_html_report_escapes_text_TC020():
    view = {"run": {"run_id": "r"}, "coverage": {}, "requirements": [{
        "requirement": {"requirement_id": "SH-1", "revision": 1, "source_text": "<script>alert(1)</script>"},
        "auto": {"status_zh": "x", "candidates": [], "reasons": []}, "auto_outdated": False, "human_confirmed": False, "human_exception": False}]}
    html = to_html(view, [], {"name": "<b>p</b>"})
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html and "http" not in html.split("</style>")[1].split("<table>")[0]


def test_dns_rebinding_host_rejected(tmp_path):
    app = create_app(str(tmp_path / "work"), MockColorBackend, {"semantic_threshold": 0.95}, token=TOKEN)
    with TestClient(app, base_url="http://evil.example:8765") as c:
        r = c.get("/api/v1/projects/x", headers={"X-SG-Token": TOKEN})
        assert r.status_code == 403 and r.json()["code"] == "HOST_REJECTED"


def test_media_cookie_projects_list_and_exclude(tmp_path):
    app = create_app(str(tmp_path / "work"), MockColorBackend, {"semantic_threshold": 0.95}, token=TOKEN)
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        assert c.get("/api/v1/assets/a_x/media").status_code == 401           # no header, no cookie
        page = c.get("/")
        assert page.status_code == 200 and "sg_media" in page.headers.get("set-cookie", "")
        assert "samesite=strict" in page.headers["set-cookie"].lower() and "httponly" in page.headers["set-cookie"].lower()
        assert c.get("/api/v1/assets/a_x/media").status_code == 404           # cookie accepted for media only
        assert c.get("/api/v1/projects").status_code == 401                    # cookie is not enough elsewhere
        H = {"X-SG-Token": TOKEN}
        pid = c.post("/api/v1/projects", json={"name": "p"}, headers=H).json()["project_id"]
        assert [p["id"] if "id" in p else p.get("project_id") for p in c.get("/api/v1/projects", headers=H).json()]
        cov = c.get(f"/api/v1/projects/{pid}/coverage", headers=H).json()
        assert cov["run"] is None and cov["coverage"]["human_confirmed"] is None   # no requirements: N/A
        r = c.post(f"/api/v1/projects/{pid}/assets/a_nope/exclude", json={"reason": "x"}, headers=H)
        assert r.status_code == 404
        assert c.get(f"/api/v1/projects/{pid}/jobs?active=1", headers=H).json() == []
