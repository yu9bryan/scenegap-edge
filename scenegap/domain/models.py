"""Domain objects (PRD ch. 8 and 16). Plain dataclasses so the logic has no I/O or model dependency."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class AutoStatus(str, Enum):
    """Automatic status codes (PRD 8.2). Human decisions are stored separately."""
    NOT_ANALYZED = "not_analyzed"
    ANALYZING = "analyzing"
    CANDIDATE = "candidate"
    PARTIAL = "partial"
    NOT_FOUND = "not_found"
    UNVERIFIABLE = "unverifiable"
    FAILED = "failed"


STATUS_TEXT_ZH = {
    "not_analyzed": "尚未分析", "analyzing": "分析中", "candidate": "有候選，待確認", "partial": "部分符合",
    "not_found": "在已分析範圍未找到", "unverifiable": "無法自動確認", "failed": "分析失敗", "draft": "草稿（未確認）",
}


class Capability(str, Enum):
    AUTO = "auto"            # verified automatically by this version
    MANUAL = "manual"        # needs a person; automatic verdict is unknown
    UNSUPPORTED = "unsupported"


class Decision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"   # creative exception accepted by a person, with a reason


@dataclass(frozen=True)
class Interval:
    """Half-open time interval [start_ms, end_ms) on the original media timeline (PRD FR-SEG-02)."""
    start_ms: int
    end_ms: int

    def __post_init__(self):
        if self.end_ms <= self.start_ms:
            raise ValueError(f"empty or inverted interval [{self.start_ms},{self.end_ms})")

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    def overlaps(self, other: "Interval") -> bool:
        return self.start_ms < other.end_ms and other.start_ms < self.end_ms

    def intersect(self, other: "Interval") -> "Interval | None":
        s, e = max(self.start_ms, other.start_ms), min(self.end_ms, other.end_ms)
        return Interval(s, e) if e > s else None


@dataclass
class Constraint:
    """One verifiable condition of a requirement.

    kind: semantic | co_occur | duration | takes | quality | readable_text | action | composition | forbidden
    """
    kind: str
    capability: Capability = Capability.AUTO
    params: dict = field(default_factory=dict)
    hard: bool = True
    note: str = ""


@dataclass
class Requirement:
    requirement_id: str
    revision: int
    source_text: str                 # the user's own wording (Chinese)
    query_en: str                    # English retrieval query confirmed by a person (PRD 6.2, FR-REQ-06)
    required: bool = True
    weight: float = 1.0
    min_duration_ms: int = 0
    min_takes: int = 1
    constraints: list[Constraint] = field(default_factory=list)
    confirmed: bool = False
    excluded_reason: str | None = None

    @property
    def active_required(self) -> bool:
        return self.confirmed and self.required and self.excluded_reason is None


@dataclass
class Segment:
    """A candidate time range inside one shot of one asset."""
    asset_id: str
    asset_sha256: str
    shot_index: int
    interval: Interval
    capture_id: str                  # identifies an independent take; copies share one capture_id
    score: float = 0.0               # ranking_score, not a calibrated probability


@dataclass
class ConstraintResult:
    constraint: Constraint
    verdict: Verdict
    reason: str = ""


@dataclass
class CandidateResult:
    requirement_id: str
    requirement_revision: int
    segment: Segment
    results: list[ConstraintResult]
    overall: Verdict
    source: str = "model"            # "model" or "manual" (FR-REV-02: manual evidence is never counted as a model hit)


@dataclass
class ReviewDecision:
    requirement_id: str
    requirement_revision: int
    asset_sha256: str
    interval: Interval
    decision: Decision
    reason: str = ""
    source: str = "model"            # which candidate source the person reviewed
    actor: str = "local-user"
    timestamp: str = ""
