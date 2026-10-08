"""Oracle test for L9-REQ-REV-005 / L9-T-135."""
from hyai.assurance.review import ReviewGateway
from ._support import oracle

def _good() -> bool:
    gateway = ReviewGateway()
    # CI green cannot be interpreted as Independent Review PASS
    assert not gateway.is_ci_green_equivalent_to_review_pass("success")
    assert not gateway.is_ci_green_equivalent_to_review_pass("completed")
    return True

def _bad() -> bool:
    return False

def test_l9_t_135():
    oracle("L9-REQ-REV-005", "L9-T-135", _good, _bad)

