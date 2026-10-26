"""Local API, /api/v1 (PRD ch. 17, 20.1, FR-SEC-02).

Defaults: bind 127.0.0.1, per-session token in the X-SG-Token header, Origin must be the UI's own,
media read only by asset_id through authorized roots. Errors use one object:
{code, message, recoverable, stage, asset_id, request_id}; real failures never return 200.
"""
from __future__ import annotations

import io
import json
import os
import re
import secrets
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from ..backends.hailo import device_status
from ..export.report import to_csv, to_html, to_json
from ..service import CODE_VERSION, Conflict, Invalid, SceneGap
from ..store.jobs import JobRunner

WEB = os.path.join(os.path.dirname(__file__), "..", "..", "web")
_STATUS = {"NOT_FOUND": 404, "ROOT_NOT_FOUND": 404, "PATH_NOT_ALLOWED": 403}


MEDIA_PATH = re.compile(r"^/api/v1/assets/[A-Za-z0-9_]+/(media|frame)$")


def err(status: int, code: str, message: str, recoverable=True, stage=None, asset_id=None):
    return JSONResponse({"code": code, "message": message, "recoverable": recoverable, "stage": stage,
                         "asset_id": asset_id, "request_id": uuid.uuid4().hex[:12]}, status_code=status)


class ExcludeIn(BaseModel):
    reason: str


class ProjectIn(BaseModel):
    name: str
    purpose: str = ""
    aspect: str = "16:9"
    target_len_s: float | None = None


class RootIn(BaseModel):
    path: str


class ImportIn(BaseModel):
    root_id: str
    rel_paths: list[str] | None = None


class ReqIn(BaseModel):
    data: dict
    expected_revision: int | None = None


class ReviewIn(BaseModel):
    requirement_id: str
    revision: int
    asset_id: str
    start_ms: int
    end_ms: int
    decision: str
    reason: str = ""
    source: str = "model"


class SearchIn(BaseModel):
    query_en: str
    top_k: int = 10


class StatusIn(BaseModel):
    revision: int
    status: str


