from hyai.planning import PlanCompiler
from ._f03_support import task
from ._support import oracle
def test_l9_t_020():
    oracle("L9-REQ-PLAN-001", "L9-T-020", lambda: PlanCompiler().compile_task(task())["task_id"] == "task_demo", lambda: _bad())
def _bad():
    value=task(); value["scope"]=[]
    try: PlanCompiler().compile_task(value)
    except ValueError: return False
    return True
