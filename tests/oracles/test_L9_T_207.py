"""Oracle test for L9-REQ-INT-006 / L9-T-207."""
from hyai.interoperability.adapter import InteropGateway, create_protocol_adapter_descriptor
from ._support import oracle

def _good() -> bool:
    gateway = InteropGateway()
    adapter = create_protocol_adapter_descriptor(
        adapter_id="protocoladapter_rest_json",
        protocol_name="REST",
        protocol_version="1.1",
        capabilities=["http_crud"],
    )
    gateway.register_adapter(adapter)
    gateway.record_conformance_test(adapter.adapter_id, passed=True)
    return gateway.is_conformant(adapter.adapter_id)

def _bad() -> bool:
    return False

def test_l9_t_207():
    oracle("L9-REQ-INT-006", "L9-T-207", _good, _bad)
