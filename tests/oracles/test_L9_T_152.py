from hyai.executive import EscalationController
from ._support import oracle
def test_l9_t_152():
    controller=EscalationController()
    oracle("L9-REQ-EXE-005", "L9-T-152", lambda: not controller.evaluate_escalation(routine=True,reversible=True)["escalate"] and controller.evaluate_escalation(trigger="BUDGET_BREACH")["escalate"], lambda: controller.evaluate_escalation(routine=True,reversible=True)["escalate"])
