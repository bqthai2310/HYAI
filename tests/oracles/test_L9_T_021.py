from hyai.planning import PlanCompiler
from ._f03_support import task
from ._support import oracle
def test_l9_t_021():
    oracle("L9-REQ-PLAN-002", "L9-T-021", lambda: PlanCompiler().compile_task(task())["acceptance_contract_ref"] == "acceptance_demo", lambda: _bad())
def _bad():
    value=task(); value.pop("acceptance_contract_ref")
    try: PlanCompiler().compile_task(value)
    except ValueError: return False
    return True
