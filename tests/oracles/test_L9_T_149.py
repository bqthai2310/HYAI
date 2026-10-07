from hyai.constitution.authority import Principal
from hyai.executive import ExecutiveMandateManager, MandateError
from hyai.ingress import NaturalLanguageIngress
from ._support import oracle


def _create(with_exclusions=True):
    ingress = NaturalLanguageIngress(); raw = ingress.capture_raw_directive("Build report.", "directive://149", Principal("PO", "po"))
    goal = ingress.compile_goal(raw, "Build report", ["Report exists"], out_of_scope=["Production"] if with_exclusions else [])
    return ExecutiveMandateManager().create_mandate(goal, raw, "product_reports", ["implement staging"], ["approve release"], {"max_duration_seconds": 60}, "staging bundle", 10, "risk_env_default", "budget_env_default", Principal("PO", "po"))


def test_l9_t_149_complete_versioned_mandate():
    def incomplete_rejected():
        try: _create(False)
        except MandateError: return True
        return False
    oracle("L9-REQ-EXE-002", "L9-T-149", lambda: _create()["revision"] == 1 and bool(_create()["time_ceiling"]), lambda: not incomplete_rejected())
