"""Oracle test for L9-REQ-INT-003 / L9-T-204."""
from hyai.interoperability.adapter import InteropGateway, SilentProtocolDowngradeError
from ._support import oracle

def _good() -> bool:
    gateway = InteropGateway()
    # Explicit version negotiation: unsupported version without explicit allowance must fail
    try:
        gateway.negotiate_version(
            protocol_name="MCP",
            requested_version="2025-01-01",
            supported_versions=["2024-11-05", "2024-10-07"],
            allow_silent_downgrade=False,
        )
        return False
    except SilentProtocolDowngradeError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_204():
    oracle("L9-REQ-INT-003", "L9-T-204", _good, _bad)
