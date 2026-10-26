"""Domain rules mapped to PRD acceptance cases (TC ids in each test name)."""
import pytest

from scenegap.domain.coverage import AssetIndex, Sample, candidates_for, coverage, human_confirmed, requirement_status
from scenegap.domain.logic import AND, NOT, OR
from scenegap.domain.models import (AutoStatus, Capability, Constraint, Decision, Interval, Requirement, ReviewDecision,
                                    Verdict)
from scenegap.domain.reshoot import cards

P, F, U = Verdict.PASS, Verdict.FAIL, Verdict.UNKNOWN
Q = "a cup of coffee"


def req(rid="SH-001", rev=1, min_ms=3000, takes=1, cons=None, confirmed=True, weight=1.0):
    return Requirement(rid, rev, "完成飲品近景", Q, True, weight, min_ms, takes,
                       cons if cons is not None else [Constraint("semantic", Capability.AUTO, {"query": Q})], confirmed)


def asset(aid="a1", sims=(), shots=((0, 10000),), status="analyzed", capture=None, step=1000, extra=None):
    samples = []
    for i, v in enumerate(sims):
        t = i * step
        shot = max(k for k, (s, _) in enumerate(shots) if s <= t)
        samples.append(Sample(t, shot, {Q: v, **({k: x[i] for k, x in (extra or {}).items()})}, blur=False))
    return AssetIndex(aid, "sha_" + aid, capture or "cap_" + aid, status, shots[-1][1],
                      [Interval(s, e) for s, e in shots], samples)


def test_three_valued_logic_TC008():
    assert AND([P, P]) is P and AND([P, U]) is U and AND([P, F, U]) is F and AND([]) is U
    assert OR([F, U]) is U and OR([F, P]) is P and OR([F, F]) is F
    assert NOT(P, negative_scope_complete=False) is U and NOT(P, True) is F


def test_interval_half_open_and_validation():
    assert Interval(0, 1000).overlaps(Interval(999, 2000)) and not Interval(0, 1000).overlaps(Interval(1000, 2000))
    with pytest.raises(ValueError):
        Interval(5, 5)


def test_empty_library_is_not_a_gap_TC002():
    o = requirement_status(req(), [], [])
    assert o.status == AutoStatus.NOT_ANALYZED and o.candidates == []


def test_pending_assets_protect_gap_conclusion_TC003():
    a, b = asset("a1", [0.1] * 5), asset("a2", [], status="pending")
    r = req()
    o = requirement_status(r, [a, b], candidates_for(r, [a, b], 0.5))
    assert o.status == AutoStatus.UNVERIFIABLE and "SCOPE_INCOMPLETE" in o.reasons


def test_decode_failure_is_not_absence_TC004():
    a, b = asset("a1", [0.1] * 5), asset("a2", [], status="failed")
    r = req()
    o = requirement_status(r, [a, b], candidates_for(r, [a, b], 0.5))
    assert o.status == AutoStatus.UNVERIFIABLE


def test_similar_but_too_short_is_partial_TC005():
    a = asset("a1", [0.1, 0.9, 0.9, 0.1, 0.1, 0.1])          # 2 passing samples -> at most 2 s, need 3 s
    r = req(min_ms=3000)
    o = requirement_status(r, [a], candidates_for(r, [a], 0.5))
    assert o.status == AutoStatus.PARTIAL and "DURATION_SHORT" in o.reasons


def test_long_enough_run_is_candidate_not_confirmed():
    a = asset("a1", [0.9] * 6)
    r = req(min_ms=3000)
    o = requirement_status(r, [a], candidates_for(r, [a], 0.5))
    assert o.status == AutoStatus.CANDIDATE
    assert not human_confirmed(r, [], {"sha_a1"})[0]          # candidate is not completion


def test_unknown_duration_stays_unknown():
    a = asset("a1", [0.9, 0.9, 0.9, 0.1], shots=((0, 4000),))   # seen 2 s, could be up to 3 s
    r = req(min_ms=2500)
    c = candidates_for(r, [a], 0.5)[0]
    assert c.overall is U


def test_cooccurrence_needs_same_time_TC006():
    B = "two people"
    cons = [Constraint("co_occur", Capability.AUTO, {"queries": [Q, B]})]
    a = asset("a1", [0.9, 0.9, 0.9, 0.1, 0.1, 0.1], extra={B: [0.1, 0.1, 0.1, 0.9, 0.9, 0.9]})
    r = Requirement("SH-009", 1, "兩人同框", Q, True, 1, 2000, 1, cons, True)
    assert candidates_for(r, [a], 0.5) == []
    o = requirement_status(r, [a], [])
    assert o.status == AutoStatus.NOT_FOUND


def test_single_frame_cannot_prove_action_TC007():
    cons = [Constraint("semantic", Capability.AUTO, {"query": Q}), Constraint("action", Capability.MANUAL, {"action": "pouring"})]
    a = asset("a1", [0.9] * 6)
    r = req(cons=cons, min_ms=3000)
    c = candidates_for(r, [a], 0.5)[0]
    assert c.overall is U
    o = requirement_status(r, [a], [c])
    assert o.status == AutoStatus.PARTIAL and "NEEDS_MANUAL" in o.reasons


