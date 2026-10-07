"""Oracle test for L9-REQ-CAP-001 / L9-T-031."""
from hyai.capabilities.resolver import CapabilityRequest, HardcodedModelIdentityError
from ._support import oracle

def _good() -> bool:
    # Task requests abstract capability
    req = CapabilityRequest(task_id="task_1", capability_id="cap_code_analysis")
    assert req.capability_id == "cap_code_analysis"
    # Hardcoded model identity must be rejected
    try:
        CapabilityRequest(task_id="task_2", capability_id="gpt-4o-model")
        return False
    except HardcodedModelIdentityError:
        return True

def _bad() -> bool:
    # Adversarial mutation: hardcoded model identity is permitted
    try:
        CapabilityRequest(task_id="task_bad", capability_id="gpt-4o")
        return True
    except HardcodedModelIdentityError:
        return False

def test_l9_t_031():
    oracle("L9-REQ-CAP-001", "L9-T-031", _good, _bad)
