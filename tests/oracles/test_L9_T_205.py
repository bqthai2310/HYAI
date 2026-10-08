"""Oracle test for L9-REQ-INT-004 / L9-T-205."""
from hyai.interoperability.adapter import InteropGateway, LossyTranslationError
from ._support import oracle

def _good() -> bool:
    gateway = InteropGateway()
    # Translation loss: failing to map required semantics fails closed
    try:
        gateway.translate_message(
            source_protocol="A2A",
            target_protocol="REST",
            payload={"action": "query"},
            required_semantics=["transactional_lease_id"],
        )
        return False
    except LossyTranslationError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_205():
    oracle("L9-REQ-INT-004", "L9-T-205", _good, _bad)
