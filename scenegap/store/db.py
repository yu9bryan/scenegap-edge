"""SQLite store (PRD 16). Short transactions only; model inference never holds the database lock.
Vector indexes are rebuildable cache files written atomically; requirements and decisions are not cache."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT, purpose TEXT, aspect TEXT, target_len_s REAL,
  language TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS requirements(project_id TEXT, requirement_id TEXT, revision INTEGER, data TEXT, created_at TEXT,
  PRIMARY KEY(project_id, requirement_id, revision));
CREATE TABLE IF NOT EXISTS source_roots(id TEXT PRIMARY KEY, project_id TEXT, path TEXT);
CREATE TABLE IF NOT EXISTS assets(asset_id TEXT PRIMARY KEY, project_id TEXT, sha256 TEXT, capture_id TEXT, probe TEXT,
  status TEXT, error_code TEXT, error_msg TEXT, duration_ms INTEGER, created_at TEXT, UNIQUE(project_id, sha256));
CREATE TABLE IF NOT EXISTS asset_locations(asset_id TEXT, root_id TEXT, rel_path TEXT, state TEXT, PRIMARY KEY(asset_id, root_id, rel_path));
CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, project_id TEXT, created_at TEXT, backend TEXT, model_fingerprint TEXT,
  config_hash TEXT, requirement_revisions TEXT, scope TEXT, result TEXT, code_version TEXT);
CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY, project_id TEXT, requirement_id TEXT, revision INTEGER, asset_sha TEXT,
  start_ms INTEGER, end_ms INTEGER, decision TEXT, reason TEXT, source TEXT, actor TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY, project_id TEXT, kind TEXT, state TEXT, stage TEXT, done INTEGER,
  total INTEGER, failed INTEGER, error TEXT, payload TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS reshoot_requests(project_id TEXT, requirement_id TEXT, revision INTEGER, reason TEXT, actor TEXT, ts TEXT,
  PRIMARY KEY(project_id, requirement_id, revision));
CREATE TABLE IF NOT EXISTS reshoot_status(project_id TEXT, requirement_id TEXT, revision INTEGER, status TEXT,
  PRIMARY KEY(project_id, requirement_id, revision));
"""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class DB:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        self._lock = threading.RLock()                 # single writer
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def x(self, sql: str, args=()):
        with self._lock:
            return self.conn.execute(sql, args)

    def tx(self, statements: list[tuple[str, tuple]]):
        with self._lock:
            self.conn.execute("BEGIN")
            try:
                for sql, args in statements:
                    self.conn.execute(sql, args)
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def one(self, sql: str, args=()):
        with self._lock:                               # fetch inside the lock: the connection is shared by threads
            r = self.conn.execute(sql, args).fetchone()
        return dict(r) if r else None

    def all(self, sql: str, args=()):
        with self._lock:
            rows = self.conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]


def atomic_write_bytes(path: str, data: bytes):
    """Write then rename, so a half-written index is never read (PRD 16.2, FR-OPS-01)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp-{uuid.uuid4().hex[:6]}"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, sort_keys=True)
