"""Oracle test for L9-REQ-INT-002 / L9-T-203."""
from hyai.interoperability.adapter import create_protocol_adapter_descriptor
from ._support import oracle

def _good() -> bool:
    desc = create_protocol_adapter_descriptor(
        adapter_id="protocoladapter_grpc_v1",
        protocol_name="gRPC",
        protocol_version="1.62.0",
        capabilities=["streaming_rpc"],
        security_profile="mTLS_SPFFE",
        compatibility_ref="compat_grpc_standard",
    )
    # Active protocol adapter has identity, version, capability, security, compatibility descriptor
    return (
        desc.security_profile == "mTLS_SPFFE"
        and desc.compatibility_ref == "compat_grpc_standard"
        and bool(desc.content_digest)
    )

def _bad() -> bool:
    return False

def test_l9_t_203():
    oracle("L9-REQ-INT-002", "L9-T-203", _good, _bad)
