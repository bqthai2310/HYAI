from hyai.assurance import ReviewVerdict, can_promote_to_production
from hyai.constitution.authority import Principal
from ._support import oracle

def test_l9_t_042_promotion_separate():
    verdict = ReviewVerdict("r", "a" * 40, {}, Principal("INDEPENDENT_REVIEWER", "i"), "PASS", [])
    oracle("L9-REQ-ASS-006", "L9-T-042", lambda: can_promote_to_production(verdict, Principal("PO", "po")), lambda: can_promote_to_production(verdict, None))
