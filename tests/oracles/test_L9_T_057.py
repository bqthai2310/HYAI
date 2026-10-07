"""Oracle test for L9-REQ-FED-004 / L9-T-057."""
from hyai.federation.node import CompetingWriterError, FederationManager, create_federation_node
from ._support import oracle

def _good() -> bool:
    mgr = FederationManager()
    n1 = create_federation_node(node_id="node_primary")
    n2 = create_federation_node(node_id="node_competing")
    mgr.register_node(n1)
    mgr.register_node(n2)
    mgr.issue_writer_lease("node_primary", "lease_p1")
    # Granting competing writer lease while primary writer is active must be rejected
    try:
        mgr.issue_writer_lease("node_competing", "lease_p2")
        return False
    except CompetingWriterError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_057():
    oracle("L9-REQ-FED-004", "L9-T-057", _good, _bad)
