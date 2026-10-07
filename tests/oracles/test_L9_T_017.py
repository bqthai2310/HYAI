from hyai.portfolio import PortfolioKernel
from ._support import oracle
def test_l9_t_017():
    kernel=PortfolioKernel()
    oracle("L9-REQ-PORT-003", "L9-T-017", lambda: kernel.cancel_or_supersede({"task_id":"task_x"}, "CANCEL", reason="obsolete", provenance_ref="decision_1")["lifecycle_provenance"]["writer"] == "PortfolioKernel", lambda: False)
