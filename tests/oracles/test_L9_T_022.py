from hyai.planning import PlanCompiler
from ._f03_support import task
from ._support import oracle
def test_l9_t_022():
    oracle("L9-REQ-PLAN-003", "L9-T-022", lambda: PlanCompiler().check_no_orphans(["REQ-1"],[task()],[{"requirement_ref":"REQ-1","task_ref":"task_demo"}]), lambda: _bad())
def _bad():
    try: PlanCompiler().check_no_orphans(["REQ-1"],[task()],[])
    except ValueError: return False
    return True
