"""Resumable job queue (FR-OPS-01). One worker thread = one device user (FR-HW-04).
On start, jobs left 'running' by a crash go back to 'queued'; index files are written atomically and assets
already indexed are skipped, so a restart continues without duplicate candidates."""
from __future__ import annotations

import threading
import time
import traceback

from .db import dumps, new_id, now


class JobRunner:
    def __init__(self, svc):
        self.svc = svc
        self.db = svc.db
        self.db.x("UPDATE jobs SET state='queued', stage='resumed after restart' WHERE state='running'")
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def submit(self, pid: str, kind: str = "analyze", payload: dict | None = None) -> str:
        jid = new_id("job")
        n = len([a for a in self.svc.assets(pid) if a["status"] in ("pending", "analyzing", "analyzed")])
        self.db.x("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (jid, pid, kind, "queued", "queued", 0, n, 0, None, dumps(payload or {}), now(), now()))
        return jid

    def cancel(self, jid: str):
        self.svc.cancel_flags.add(jid)
        self.db.x("UPDATE jobs SET state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END, updated_at=? WHERE job_id=?", (now(), jid))

    def get(self, jid: str):
        return self.db.one("SELECT * FROM jobs WHERE job_id=?", (jid,))

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            j = self.db.one("SELECT * FROM jobs WHERE state='queued' ORDER BY created_at LIMIT 1")
            if not j:
                time.sleep(0.2)
                continue
            jid = j["job_id"]
            self.db.x("UPDATE jobs SET state='running', stage='analyzing assets', updated_at=? WHERE job_id=?", (now(), jid))
            try:
                stats = self.svc.analyze_assets(j["project_id"], jid)
                if jid in self.svc.cancel_flags:
                    self.db.x("UPDATE jobs SET state='cancelled', stage='cancelled by user', updated_at=? WHERE job_id=?", (now(), jid))
                    continue
                self.db.x("UPDATE jobs SET stage='matching requirements', updated_at=? WHERE job_id=?", (now(), jid))
                run = self.svc.compute_run(j["project_id"])
                self.db.x("UPDATE jobs SET state='done', stage=?, payload=?, updated_at=? WHERE job_id=?",
                          ("done", dumps({**stats, "run_id": run["run_id"]}), now(), jid))
            except Exception as e:
                self.db.x("UPDATE jobs SET state='failed', stage='failed', error=?, updated_at=? WHERE job_id=?",
                          (f"{type(e).__name__}: {e}"[:500] + "\n" + traceback.format_exc()[-800:], now(), jid))
