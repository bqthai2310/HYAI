"""Oracle test for L9-REQ-FED-002 / L9-T-055."""
from hyai.federation.node import (
    FederationManager,
    NodeTrustClass,
    UntrustedPlacementError,
    create_federation_node,
)
from ._support import oracle

def _good() -> bool:
    mgr = FederationManager()
    low_trust_node = create_federation_node(
        node_id="node_low_trust",
        trust_class=NodeTrustClass.LIMITED,
        capabilities=["cap_sec_compute"],
    )
    mgr.register_node(low_trust_node)
    # Placing task requiring HIGH_TRUST on LIMITED trust node must be rejected
    try:
        mgr.place_task("task_secret_data", "cap_sec_compute", min_trust=NodeTrustClass.HIGH_TRUST)
        return False
    except UntrustedPlacementError:
        pass
    high_trust_node = create_federation_node(
        node_id="node_high_trust",
        trust_class=NodeTrustClass.HIGH_TRUST,
        capabilities=["cap_sec_compute"],
    )
    mgr.register_node(high_trust_node)
    placed = mgr.place_task("task_secret_data", "cap_sec_compute", min_trust=NodeTrustClass.HIGH_TRUST)
    return placed.node_id == "node_high_trust"

def _bad() -> bool:
    return False

def test_l9_t_055():
    oracle("L9-REQ-FED-002", "L9-T-055", _good, _bad)
