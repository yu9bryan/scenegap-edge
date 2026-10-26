"""Candidate formation, condition checks, automatic status, coverage and gap reasons (PRD ch. 8, 13).

Input is an index of analysed assets: per asset, its shots and sampled frames with the original
timestamp, per-query similarity and quality flags. The functions here are pure: no I/O, no model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .logic import AND
from .models import (AutoStatus, CandidateResult, Capability, Constraint, ConstraintResult, Decision, Interval,
                     Requirement, ReviewDecision, Segment, Verdict)

P, F, U = Verdict.PASS, Verdict.FAIL, Verdict.UNKNOWN


@dataclass
class Sample:
    t_ms: int                         # original presentation time in ms
    shot_index: int
    sims: dict[str, float] = field(default_factory=dict)   # query text -> cosine similarity
    blur: bool | None = None          # None = quality not computed
    exposure_clipped: bool | None = None


@dataclass
class AssetIndex:
    asset_id: str
    sha256: str
    capture_id: str
    status: str                       # analyzed | pending | analyzing | failed | missing | excluded
    duration_ms: int
    shots: list[Interval] = field(default_factory=list)
    samples: list[Sample] = field(default_factory=list)   # sorted by t_ms


@dataclass
class RequirementOutcome:
    requirement: Requirement
    status: AutoStatus | str
    candidates: list[CandidateResult]
    reasons: list[str]
    scope_complete: bool


def _semantic_queries(req: Requirement) -> list[str]:
    for c in req.constraints:
        if c.kind == "co_occur":
            return list(c.params["queries"])
    for c in req.constraints:
        if c.kind == "semantic":
            return [c.params.get("query", req.query_en)]
    return [req.query_en]


def _runs(asset: AssetIndex, queries: list[str], tau: float) -> list[tuple[int, int, int, list[Sample]]]:
    """Consecutive passing samples inside one shot. Returns (shot, first_idx, last_idx, samples)."""
    out, cur = [], []
    for i, s in enumerate(asset.samples):
        ok = all(s.sims.get(q, -1.0) >= tau for q in queries)   # co-occurrence: all queries in the same frame
        if ok and cur and cur[-1][1].shot_index == s.shot_index:
            cur.append((i, s))
            continue
        if cur:
            out.append(cur)
        cur = [(i, s)] if ok else []
    if cur:
        out.append(cur)
    return [(r[0][1].shot_index, r[0][0], r[-1][0], [s for _, s in r]) for r in out]


def _bounds(asset: AssetIndex, shot: int, first: int, last: int) -> tuple[int, int, int, int, bool]:
    """Lower bound = span between the first and last passing samples (seen). Upper bound = up to the
    neighbouring non-passing samples or the shot edges (not seen). When both neighbours are failing samples
    the true run is strictly shorter than the upper bound (`strict`). Used for conservative duration checks."""
    sh = asset.shots[shot]
    lo_s, lo_e = asset.samples[first].t_ms, asset.samples[last].t_ms
    left_fail = first > 0 and asset.samples[first - 1].shot_index == shot
    right_fail = last + 1 < len(asset.samples) and asset.samples[last + 1].shot_index == shot
    up_s = asset.samples[first - 1].t_ms if left_fail else sh.start_ms
    up_e = asset.samples[last + 1].t_ms if right_fail else sh.end_ms
    return lo_s, lo_e, max(up_s, sh.start_ms), min(up_e, sh.end_ms), left_fail and right_fail


def check_constraint(c: Constraint, req: Requirement, run_samples: list[Sample], lo: int, up: int, strict: bool = False) -> ConstraintResult:
    if c.capability is not Capability.AUTO:
        why = "需要人工確認" if c.capability is Capability.MANUAL else "此版本不支援自動判定"
        return ConstraintResult(c, U, f"{c.kind}: {why}")
    if c.kind in ("semantic", "co_occur"):
        return ConstraintResult(c, P, "同一時段的語意候選" if c.kind == "co_occur" else "語意候選")
    if c.kind == "duration":
        need = int(c.params.get("min_ms", req.min_duration_ms))
        if lo >= need:
            return ConstraintResult(c, P, f"連續 {lo/1000:.1f} 秒 ≥ {need/1000:.1f} 秒")
        if up < need or (strict and up <= need):
            return ConstraintResult(c, F, f"最多連續 {up/1000:.1f} 秒{'（不含）' if strict else ''}，需求為 {need/1000:.1f} 秒")
        return ConstraintResult(c, U, f"已確認 {lo/1000:.1f} 秒、最多 {up/1000:.1f} 秒；需加密取樣或人工播放")
    if c.kind == "quality":
        flags = [s.blur for s in run_samples]
        if any(f is None for f in flags):
            return ConstraintResult(c, U, "品質未計算")
        frac = sum(bool(f) for f in flags) / max(1, len(flags))
        limit = float(c.params.get("max_blur_fraction", 0.5))
        return ConstraintResult(c, P if frac <= limit else F, f"模糊取樣比例 {frac:.0%}（上限 {limit:.0%}）")
    if c.kind == "takes":
        return ConstraintResult(c, U, "依獨立 take 數另行計算")
    return ConstraintResult(c, U, f"{c.kind}: 未知條件類型")


def candidates_for(req: Requirement, assets: list[AssetIndex], tau: float, top_k: int = 5, per_shot: int = 1) -> list[CandidateResult]:
    queries = _semantic_queries(req)
    found: list[CandidateResult] = []
    for a in assets:
        if a.status != "analyzed":
            continue
        for shot, first, last, run in _runs(a, queries, tau):
            lo_s, lo_e, up_s, up_e, strict = _bounds(a, shot, first, last)
            lo, up = lo_e - lo_s, up_e - up_s
            seg = Segment(a.asset_id, a.sha256, shot, Interval(lo_s, max(lo_e, lo_s + 1)), a.capture_id,
                          score=sum(min(s.sims.get(q, 0.0) for q in queries) for s in run) / len(run))
            cons = [c for c in req.constraints if c.kind != "takes"]
            if req.min_duration_ms and not any(c.kind == "duration" for c in cons):
                cons.append(Constraint("duration", Capability.AUTO, {"min_ms": req.min_duration_ms}))
            results = [check_constraint(c, req, run, lo, up, strict) for c in cons]
            overall = AND(r.verdict for r in results if r.constraint.hard) if results else U
            found.append(CandidateResult(req.requirement_id, req.revision, seg, results, overall))
    # rank: passing first, then score; keep at most `per_shot` per shot so near-duplicate frames do not crowd the list
    order = {P: 0, U: 1, F: 2}
    found.sort(key=lambda c: (order[c.overall], -c.segment.score))
    kept, per = [], {}
    for c in found:
        key = (c.segment.asset_id, c.segment.shot_index)
        if per.get(key, 0) >= per_shot:
            continue
        per[key] = per.get(key, 0) + 1
        kept.append(c)
    return kept[:top_k]


def distinct_takes(cands: list[CandidateResult]) -> int:
    return len({(c.segment.capture_id) for c in cands})


def requirement_status(req: Requirement, assets: list[AssetIndex], cands: list[CandidateResult]) -> RequirementOutcome:
    in_scope = [a for a in assets if a.status != "excluded"]
    pending = [a for a in in_scope if a.status in ("pending", "analyzing")]
    failed = [a for a in in_scope if a.status in ("failed", "missing")]
    analyzed = [a for a in in_scope if a.status == "analyzed"]
    complete = not pending and not failed and bool(analyzed)
    reasons: list[str] = []
    if not req.confirmed:
        return RequirementOutcome(req, "draft", cands, ["NOT_CONFIRMED"], complete)
    if not in_scope:
        return RequirementOutcome(req, AutoStatus.NOT_ANALYZED, [], ["NO_ASSETS"], False)
    if not analyzed:
        if pending:
            st = AutoStatus.ANALYZING if any(a.status == "analyzing" for a in pending) else AutoStatus.NOT_ANALYZED
            return RequirementOutcome(req, st, [], ["NOT_ANALYZED"], False)
        return RequirementOutcome(req, AutoStatus.FAILED, [], ["ANALYSIS_FAILED"], False)
    full = [c for c in cands if c.overall is P]
    if full and distinct_takes(full) >= max(1, req.min_takes):
        if not complete:
            reasons.append("SCOPE_INCOMPLETE")
        return RequirementOutcome(req, AutoStatus.CANDIDATE, cands, reasons, complete)
    if cands:
        for c in cands:
            for r in c.results:
                if r.verdict is F:
                    reasons.append({"duration": "DURATION_SHORT", "quality": "QUALITY_WARNING"}.get(r.constraint.kind, "CONSTRAINT_FAILED"))
                elif r.verdict is U:
                    reasons.append({"duration": "DURATION_UNKNOWN"}.get(r.constraint.kind,
                                   "NEEDS_MANUAL" if r.constraint.capability is Capability.MANUAL else "EVIDENCE_UNKNOWN"))
        if full and distinct_takes(full) < req.min_takes:
            reasons.append("TAKES_SHORT")
        if not complete:
            reasons.append("SCOPE_INCOMPLETE")
        return RequirementOutcome(req, AutoStatus.PARTIAL, cands, sorted(set(reasons)), complete)
    if not complete:
        return RequirementOutcome(req, AutoStatus.UNVERIFIABLE, [], ["NO_CANDIDATE", "SCOPE_INCOMPLETE"], False)
    if any(c.capability is Capability.UNSUPPORTED and c.kind in ("semantic", "co_occur") for c in req.constraints):
        return RequirementOutcome(req, AutoStatus.UNVERIFIABLE, [], ["UNSUPPORTED_CORE"], complete)
    return RequirementOutcome(req, AutoStatus.NOT_FOUND, [], ["NO_CANDIDATE"], complete)


def human_confirmed(req: Requirement, decisions: list[ReviewDecision], asset_shas) -> tuple[bool, bool]:
    """(confirmed, by_exception). Only decisions bound to the current revision and to assets still in scope count.
    Decisions are applied in order: a later decision on the same segment replaces an earlier one, so an accept that
    was later rejected no longer counts. `asset_shas` is a set of in-scope sha256, or a dict sha256 -> capture_id so
    takes are counted by capture the same way as the automatic count."""
    latest: dict[tuple, ReviewDecision] = {}
    for d in decisions:
        if d.requirement_id == req.requirement_id and d.requirement_revision == req.revision and d.asset_sha256 in asset_shas:
            latest[(d.asset_sha256, d.interval.start_ms, d.interval.end_ms)] = d
    valid = [d for d in latest.values() if d.decision in (Decision.ACCEPTED, Decision.OVERRIDDEN)
             and (d.decision is not Decision.OVERRIDDEN or d.reason.strip())]
    cap = asset_shas if isinstance(asset_shas, dict) else {}
    takes = {cap.get(d.asset_sha256, d.asset_sha256) for d in valid}
    ok = len(takes) >= max(1, req.min_takes)
    return ok, ok and any(d.decision is Decision.OVERRIDDEN for d in valid)


@dataclass
class Coverage:
    human_confirmed: float | None     # None = N/A
    ai_candidate: float | None
    analysis_progress: float | None
    denominator_weight: float
    unknown_count: int


def coverage(reqs: list[Requirement], outcomes: dict[str, RequirementOutcome], decisions: list[ReviewDecision],
             assets: list[AssetIndex]) -> Coverage:
    active = [r for r in reqs if r.active_required]
    denom = sum(r.weight for r in active)
    shas = {a.sha256: a.capture_id for a in assets if a.status != "excluded"}
    hc = sum(r.weight for r in active if human_confirmed(r, decisions, shas)[0])
    ai = sum(r.weight for r in active if outcomes.get(r.requirement_id) and outcomes[r.requirement_id].status == AutoStatus.CANDIDATE)
    incl = [a for a in assets if a.status != "excluded"]
    total_ms = sum(a.duration_ms for a in incl)
    done_ms = sum(a.duration_ms for a in incl if a.status == "analyzed")
    unknown = sum(1 for r in active if outcomes.get(r.requirement_id) and outcomes[r.requirement_id].status in
                  (AutoStatus.UNVERIFIABLE, AutoStatus.PARTIAL, AutoStatus.NOT_ANALYZED, AutoStatus.FAILED))
    return Coverage(hc / denom if denom else None, ai / denom if denom else None,
                    done_ms / total_ms if total_ms else None, denom, unknown)
