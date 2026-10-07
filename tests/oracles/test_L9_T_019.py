from hyai.portfolio import PortfolioKernel
from ._support import oracle
def test_l9_t_019():
    oracle("L9-REQ-PORT-005", "L9-T-019", lambda: PortfolioKernel().cancel_or_supersede({"task_id":"task_x"},"SUPERSEDE",reason="changed",provenance_ref="decision",replacement_ref="task_y")["state"] == "SUPERSEDED", lambda: _missing())
def _missing():
    try: PortfolioKernel().cancel_or_supersede({"task_id":"task_x"},"SUPERSEDE",reason="changed",provenance_ref="decision")
    except ValueError: return False
    return True
