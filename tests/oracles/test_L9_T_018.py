from hyai.portfolio import PortfolioKernel
from ._support import oracle
def test_l9_t_018():
    oracle("L9-REQ-PORT-004", "L9-T-018", lambda: PortfolioKernel().priority_gate(authority_ok=True,risk_ok=True,dependencies_ok=True,budget_ok=True), lambda: _blocked())
def _blocked():
    try: PortfolioKernel().priority_gate(authority_ok=False,risk_ok=True,dependencies_ok=True,budget_ok=True)
    except ValueError: return False
    return True
