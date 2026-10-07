from hyai.portfolio import PortfolioKernel
from ._support import oracle
def test_l9_t_153():
    oracle("L9-REQ-EXE-006", "L9-T-153", lambda: PortfolioKernel().priority_gate(authority_ok=True,risk_ok=True,dependencies_ok=True,budget_ok=True), lambda: False)
