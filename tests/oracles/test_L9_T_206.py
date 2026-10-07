"""Oracle test for L9-REQ-INT-005 / L9-T-206."""
from hyai.interoperability.adapter import ExternalDirectWriteForbiddenError, InteropGateway
from ._support import oracle

def _good() -> bool:
    gateway = InteropGateway()
    # External agent attempting direct-write to canonical state must be rejected
    try:
        gateway.execute_external_agent_call(
            agent_id="external_agent_xyz",
            action="direct_db_write",
            is_direct_write=True,
        )
        return False
    except ExternalDirectWriteForbiddenError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_206():
    oracle("L9-REQ-INT-005", "L9-T-206", _good, _bad)
