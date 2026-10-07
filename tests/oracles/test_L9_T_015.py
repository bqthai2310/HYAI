from hyai.portfolio import PortfolioKernel
from ._f03_support import product, program, task, workstream
from ._support import oracle
def test_l9_t_015():
    oracle("L9-REQ-PORT-001", "L9-T-015", lambda: PortfolioKernel().validate_hierarchy({"goal_id":"goal_demo"}, [product()], [program()], [workstream()], [task()]), lambda: _bad())
def _bad():
    try: PortfolioKernel().validate_hierarchy({"goal_id":"goal_demo"}, [product()], [program()], [workstream()], [task(workstream_id="ws_missing")])
    except ValueError: return False
    return True
