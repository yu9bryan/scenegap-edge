"""Review / reshoot cards (PRD ch. 14, FR-RET-01/02). Template text only: every field comes from the
confirmed requirement or from recorded evidence; nothing new is invented."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .coverage import RequirementOutcome
from .models import AutoStatus, Capability

REASON_ZH = {
    "NO_CANDIDATE": "已分析範圍內沒有候選", "DURATION_SHORT": "連續時長不足", "DURATION_UNKNOWN": "連續時長未能確認",
    "QUALITY_WARNING": "品質警示（模糊比例偏高）", "NEEDS_MANUAL": "含需人工確認的條件", "EVIDENCE_UNKNOWN": "證據不足",
    "TAKES_SHORT": "獨立 take 數不足", "SCOPE_INCOMPLETE": "仍有素材未分析或失敗", "UNSUPPORTED_CORE": "核心條件此版本不支援",
    "ANALYSIS_FAILED": "分析失敗", "NOT_ANALYZED": "尚未分析", "NO_ASSETS": "尚未加入素材", "CONSTRAINT_FAILED": "條件不符",
}


@dataclass
class ReshootCard:
    requirement_id: str
    requirement_revision: int
    source_text: str
    kind: str                 # review_first | reshoot_proposed
    review_first: bool
    reasons: list[str]
    reasons_zh: list[str]
    best_candidate: dict | None
    min_continuous_s: float
    handles: str
    composition: str
    props: str
    verify_by: str
    status: str = "proposed"  # proposed -> confirmed -> shooting -> done (person changes it)

    def to_dict(self) -> dict:
        return asdict(self)


def cards(outcomes: list[RequirementOutcome], confirmed_ids: set[str]) -> list[ReshootCard]:
    out = []
    for o in outcomes:
        r = o.requirement
        if not r.active_required or r.requirement_id in confirmed_ids:
            continue
        if o.status in ("draft", AutoStatus.CANDIDATE):
            continue                      # candidates are reviewed in the evidence viewer, not re-shot
        review_first = o.status != AutoStatus.NOT_FOUND
        best = None
        if o.candidates:
            c = o.candidates[0]
            best = {"asset_id": c.segment.asset_id, "start_ms": c.segment.interval.start_ms, "end_ms": c.segment.interval.end_ms,
                    "shortfalls": [x.reason for x in c.results if x.verdict.value != "pass"]}
        manual = [c for c in r.constraints if c.capability is not Capability.AUTO]
        comp = "；".join(c.note or c.kind for c in r.constraints if c.kind == "composition") or "依需求原文"
        props = "；".join(str(c.params.get("props")) for c in r.constraints if c.params.get("props")) or "依需求原文"
        verify = "重新匯入後自動比對語意與連續時長，再由人播放確認"
        if manual:
            verify += "；" + "、".join(sorted({c.kind for c in manual})) + " 由人工確認"
        out.append(ReshootCard(
            requirement_id=r.requirement_id, requirement_revision=r.revision, source_text=r.source_text,
            kind="review_first" if review_first else "reshoot_proposed", review_first=review_first,
            reasons=list(o.reasons), reasons_zh=[REASON_ZH.get(x, x) for x in o.reasons], best_candidate=best,
            min_continuous_s=r.min_duration_ms / 1000,
            handles=next((f"前後各 {c.params['handles_ms']/1000:.1f} 秒" for c in r.constraints if c.params.get("handles_ms")), "未指定"),
            composition=comp, props=props, verify_by=verify))
    out.sort(key=lambda c: (not c.review_first, c.requirement_id))   # review items first (FR-RET-02)
    return out
