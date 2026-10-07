from hyai.constitution.authority import Principal
from hyai.executive import ExecutiveMandateManager, MandateError
from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def _reserved_required():
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build report.", "directive://151", Principal("PO", "po"))
    goal = ingress.compile_goal(raw, "Build report", ["Report exists"], out_of_scope=["Production"])
    try:
        ExecutiveMandateManager().create_mandate(goal, raw, "product_reports", ["implement staging"], [], {"max_duration_seconds": 60}, "staging bundle", 10, "risk_env_default", "budget_env_default", Principal("PO", "po"))
    except MandateError:
        return True
    return False


def test_l9_t_151_po_reservations():
    oracle("L9-REQ-EXE-004", "L9-T-151", _reserved_required, lambda: False)
