"""Application service: projects, requirements, import, incremental analysis, run snapshots, review, reshoot.

Every analysis result is a snapshot bound to requirement revisions, model fingerprint, config and asset
scope (PRD 16.3, FR-PRJ-02). Requirement edits make the old snapshot `outdated`; they never keep a stale
green light. Original media are only read (FR-PRJ-05).
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import threading
import time
from dataclasses import asdict

import numpy as np

from .domain.coverage import AssetIndex, Sample, candidates_for, coverage, human_confirmed, requirement_status
from .domain.models import AutoStatus, Capability, Constraint, Decision, Interval, Requirement, ReviewDecision, STATUS_TEXT_ZH, Verdict
from .domain.reshoot import cards
from .media.probe import MediaError, is_stable, probe, sha256_file
from .store.db import DB, atomic_write_bytes, dumps, new_id, now

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".ogv"}
CODE_VERSION = "0.1.0"

DEFAULTS = {
    "sample_every_ms": 1000,      # coarse sampling, then densify candidate windows (PRD 12.2)
    "densify_step_ms": 250,
    "top_k": 5,
    "semantic_threshold": None,   # must be calibrated on the dev split; None refuses to run (PRD 13.4)
    "stable_wait_s": 0.5,
}


class Conflict(Exception):
    code = "STALE_REVISION"


class Invalid(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def req_to_dict(r: Requirement) -> dict:
    d = asdict(r)
    for c in d["constraints"]:
        c["capability"] = c["capability"].value if hasattr(c["capability"], "value") else c["capability"]
    return d


def req_from_dict(d: dict) -> Requirement:
    d = dict(d)
    cons = [Constraint(kind=c["kind"], capability=Capability(c.get("capability", "auto")), params=c.get("params", {}),
                       hard=c.get("hard", True), note=c.get("note", "")) for c in d.pop("constraints", [])]
    return Requirement(constraints=cons, **{k: v for k, v in d.items() if k in Requirement.__dataclass_fields__})


class SceneGap:
    def __init__(self, workdir: str, backend_factory=None, config: dict | None = None):
        self.workdir = os.path.abspath(workdir)
        self.db = DB(os.path.join(self.workdir, "scenegap.db"))
        self.cache = os.path.join(self.workdir, "cache")
        self.cfg = {**DEFAULTS, **(config or {})}
        self._backend_factory = backend_factory
        self._backend = None
        self._lock = threading.Lock()
        self.cancel_flags: set[str] = set()

    # ---------- backend ----------
    @property
    def backend(self):
        with self._lock:
            if self._backend is None:
                if self._backend_factory is None:
                    from .backends.cpu_clip import ClipReference
                    self._backend = ClipReference()
                else:
                    self._backend = self._backend_factory()
            return self._backend

    def config_hash(self) -> str:
        keep = {k: self.cfg[k] for k in ("sample_every_ms", "densify_step_ms", "top_k", "semantic_threshold")}
        return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:12]

    # ---------- projects and requirements ----------
    def create_project(self, name: str, purpose: str = "", aspect: str = "16:9", target_len_s: float | None = None, language: str = "zh-TW") -> str:
        pid = new_id("p")
        self.db.x("INSERT INTO projects VALUES(?,?,?,?,?,?,?)", (pid, name, purpose, aspect, target_len_s, language, now()))
        return pid

    def project(self, pid: str) -> dict:
        p = self.db.one("SELECT * FROM projects WHERE id=?", (pid,))
        if not p:
            raise Invalid("NOT_FOUND", "project not found")
        return p

    def add_root(self, pid: str, path: str) -> str:
        if not os.path.isdir(path):
            raise Invalid("ROOT_NOT_FOUND", "source root is not a directory")
        rid = new_id("r")
        self.db.x("INSERT INTO source_roots VALUES(?,?,?)", (rid, pid, os.path.realpath(path)))
        return rid

    def requirements(self, pid: str) -> list[Requirement]:
        rows = self.db.all("""SELECT r.data FROM requirements r JOIN (SELECT requirement_id, MAX(revision) mr FROM requirements
                              WHERE project_id=? GROUP BY requirement_id) m ON r.requirement_id=m.requirement_id AND r.revision=m.mr
                              WHERE r.project_id=? ORDER BY r.requirement_id""", (pid, pid))
        return [req_from_dict(json.loads(r["data"])) for r in rows]

    def set_requirement(self, pid: str, data: dict, expected_revision: int | None = None) -> Requirement:
        """Create or revise. A changed requirement gets a new revision; a stale expected_revision is a 409 (TC-036)."""
        self.project(pid)
        rid = data["requirement_id"]
        cur = self.db.one("SELECT MAX(revision) rev FROM requirements WHERE project_id=? AND requirement_id=?", (pid, rid))["rev"]
        if cur is not None and expected_revision is not None and expected_revision != cur:
            raise Conflict(f"{rid}: expected revision {expected_revision}, current is {cur}")
        if cur is not None and expected_revision is None:
            raise Conflict(f"{rid}: requirement exists; send expected_revision={cur}")
        if not str(data.get("query_en", "")).strip():
            raise Invalid("SCHEMA", "query_en (confirmed English retrieval text) is required")
        new = req_from_dict({**data, "revision": (cur or 0) + 1})
        if cur is not None:
            old = [r for r in self.requirements(pid) if r.requirement_id == rid][0]
            if req_to_dict(old) | {"revision": 0} == req_to_dict(new) | {"revision": 0}:
                return old                                     # unchanged: no new revision
        self.db.x("INSERT INTO requirements VALUES(?,?,?,?,?)", (pid, rid, new.revision, dumps(req_to_dict(new)), now()))
        return new

    # ---------- import ----------
    def _resolve(self, root_id: str, rel: str) -> str:
        root = self.db.one("SELECT * FROM source_roots WHERE id=?", (root_id,))
        if not root:
            raise Invalid("ROOT_NOT_FOUND", "unknown source root")
        if os.path.isabs(rel) or rel.startswith(("\\", "/")) or ".." in rel.replace("\\", "/").split("/"):
            raise Invalid("PATH_NOT_ALLOWED", "paths must be relative to an authorized source root")
        full = os.path.realpath(os.path.join(root["path"], rel))
        if os.path.commonpath([full, root["path"]]) != root["path"]:
            raise Invalid("PATH_NOT_ALLOWED", "path escapes the authorized source root")
        return full

    def import_assets(self, pid: str, root_id: str, rel_paths: list[str] | None = None) -> dict:
        self.project(pid)
        root = self.db.one("SELECT * FROM source_roots WHERE id=? AND project_id=?", (root_id, pid))
        if not root:
            raise Invalid("ROOT_NOT_FOUND", "source root not authorized for this project")
        if rel_paths is None:
            rel_paths = []
            for dp, _, fns in os.walk(root["path"]):
                for fn in sorted(fns):
                    if os.path.splitext(fn)[1].lower() in VIDEO_EXT:
                        rel_paths.append(os.path.relpath(os.path.join(dp, fn), root["path"]))
        accepted, rejected = [], []
        for rel in rel_paths:
            try:
                full = self._resolve(root_id, rel)
            except Invalid as e:
                rejected.append({"path": rel, "code": e.code, "message": str(e)})
                continue
            if not os.path.isfile(full):
                rejected.append({"path": rel, "code": "ASSET_MISSING", "message": "file not found"})
                continue
            if not is_stable(full, self.cfg["stable_wait_s"]):
                rejected.append({"path": rel, "code": "FILE_UNSTABLE", "message": "file still changing or empty; retry when copying ends"})
                continue
            sha = sha256_file(full)
            ex = self.db.one("SELECT asset_id FROM assets WHERE project_id=? AND sha256=?", (pid, sha))
            if ex:                                              # same content: one logical asset, another location
                self.db.x("INSERT OR IGNORE INTO asset_locations VALUES(?,?,?,?)", (ex["asset_id"], root_id, rel, "ok"))
                accepted.append({"path": rel, "asset_id": ex["asset_id"], "duplicate_of": ex["asset_id"]})
                continue
            aid = "a_" + sha[:12]
            status, code, msg, pr, dur = "pending", None, None, None, 0
            try:
                pr = probe(full)
                dur = pr.duration_ms
                if not pr.supported:
                    status, code, msg = "failed", "UNSUPPORTED_CODEC", pr.unsupported_reason
            except MediaError as e:
                status, code, msg = "failed", e.code, str(e)
            self.db.tx([("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (aid, pid, sha, sha[:12], dumps(pr.to_dict()) if pr else None, status, code, msg, dur, now())),
                        ("INSERT OR IGNORE INTO asset_locations VALUES(?,?,?,?)", (aid, root_id, rel, "ok"))])
            accepted.append({"path": rel, "asset_id": aid, "status": status, "error_code": code})
        return {"accepted": accepted, "rejected": rejected}

    def assets(self, pid: str) -> list[dict]:
        return self.db.all("SELECT * FROM assets WHERE project_id=? ORDER BY created_at, asset_id", (pid,))

    def asset_path(self, asset_id: str) -> str | None:
        for loc in self.db.all("SELECT l.*, r.path root FROM asset_locations l JOIN source_roots r ON r.id=l.root_id WHERE asset_id=?", (asset_id,)):
            p = os.path.join(loc["root"], loc["rel_path"])
            if os.path.isfile(p):
                return p
        return None

    def set_capture(self, asset_id: str, capture_id: str):
        self.db.x("UPDATE assets SET capture_id=? WHERE asset_id=?", (capture_id, asset_id))

    def exclude_asset(self, asset_id: str, reason: str):
        if not reason.strip():
            raise Invalid("REASON_REQUIRED", "excluding an asset needs a reason")
        self.db.x("UPDATE assets SET status='excluded', error_msg=? WHERE asset_id=?", (reason, asset_id))

    # ---------- analysis ----------
    def _index_path(self, sha: str) -> str:
        fp = self.backend.manifest.fingerprint
        return os.path.join(self.cache, fp, f"{sha}_{self.cfg['sample_every_ms']}.npz")

    def _save_index(self, sha, shots, frames, emb, extra=None):
        buf = io.BytesIO()
        np.savez_compressed(buf, t_ms=np.array([f.t_ms for f in frames], np.int64), pts=np.array([f.pts for f in frames], np.int64),
                            shot=np.array([f.shot_index for f in frames], np.int32),
                            blur=np.array([-1 if f.blur is None else int(f.blur) for f in frames], np.int8),
                            clipped=np.array([-1 if f.exposure_clipped is None else int(f.exposure_clipped) for f in frames], np.int8),
                            emb=emb.astype(np.float16), shots=np.array(shots, np.int64),
                            meta=np.array(dumps({"fingerprint": self.backend.manifest.fingerprint, "backend": self.backend.name, **(extra or {})})))
        atomic_write_bytes(self._index_path(sha), buf.getvalue())

    def _load_index(self, sha):
        p = self._index_path(sha)
        if not os.path.exists(p):
            return None
        z = np.load(p, allow_pickle=False)
        meta = json.loads(str(z["meta"]))
        if meta["fingerprint"] != self.backend.manifest.fingerprint:
            return None                                       # never mix model versions in one index (TC-030)
        return z, meta

    def analyze_assets(self, pid: str, job_id: str | None = None) -> dict:
        from .shots.analyze import analyze
        todo = [a for a in self.assets(pid) if a["status"] in ("pending", "analyzing") or
                (a["status"] == "analyzed" and self._load_index(a["sha256"]) is None)]
        done, failed = 0, 0
        for a in todo:
            if job_id and job_id in self.cancel_flags:
                break
            path = self.asset_path(a["asset_id"])
            if not path:
                self.db.x("UPDATE assets SET status='missing', error_code='ASSET_MISSING' WHERE asset_id=?", (a["asset_id"],))
                failed += 1
                continue
            self.db.x("UPDATE assets SET status='analyzing' WHERE asset_id=?", (a["asset_id"],))
            try:
                rot = json.loads(a["probe"])["rotation"] if a["probe"] else 0
                t0 = time.perf_counter()
                shots, frames, st = analyze(path, rot, self.cfg["sample_every_ms"])
                t1 = time.perf_counter()
                emb = self.backend.encode_images([f.image for f in frames])
                t2 = time.perf_counter()
                self._save_index(a["sha256"], shots, frames, emb, {"decode": st, "decode_sample_s": round(t1 - t0, 3),
                                                                   "embed_s": round(t2 - t1, 3), "backend_at_index": self.backend.name})
                self.db.x("UPDATE assets SET status='analyzed', error_code=NULL, error_msg=NULL WHERE asset_id=?", (a["asset_id"],))
                done += 1
            except Exception as e:                               # one bad file never sinks the project (FR-ING-06)
                self.db.x("UPDATE assets SET status='failed', error_code='DECODE_FAILED', error_msg=? WHERE asset_id=?", (str(e)[:300], a["asset_id"]))
                failed += 1
            if job_id:
                self.db.x("UPDATE jobs SET done=?, failed=?, updated_at=? WHERE job_id=?", (done, failed, now(), job_id))
        return {"analyzed": done, "failed": failed, "todo": len(todo)}

    def _asset_indexes(self, pid: str, queries: list[str]) -> tuple[list[AssetIndex], dict]:
        from .backends.base import check_pair
        tv = self.backend.encode_texts(queries) if queries else np.zeros((0, 1))
        out, raw = [], {}
        for a in self.assets(pid):
            ai = AssetIndex(a["asset_id"], a["sha256"], a["capture_id"], a["status"], a["duration_ms"] or 0)
            if a["status"] == "analyzed":
                loaded = self._load_index(a["sha256"])
                if loaded is None:
                    ai.status = "pending"
                else:
                    z, meta = loaded
                    check_pair(meta["fingerprint"], self.backend.manifest.fingerprint)
                    emb = z["emb"].astype(np.float32)
                    sims = emb @ tv.T if len(queries) else np.zeros((len(emb), 0))
                    ai.shots = [Interval(int(s), int(e)) for s, e in z["shots"]]
                    ai.samples = [Sample(int(t), int(sh), {q: float(sims[i, j]) for j, q in enumerate(queries)},
                                         None if b < 0 else bool(b), None if c < 0 else bool(c))
                                  for i, (t, sh, b, c) in enumerate(zip(z["t_ms"], z["shot"], z["blur"], z["clipped"]))]
                    raw[a["asset_id"]] = (z, meta)
            out.append(ai)
        return out, raw

    def _densify(self, pid, req, cands, assets):
        """Unknown duration -> sample the candidate window more densely and keep the frames in the index (FR-SEG-03)."""
        from .shots.analyze import frames_at, quality_flags
        changed = False
        for c in cands:
            if not any(r.constraint.kind == "duration" and r.verdict is Verdict.UNKNOWN for r in c.results):
                continue
            a = next(x for x in assets if x.asset_id == c.segment.asset_id)
            sh = a.shots[c.segment.shot_index]
            have = {s.t_ms for s in a.samples}
            step = self.cfg["densify_step_ms"]
            targets = [t for t in range(sh.start_ms, sh.end_ms, step) if all(abs(t - h) > step // 2 for h in have)]
            path = self.asset_path(a.asset_id)
            if not targets or not path:
                continue
            row = self.db.one("SELECT probe FROM assets WHERE asset_id=?", (a.asset_id,))
            rot = json.loads(row["probe"])["rotation"] if row and row["probe"] else 0
            fr = frames_at(path, targets, rot)
            for f in fr:
                f.shot_index = c.segment.shot_index
                f.blur, f.exposure_clipped = quality_flags(f.image)
            if not fr:
                continue
            z, meta = self._load_index(a.sha256)
            emb_new = self.backend.encode_images([f.image for f in fr])
            from .shots.analyze import Frame
            old = [Frame(int(t), int(p), None, int(s), None if b < 0 else bool(b), None if q < 0 else bool(q))
                   for t, p, s, b, q in zip(z["t_ms"], z["pts"], z["shot"], z["blur"], z["clipped"])]
            frames = old + fr
            emb = np.concatenate([z["emb"].astype(np.float32), emb_new])
            order = np.argsort([f.t_ms for f in frames], kind="stable")
            frames = [frames[i] for i in order]
            emb = emb[order]
            self._save_index(a.sha256, [tuple(s) for s in z["shots"]], frames, emb, {**{k: v for k, v in meta.items() if k not in ("fingerprint", "backend")},
                                                                                       "densified": meta.get("densified", 0) + len(fr)})
            changed = True
        return changed

    def compute_run(self, pid: str) -> dict:
        tau = self.cfg["semantic_threshold"]
        if tau is None:
            raise Invalid("UNCALIBRATED", "semantic_threshold is not set; calibrate on the dev split first")
        reqs = self.requirements(pid)
        queries = sorted({q for r in reqs for q in self._queries(r)})
        assets, _ = self._asset_indexes(pid, queries)
        for _ in range(2):                                       # densify once, then recompute
            changed = False
            for r in reqs:
                if r.confirmed:
                    changed |= self._densify(pid, r, candidates_for(r, assets, tau, self.cfg["top_k"]), assets)
            if not changed:
                break
            assets, _ = self._asset_indexes(pid, queries)
        outcomes = {r.requirement_id: requirement_status(r, assets, candidates_for(r, assets, tau, self.cfg["top_k"])) for r in reqs}
        decisions = self.decisions(pid)
        cov = coverage(reqs, outcomes, decisions, assets)
        result = {"outcomes": {k: self._outcome_dict(o) for k, o in outcomes.items()},
                  "coverage": asdict(cov), "tau": tau}
        run_id = new_id("run")
        scope = {a.asset_id: a.status for a in assets}
        self.db.x("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)",
                  (run_id, pid, now(), self.backend.name, self.backend.manifest.fingerprint, self.config_hash(),
                   dumps({r.requirement_id: r.revision for r in reqs}), dumps(scope), dumps(result), CODE_VERSION))
        return {"run_id": run_id, **result}

    @staticmethod
    def _queries(r: Requirement) -> list[str]:
        qs = [r.query_en]
        for c in r.constraints:
            if c.kind == "co_occur":
                qs += list(c.params["queries"])
            if c.kind == "semantic" and c.params.get("query"):
                qs.append(c.params["query"])
        return qs

    @staticmethod
    def _outcome_dict(o) -> dict:
        st = o.status.value if hasattr(o.status, "value") else o.status
        return {"status": st, "status_zh": STATUS_TEXT_ZH.get(st, st), "reasons": o.reasons, "scope_complete": o.scope_complete,
                "revision": o.requirement.revision,
                "candidates": [{"asset_id": c.segment.asset_id, "asset_sha256": c.segment.asset_sha256, "shot": c.segment.shot_index,
                                "start_ms": c.segment.interval.start_ms, "end_ms": c.segment.interval.end_ms,
                                "capture_id": c.segment.capture_id, "ranking_score": round(c.segment.score, 4),
                                "overall": c.overall.value, "source": c.source,
                                "conditions": [{"kind": x.constraint.kind, "verdict": x.verdict.value, "reason": x.reason} for x in c.results]}
                               for c in o.candidates]}

    def latest_run(self, pid: str) -> dict | None:
        r = self.db.one("SELECT * FROM runs WHERE project_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1", (pid,))
        return r

    def coverage_view(self, pid: str) -> dict:
        run = self.latest_run(pid)
        reqs = self.requirements(pid)
        cur_revs = {r.requirement_id: r.revision for r in reqs}
        if not run:
            return {"run": None, "outdated": True, "requirements": [], "coverage": None}
        res = json.loads(run["result"])
        revs = json.loads(run["requirement_revisions"])
        scope = json.loads(run["scope"])
        cur_scope = {a["asset_id"]: a["status"] for a in self.assets(pid)}
        outdated = revs != cur_revs or scope != cur_scope or run["model_fingerprint"] != self.backend.manifest.fingerprint
        decisions = self.decisions(pid)
        shas = {a["sha256"] for a in self.assets(pid) if a["status"] != "excluded"}
        rows = []
        for r in reqs:
            o = res["outcomes"].get(r.requirement_id)
            stale = (o is None) or o["revision"] != r.revision
            hc, exc = human_confirmed(r, decisions, shas)
            rows.append({"requirement": req_to_dict(r), "auto": None if stale else o, "auto_outdated": stale,
                         "human_confirmed": hc, "human_exception": exc})
        # human coverage is live (decisions bound to current revisions); AI coverage only from a current snapshot
        active = [r for r in reqs if r.active_required]
        denom = sum(r.weight for r in active)
        hc_w = sum(r.weight for r in active if human_confirmed(r, decisions, shas)[0])
        cov = dict(res["coverage"])
        cov["human_confirmed"] = hc_w / denom if denom else None
        if outdated:
            cov["ai_candidate"] = None
        return {"run": {k: run[k] for k in ("run_id", "created_at", "backend", "model_fingerprint", "config_hash", "code_version")},
                "outdated": outdated, "requirements": rows, "coverage": cov, "scope": scope}

    # ---------- review ----------
    def decisions(self, pid: str) -> list[ReviewDecision]:
        return [ReviewDecision(d["requirement_id"], d["revision"], d["asset_sha"], Interval(d["start_ms"], d["end_ms"]),
                               Decision(d["decision"]), d["reason"] or "", d["source"], d["actor"], d["ts"])
                for d in self.db.all("SELECT * FROM decisions WHERE project_id=? ORDER BY ts", (pid,))]

    def review(self, pid: str, requirement_id: str, revision: int, asset_id: str, start_ms: int, end_ms: int,
               decision: str, reason: str = "", source: str = "model", actor: str = "local-user") -> str:
        cur = {r.requirement_id: r for r in self.requirements(pid)}.get(requirement_id)
        if not cur:
            raise Invalid("NOT_FOUND", "requirement not found")
        if revision != cur.revision:
            raise Conflict(f"decision targets revision {revision}; current is {cur.revision}")
        a = self.db.one("SELECT * FROM assets WHERE asset_id=? AND project_id=?", (asset_id, pid))
        if not a or a["status"] == "excluded":
            raise Invalid("NOT_FOUND", "asset not in scope")
        if not (0 <= start_ms < end_ms) or (a["duration_ms"] and end_ms > (json.loads(a["probe"]).get("start_ms", 0) if a["probe"] else 0) + a["duration_ms"] + 50):
            raise Invalid("BAD_INTERVAL", "interval must lie inside the asset")
        d = Decision(decision)
        if d is Decision.OVERRIDDEN and not reason.strip():
            raise Invalid("REASON_REQUIRED", "a creative exception needs a reason")
        did = new_id("d")
        self.db.x("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (did, pid, requirement_id, revision, a["sha256"], start_ms, end_ms, d.value, reason, source, actor, now()))
        return did

    def reshoot_cards(self, pid: str) -> list[dict]:
        run = self.latest_run(pid)
        if not run:
            return []
        reqs = {r.requirement_id: r for r in self.requirements(pid)}
        res = json.loads(run["result"])
        shas = {a["sha256"] for a in self.assets(pid) if a["status"] != "excluded"}
        confirmed = {rid for rid, r in reqs.items() if human_confirmed(r, self.decisions(pid), shas)[0]}
        from .domain.coverage import RequirementOutcome
        outs = []
        for rid, o in res["outcomes"].items():
            r = reqs.get(rid)
            if not r or o["revision"] != r.revision:
                continue                                      # stale outcome -> no card until re-analysed
            st = o["status"]
            outs.append(RequirementOutcome(r, AutoStatus(st) if st != "draft" else st, [], o["reasons"], o["scope_complete"]))
        out = []
        for c in cards(outs, confirmed):
            d = c.to_dict()
            best = res["outcomes"][c.requirement_id]["candidates"]
            if best:
                b = best[0]
                d["best_candidate"] = {"asset_id": b["asset_id"], "start_ms": b["start_ms"], "end_ms": b["end_ms"],
                                       "shortfalls": [x["reason"] for x in b["conditions"] if x["verdict"] != "pass"]}
            st = self.db.one("SELECT status FROM reshoot_status WHERE project_id=? AND requirement_id=? AND revision=?",
                             (pid, c.requirement_id, c.requirement_revision))
            d["status"] = st["status"] if st else "proposed"
            out.append(d)
        return out

    def set_reshoot_status(self, pid, requirement_id, revision, status):
        if status not in ("proposed", "confirmed", "shooting", "done", "dismissed"):
            raise Invalid("SCHEMA", "bad status")
        self.db.x("INSERT OR REPLACE INTO reshoot_status VALUES(?,?,?,?)", (pid, requirement_id, revision, status))
