"""Oracle test for L9-REQ-CAP-002 / L9-T-032."""
from hyai.capabilities.resolver import (
    CapabilityRequest,
    CapabilityResolver,
    ConstraintSatisfactionError,
    ImplementationCandidate,
)
from ._support import oracle

def _good() -> bool:
    resolver = CapabilityResolver()
    request = CapabilityRequest(
        task_id="task_audit",
        capability_id="cap_audit",
        required_permissions=("perm_read",),
        max_risk_class="MEDIUM",
    )
    # Candidate 1: cheap/fast but violates hard constraint (HIGH risk > max MEDIUM)
    c1 = ImplementationCandidate(
        implementation_ref="impl_cheap_risky",
        provided_capabilities=("cap_audit",),
        permissions=("perm_read",),
        quality_class="STANDARD",
        risk_class="HIGH",
        estimated_cost=1.0,
    )
    # Candidate 2: more expensive but satisfies hard constraints
    c2 = ImplementationCandidate(
        implementation_ref="impl_safe",
        provided_capabilities=("cap_audit",),
        permissions=("perm_read",),
        quality_class="STANDARD",
        risk_class="LOW",
        estimated_cost=5.0,
    )
    plan = resolver.resolve(request, [c1, c2])
    return plan.bindings[0]["implementation_ref"] == "impl_safe"

def _bad() -> bool:
    # Adversarial mutation: resolver picks c1 despite hard constraint violation
    return False

def test_l9_t_032():
    oracle("L9-REQ-CAP-002", "L9-T-032", _good, _bad)
