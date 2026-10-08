"""Oracle test for L9-REQ-INT-001 / L9-T-202."""
from hyai.interoperability.adapter import create_protocol_adapter_descriptor
from ._support import oracle

def _good() -> bool:
    # MCP/A2A/REST/gRPC protocols are adapters with descriptors, not stable core semantics
    mcp_desc = create_protocol_adapter_descriptor(
        adapter_id="protocoladapter_mcp_v1",
        protocol_name="MCP",
        protocol_version="2024-11-05",
        capabilities=["tool_invocation", "resource_read"],
    )
    return mcp_desc.protocol_name == "MCP" and mcp_desc.adapter_id.startswith("protocoladapter_")

def _bad() -> bool:
    return False

def test_l9_t_202():
    oracle("L9-REQ-INT-001", "L9-T-202", _good, _bad)
