"""Oracle test for L9-REQ-FED-001 / L9-T-054."""
from hyai.federation.node import NodeHealth, NodeState, NodeTrustClass, create_federation_node
from ._support import oracle

def _good() -> bool:
    node = create_federation_node(
        node_id="node_cluster_edge_01",
        state=NodeState.ACTIVE,
        trust_class=NodeTrustClass.TRUSTED,
        platform="arm64-linux",
        capabilities=["cap_inference", "cap_cache"],
        health=NodeHealth.HEALTHY,
    )
    return node.node_id == "node_cluster_edge_01" and node.trust_class == "TRUSTED" and node.health == "HEALTHY"

def _bad() -> bool:
    return False

def test_l9_t_054():
    oracle("L9-REQ-FED-001", "L9-T-054", _good, _bad)
