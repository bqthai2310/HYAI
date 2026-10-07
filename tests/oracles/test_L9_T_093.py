from hyai.portfolio import PortfolioKernel
from ._f03_support import product, program, task, workstream
from ._support import oracle
def test_l9_t_093():
    oracle("L9-REQ-PRD-002", "L9-T-093", lambda: PortfolioKernel().validate_hierarchy({"goal_id":"goal_demo"},[product()],[program()],[workstream()],[task()]), lambda: False)
