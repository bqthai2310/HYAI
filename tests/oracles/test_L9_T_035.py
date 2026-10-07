"""Oracle test for L9-REQ-CAP-005 / L9-T-035."""
from hyai.capabilities.resolver import CapabilityResolver
from ._support import oracle

def _good() -> bool:
    resolver = CapabilityResolver()
    full_context = {
        "task_id": "task_101",
        "inputs": {"text": "analyze this"},
        "secret_token": "sk-secret-123",
        "user_password": "super-secret-password",
        "scope_unrelated": "unrelated enterprise data",
    }
    minimized = resolver.minimize_context(full_context, "cap_nlp")
    # Must remove secrets and unrelated scope
    return (
        "secret_token" not in minimized
        and "user_password" not in minimized
        and "scope_unrelated" not in minimized
        and "inputs" in minimized
    )

def _bad() -> bool:
    # Adversarial mutation: context minimization retains credentials/secrets
    resolver = CapabilityResolver()
    minimized = resolver.minimize_context({"secret_key": "raw_secret"}, "cap_nlp")
    return "secret_key" in minimized

def test_l9_t_035():
    oracle("L9-REQ-CAP-005", "L9-T-035", _good, _bad)
