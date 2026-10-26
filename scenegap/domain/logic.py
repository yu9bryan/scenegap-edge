"""Three-valued condition logic (PRD 8.3, FR-MAT-02). Unknown is never treated as pass."""
from __future__ import annotations

from collections.abc import Iterable

from .models import Verdict

P, F, U = Verdict.PASS, Verdict.FAIL, Verdict.UNKNOWN


def AND(verdicts: Iterable[Verdict]) -> Verdict:
    vs = list(verdicts)
    if any(v is F for v in vs):
        return F
    if vs and all(v is P for v in vs):
        return P
    return U                                   # empty AND is unknown, never a silent pass


def OR(verdicts: Iterable[Verdict]) -> Verdict:
    vs = list(verdicts)
    if any(v is P for v in vs):
        return P
    if vs and all(v is F for v in vs):
        return F
    return U


def NOT(verdict: Verdict, negative_scope_complete: bool) -> Verdict:
    """Negation is only decidable when the detector and the scope of negative evidence are adequate."""
    if not negative_scope_complete:
        return U
    return {P: F, F: P, U: U}[verdict]
