"""Oracle test for L9-REQ-FED-005 / L9-T-058."""
from hyai.federation.node import FederationManager, create_federation_node
from ._support import oracle

def _good() -> bool:
    mgr = FederationManager()
    node = create_federation_node(node_id="node_failing_sensor")
    mgr.register_node(node)
    quarantined = mgr.quarantine_node("node_failing_sensor", reason="Consecutive heartbeat timeout")
    return quarantined.state == "QUARANTINED" and quarantined.health == "UNHEALTHY"

def _bad() -> bool:
    return False

def test_l9_t_058():
    oracle("L9-REQ-FED-005", "L9-T-058", _good, _bad)
