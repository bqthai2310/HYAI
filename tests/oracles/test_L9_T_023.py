from hyai.planning import PlanCompiler
from ._f03_support import task
from ._support import oracle
def test_l9_t_023():
    oracle("L9-REQ-PLAN-004", "L9-T-023", lambda: PlanCompiler().validate_high_risk_adversarial(task(risk="HIGH"),[{"kind":"ADVERSARIAL"}]), lambda: _bad())
def _bad():
    try: PlanCompiler().validate_high_risk_adversarial(task(risk="HIGH"),[])
    except ValueError: return False
    return True