def test_no_results_no_fake_timecodes_TC009():
    a = asset("a1", [0.1] * 6)
    r = req()
    assert candidates_for(r, [a], 0.5) == []
    assert requirement_status(r, [a], []).status == AutoStatus.NOT_FOUND


def test_revision_change_invalidates_human_confirmation_TC010():
    r1, r2 = req(rev=1), req(rev=2, min_ms=5000)
    d = ReviewDecision("SH-001", 1, "sha_a1", Interval(0, 4000), Decision.ACCEPTED)
    assert human_confirmed(r1, [d], {"sha_a1"})[0]
    assert not human_confirmed(r2, [d], {"sha_a1"})[0]


def test_denominator_keeps_unknowns_TC011():
    r1, r2 = req("SH-001"), req("SH-002")
    a = asset("a1", [0.9] * 6)
    outcomes = {r.requirement_id: requirement_status(r, [a], candidates_for(r, [a], 0.5)) for r in (r1, r2)}
    outcomes["SH-002"].status = AutoStatus.UNVERIFIABLE
    d = ReviewDecision("SH-001", 1, "sha_a1", Interval(0, 4000), Decision.ACCEPTED)
    cov = coverage([r1, r2], outcomes, [d], [a])
    assert cov.human_confirmed == 0.5 and cov.unknown_count == 1


def test_coverage_is_na_without_required_items():
    cov = coverage([req(confirmed=False)], {}, [], [])
    assert cov.human_confirmed is None and cov.ai_candidate is None and cov.analysis_progress is None


def test_two_short_pieces_do_not_add_up_TC012():
    a = asset("a1", [0.9, 0.9, 0.1, 0.9, 0.9, 0.1], shots=((0, 6000),))
    r = req(min_ms=3000)
    cs = candidates_for(r, [a], 0.5, per_shot=5)
    assert len(cs) == 2 and all(c.overall is F for c in cs)


def test_cut_splits_runs():
    a = asset("a1", [0.9] * 6, shots=((0, 3000), (3000, 6000)))
    r = req(min_ms=4000)
    cs = candidates_for(r, [a], 0.5, per_shot=5)
    assert len(cs) == 2 and all(c.segment.interval.duration_ms < 4000 for c in cs)


def test_duplicate_is_not_two_takes_TC013():
    a = asset("a1", [0.9] * 6, capture="same")
    b = asset("a2", [0.9] * 6, capture="same")
    r = req(min_ms=3000, takes=2)
    o = requirement_status(r, [a, b], candidates_for(r, [a, b], 0.5))
    assert o.status == AutoStatus.PARTIAL and "TAKES_SHORT" in o.reasons
    b.capture_id = "other"
    assert requirement_status(r, [a, b], candidates_for(r, [a, b], 0.5)).status == AutoStatus.CANDIDATE


def test_exception_is_traceable_TC025():
    r = req()
    d = ReviewDecision("SH-001", 1, "sha_a1", Interval(0, 1000), Decision.OVERRIDDEN, reason="刻意的短鏡頭")
    ok, exc = human_confirmed(r, [d], {"sha_a1"})
    assert ok and exc
    blank = ReviewDecision("SH-001", 1, "sha_a1", Interval(0, 1000), Decision.OVERRIDDEN, reason=" ")
    assert not human_confirmed(r, [blank], {"sha_a1"})[0]


def test_manual_segment_counts_for_human_only_TC026():
    r = req()
    a = asset("a1", [0.1] * 6)
    out = requirement_status(r, [a], candidates_for(r, [a], 0.5))
    d = ReviewDecision("SH-001", 1, "sha_a1", Interval(1000, 4000), Decision.ACCEPTED, source="manual")
    cov = coverage([r], {"SH-001": out}, [d], [a])
    assert out.status == AutoStatus.NOT_FOUND and cov.human_confirmed == 1.0 and cov.ai_candidate == 0.0


def test_reshoot_cards_only_confirmed_and_review_first_TC027():
    a = asset("a1", [0.1, 0.9, 0.9, 0.1, 0.1, 0.1])
    r_short, r_none, r_draft = req("SH-004", min_ms=3000), req("SH-012", min_ms=5000), req("SH-099", confirmed=False)
    a2 = asset("a2", [0.1] * 6)
    outs = [requirement_status(r_short, [a], candidates_for(r_short, [a], 0.5)),
            requirement_status(r_none, [a2], candidates_for(r_none, [a2], 0.5)),
            requirement_status(r_draft, [a], [])]
    cs = cards(outs, set())
    ids = [c.requirement_id for c in cs]
    assert "SH-099" not in ids
    assert cs[0].requirement_id == "SH-004" and cs[0].review_first          # partial -> review first
    assert [c for c in cs if c.requirement_id == "SH-012"][0].kind == "reshoot_proposed"
    for c in cs:
        assert c.source_text and c.handles == "未指定"                      # nothing invented
