"""Oracle test for L9-REQ-CAP-004 / L9-T-034."""
from hyai.capabilities.adapters import (
    DirectAccessForbiddenError,
    ModelAdapter,
    ProviderAdapter,
    verify_adapter_access,
)
from ._support import oracle

def _good() -> bool:
    adapter = ModelAdapter(
        model_id="gemini-flash",
        handler=lambda cap, req: {"status": "ADAPTED", "cap": cap},
        supported_capabilities=("cap_gen",),
    )
    res = adapter.invoke("cap_gen", {"prompt": "hello"})
    is_valid = verify_adapter_access(adapter)
    return is_valid and res.get("status") == "ADAPTED"

def _bad() -> bool:
    # Adversarial mutation: non-adapter object passes adapter verification
    raw_unadapted = object()
    return verify_adapter_access(raw_unadapted)

def test_l9_t_034():
    oracle("L9-REQ-CAP-004", "L9-T-034", _good, _bad)
