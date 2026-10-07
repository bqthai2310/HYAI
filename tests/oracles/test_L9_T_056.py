"""Oracle test for L9-REQ-FED-003 / L9-T-056."""
from hyai.federation.node import ExpiredLeaseCommitError, FederationManager, create_federation_node
from ._support import oracle

def _good() -> bool:
    mgr = FederationManager()
    node = create_federation_node(node_id="node_writer_01")
    mgr.register_node(node)
    mgr.issue_writer_lease("node_writer_01", "lease_writer_01")
    # Expired node lease cannot commit mutations
    try:
        mgr.commit_mutation("node_writer_01", "lease_writer_01", is_expired=True)
        return False
    except ExpiredLeaseCommitError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_056():
    oracle("L9-REQ-FED-003", "L9-T-056", _good, _bad)
