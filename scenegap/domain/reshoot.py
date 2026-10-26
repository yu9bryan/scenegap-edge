"""Review / reshoot cards (PRD ch. 14, FR-RET-01/02). Template text only: every field comes from the
confirmed requirement or from recorded evidence; nothing new is invented."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .coverage import RequirementOutcome
from .models import AutoStatus, Capability

REASON_ZH = {
    "NO_CANDIDATE": "已分析的素材裡沒找到", "DURATION_SHORT": "長度不夠", "DURATION_UNKNOWN": "長度無法確認",
    "QUALITY_WARNING": "畫面偏模糊", "NEEDS_MANUAL": "有條件要人工確認", "EVIDENCE_UNKNOWN": "片段不足",
    "TAKES_SHORT": "Take 數不夠", "SCOPE_INCOMPLETE": "還有素材沒分析完", "UNSUPPORTED_CORE": "這個版本還不支援此條件",
    "ANALYSIS_FAILED": "分析失敗", "NOT_ANALYZED": "尚未分析", "NO_ASSETS": "還沒加入素材", "CONSTRAINT_FAILED": "條件不符",
    "VERIFIER_NO": "前幾名候選都沒被確認（AI 確認層），可能沒拍到",
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


def cards(outcomes: list[RequirementOutcome], confirmed_ids: set[str], human_requests: dict[str, str] | None = None) -> list[ReshootCard]:
    """human_requests: requirement_id -> reason, for requirements a person sent to reshoot after reviewing candidates."""
    human_requests = human_requests or {}
    out = []
    for o in outcomes:
        r = o.requirement
        if not r.active_required or r.requirement_id in confirmed_ids:
            continue
        requested = r.requirement_id in human_requests
        if o.status == "draft" or (o.status == AutoStatus.CANDIDATE and not requested):
            continue                      # candidates are reviewed in the evidence viewer, not re-shot, unless a person asks
        review_first = o.status != AutoStatus.NOT_FOUND and not requested
        best = None
        if o.candidates:
            c = o.candidates[0]
            best = {"asset_id": c.segment.asset_id, "start_ms": c.segment.interval.start_ms, "end_ms": c.segment.interval.end_ms,
                    "shortfalls": [x.reason for x in c.results if x.verdict.value != "pass"]}
        manual = [c for c in r.constraints if c.capability is not Capability.AUTO]
        comp = "；".join(c.note or c.kind for c in r.constraints if c.kind == "composition") or "依原文"
        props = "；".join(str(c.params.get("props")) for c in r.constraints if c.params.get("props")) or "依原文"
        verify = "補拍後重新匯入，自動比對畫面和長度，再由人看過確認"
        if manual:
            verify += "；" + "、".join(sorted({c.kind for c in manual})) + " 由人確認"
        out.append(ReshootCard(
            requirement_id=r.requirement_id, requirement_revision=r.revision, source_text=r.source_text,
            kind="reshoot_requested" if requested else ("review_first" if review_first else "reshoot_proposed"), review_first=review_first,
            reasons=list(o.reasons) + (["HUMAN_REQUESTED"] if requested else []),
            reasons_zh=[REASON_ZH.get(x, x) for x in o.reasons] + ([f"人工加入補拍：{human_requests[r.requirement_id]}"] if requested else []),
            best_candidate=best,
            min_continuous_s=r.min_duration_ms / 1000,
            handles=next((f"前後各 {c.params['handles_ms']/1000:.1f} 秒" for c in r.constraints if c.params.get("handles_ms")), "未指定"),
            composition=comp, props=props, verify_by=verify))
    out.sort(key=lambda c: (not c.review_first, c.requirement_id))   # review items first (FR-RET-02)
    return out