def create_app(workdir: str, backend_factory=None, config: dict | None = None, token: str | None = None,
               allowed_origins: set[str] | None = None) -> FastAPI:
    svc = SceneGap(workdir, backend_factory, config)
    runner = JobRunner(svc)
    token = token or secrets.token_urlsafe(24)
    port = os.environ.get("SG_PORT", "8765")
    origins = allowed_origins or {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    hosts = {o.split("://", 1)[1] for o in origins} if allowed_origins is None else None
    app = FastAPI(title="SceneGap Edge", version=CODE_VERSION)
    app.state.svc, app.state.runner, app.state.token = svc, runner, token

    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        host = request.headers.get("host", "")
        if hosts and host not in hosts:                       # DNS-rebinding guard: only the loopback names we bound
            return err(403, "HOST_REJECTED", "unexpected Host header", recoverable=False)
        if path.startswith("/api/v1/") and path != "/api/v1/health":
            origin = request.headers.get("origin")
            if origin and origin not in origins:
                return err(403, "ORIGIN_REJECTED", "cross-origin requests are not allowed", recoverable=False)
            sent = request.headers.get("x-sg-token", "")
            if not sent and request.method == "GET" and MEDIA_PATH.match(path):
                sent = request.cookies.get("sg_media", "")      # <video>/<img> cannot send headers; SameSite=Strict cookie
            if not secrets.compare_digest(sent, token):
                return err(401, "UNAUTHORIZED", "missing or wrong session token", recoverable=False)
        return await call_next(request)

    @app.exception_handler(Invalid)
    async def _inv(request, e: Invalid):
        return err(_STATUS.get(e.code, 422), e.code, str(e))

    @app.exception_handler(Conflict)
    async def _conf(request, e: Conflict):
        return err(409, "STALE_REVISION", str(e))

    @app.get("/api/v1/health")
    def health():
        dev = device_status()
        be = svc._backend
        return {"service": "scenegap-edge", "version": CODE_VERSION, "db": "ok",
                "active_backend": be.name if be else "not loaded", "npu_active": False if not dev["available"] else None,
                "device": {"available": dev["available"], "reason": dev["reason"]}}

    @app.get("/api/v1/device/status")
    def device():
        dev = device_status()
        be = svc._backend
        return {"device": dev, "active_backend": be.name if be else "not loaded",
                "manifest": be.manifest.to_dict() if be else None,
                "note": "NPU results are reported only when a UGen300 answered the scan and a validated HEF ran."}

    @app.get("/api/v1/projects")
    def list_projects():
        return svc.db.all("SELECT * FROM projects ORDER BY created_at DESC")

    @app.post("/api/v1/projects")
    def create_project(p: ProjectIn):
        return {"project_id": svc.create_project(p.name, p.purpose, p.aspect, p.target_len_s)}

    @app.get("/api/v1/projects/{pid}")
    def get_project(pid: str):
        p = svc.project(pid)
        assets = svc.assets(pid)
        return {"project": p, "assets": {s: sum(1 for a in assets if a["status"] == s) for s in
                                         ("pending", "analyzing", "analyzed", "failed", "missing", "excluded")},
                "roots": svc.db.all("SELECT id, path FROM source_roots WHERE project_id=?", (pid,))}

    @app.post("/api/v1/projects/{pid}/roots")
    def add_root(pid: str, r: RootIn):
        svc.project(pid)
        return {"root_id": svc.add_root(pid, r.path)}

    @app.get("/api/v1/projects/{pid}/requirements")
    def list_reqs(pid: str):
        from ..service import req_to_dict
        return [req_to_dict(r) for r in svc.requirements(pid)]

    @app.post("/api/v1/projects/{pid}/requirements")
    def add_req(pid: str, body: ReqIn):
        from ..service import req_to_dict
        return req_to_dict(svc.set_requirement(pid, body.data, None))

    @app.patch("/api/v1/projects/{pid}/requirements/{rid}")
    def patch_req(pid: str, rid: str, body: ReqIn):
        from ..service import req_to_dict
        if body.expected_revision is None:
            return err(422, "SCHEMA", "expected_revision is required for changes")
        return req_to_dict(svc.set_requirement(pid, {**body.data, "requirement_id": rid}, body.expected_revision))

    @app.post("/api/v1/projects/{pid}/assets/import")
    def import_assets(pid: str, body: ImportIn):
        return svc.import_assets(pid, body.root_id, body.rel_paths)

    @app.get("/api/v1/projects/{pid}/assets")
    def list_assets(pid: str):
        svc.project(pid)
        out = []
        for a in svc.assets(pid):
            locs = svc.db.all("SELECT rel_path FROM asset_locations WHERE asset_id=?", (a["asset_id"],))
            out.append({**{k: a[k] for k in ("asset_id", "sha256", "capture_id", "status", "error_code", "error_msg", "duration_ms")},
                        "probe": json.loads(a["probe"]) if a["probe"] else None, "locations": [l["rel_path"] for l in locs]})
        return out

    @app.post("/api/v1/projects/{pid}/analyze", status_code=202)
    def analyze(pid: str):
        svc.project(pid)
        _ = svc.backend                                            # load (and fail early) before queueing
        return {"job_id": runner.submit(pid), "backend": svc.backend.name, "model_fingerprint": svc.backend.manifest.fingerprint}

    def _job_out(j):
        j = dict(j)
        j["payload"] = json.loads(j["payload"] or "{}")
        if j.get("error"):                                         # the traceback stays in the local database
            lines = [x for x in j["error"].strip().splitlines() if x.strip()]
            j["error"] = lines[-1][:300] if lines else "error"
        return j

    @app.get("/api/v1/jobs/{jid}")
    def job(jid: str):
        j = runner.get(jid)
        if not j:
            return err(404, "NOT_FOUND", "job not found")
        return _job_out(j)

    @app.get("/api/v1/projects/{pid}/jobs")
    def jobs(pid: str, active: int = 0):
        svc.project(pid)
        q = "SELECT * FROM jobs WHERE project_id=?" + (" AND state IN ('queued','running')" if active else "") + " ORDER BY created_at DESC LIMIT 50"
        return [_job_out(j) for j in svc.db.all(q, (pid,))]

    @app.get("/api/v1/projects/{pid}/decisions")
    def decisions(pid: str):
        svc.project(pid)
        return svc.db.all("SELECT * FROM decisions WHERE project_id=? ORDER BY ts, rowid", (pid,))

    @app.post("/api/v1/projects/{pid}/assets/{aid}/exclude")
    def exclude(pid: str, aid: str, body: ExcludeIn):
        svc.project(pid)
        if not body.reason.strip():
            return err(422, "REASON_REQUIRED", "excluding an asset needs a reason")
        a = svc.db.one("SELECT project_id FROM assets WHERE asset_id=?", (aid,))
        if not a or a["project_id"] != pid:
            return err(404, "NOT_FOUND", "asset not in this project", asset_id=aid)
        svc.exclude_asset(aid, body.reason)
        return {"asset_id": aid, "status": "excluded"}

    @app.post("/api/v1/jobs/{jid}/cancel")
    def cancel(jid: str):
        runner.cancel(jid)
        return runner.get(jid)

    @app.get("/api/v1/projects/{pid}/coverage")
    def cov(pid: str):
        svc.project(pid)
        return svc.coverage_view(pid)

    @app.post("/api/v1/projects/{pid}/search")
    def search(pid: str, body: SearchIn):
        svc.project(pid)
        tau = svc.tau()
        if tau is None:
            return err(422, "UNCALIBRATED", "semantic threshold not calibrated")
        assets, _ = svc._asset_indexes(pid, [body.query_en])
        hits = []
        for a in assets:
            best = {}
            for s in a.samples:
                v = s.sims.get(body.query_en, -1)
                if v > best.get(s.shot_index, (-9, 0))[0]:
                    best[s.shot_index] = (v, s.t_ms)
            for shot, (v, t) in best.items():
                sh = a.shots[shot]
                hits.append({"asset_id": a.asset_id, "shot": shot, "best_ms": t, "shot_start_ms": sh.start_ms, "shot_end_ms": sh.end_ms,
                             "ranking_score": round(v, 4), "above_threshold": v >= tau})
        hits.sort(key=lambda h: -h["ranking_score"])
        return {"query_en": body.query_en, "results": hits[: body.top_k], "note": "ranking_score is a similarity, not a probability"}

    @app.post("/api/v1/projects/{pid}/review")
    def review(pid: str, body: ReviewIn):
        return {"decision_id": svc.review(pid, body.requirement_id, body.revision, body.asset_id, body.start_ms, body.end_ms,
                                          body.decision, body.reason, body.source)}

    @app.get("/api/v1/projects/{pid}/reshoots")
    def reshoots(pid: str):
        svc.project(pid)
        return svc.reshoot_cards(pid)

    @app.post("/api/v1/projects/{pid}/reshoots/{rid}/status")
    def reshoot_status(pid: str, rid: str, body: StatusIn):
        svc.set_reshoot_status(pid, rid, body.revision, body.status)
        return {"ok": True}

    @app.get("/api/v1/projects/{pid}/exports/{fmt}")
    def export(pid: str, fmt: str):
        p = svc.project(pid)
        view, cards = svc.coverage_view(pid), svc.reshoot_cards(pid)
        if fmt == "json":
            return Response(to_json(view, cards, p, device_status()), media_type="application/json")
        if fmt == "csv":
            return Response("﻿" + to_csv(view), media_type="text/csv; charset=utf-8",
                            headers={"Content-Disposition": f'attachment; filename="scenegap_{pid}.csv"'})
        if fmt == "html":
            return HTMLResponse(to_html(view, cards, p, _thumbs(view)))
        return err(422, "SCHEMA", "format must be json, csv or html")

    def _thumbs(view):
        import base64
        from ..shots.analyze import frames_at
        out = {}
        for row in view.get("requirements", []):
            c = ((row.get("auto") or {}).get("candidates") or [None])[0]
            if c and c["asset_id"] not in out:
                path = svc.asset_path(c["asset_id"])
                fr = frames_at(path, [c["start_ms"]], 0, 120) if path else []
                if fr:
                    buf = io.BytesIO()
                    fr[0].image.save(buf, "JPEG", quality=70)
                    out[c["asset_id"]] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        return out

    @app.get("/api/v1/assets/{aid}/media")
    def media(aid: str):
        a = svc.db.one("SELECT * FROM assets WHERE asset_id=?", (aid,))
        path = svc.asset_path(aid) if a else None
        if not path:
            return err(404, "ASSET_MISSING", "asset not found or offline", asset_id=aid)
        return FileResponse(path, media_type="video/mp4")             # Starlette serves HTTP Range requests

    @app.get("/api/v1/assets/{aid}/frame")
    def frame(aid: str, t_ms: int):
        from ..shots.analyze import frames_at
        a = svc.db.one("SELECT * FROM assets WHERE asset_id=?", (aid,))
        path = svc.asset_path(aid) if a else None
        if not path:
            return err(404, "ASSET_MISSING", "asset not found or offline", asset_id=aid)
        rot = json.loads(a["probe"])["rotation"] if a["probe"] else 0
        fr = frames_at(path, [t_ms], rot, 360)
        if not fr:
            return err(404, "NO_FRAME", "no frame at that time", asset_id=aid)
        buf = io.BytesIO()
        fr[0].image.save(buf, "JPEG", quality=82)
        return Response(buf.getvalue(), media_type="image/jpeg")

    @app.get("/")
    def index():
        page = open(os.path.join(WEB, "index.html"), encoding="utf8").read()
        resp = HTMLResponse(page.replace("__SG_TOKEN__", token))
        resp.set_cookie("sg_media", token, httponly=True, samesite="strict", path="/api/v1/assets")
        return resp

    @app.get("/static/{name}")
    def static(name: str):
        if name not in {"app.js", "style.css"}:
            return err(404, "NOT_FOUND", "no such file")
        return FileResponse(os.path.join(WEB, name))

    return app
