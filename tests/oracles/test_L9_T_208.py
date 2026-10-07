"""Oracle test for L9-REQ-INT-007 / L9-T-208."""
from hyai.interoperability.adapter import InteropGateway, create_protocol_adapter_descriptor
from ._support import oracle

def _good() -> bool:
    gateway = InteropGateway()
    a1 = create_protocol_adapter_descriptor(
        adapter_id="protocoladapter_a2a_v1",
        protocol_name="A2A",
        protocol_version="1.0.0",
        capabilities=["agent_comm"],
    )
    a2 = create_protocol_adapter_descriptor(
        adapter_id="protocoladapter_a2a_v2",
        protocol_name="A2A",
        protocol_version="2.0.0",
        capabilities=["agent_comm", "streaming"],
    )
    gateway.register_adapter(a1)
    gateway.register_adapter(a2)
    # Multiple protocol versions coexist through isolated adapters during migration
    return gateway.supports_coexistence("A2A")

def _bad() -> bool:
    return False

def test_l9_t_208():
    oracle("L9-REQ-INT-007", "L9-T-208", _good, _bad)
