"""Oracle test for L9-REQ-CAP-006 / L9-T-036."""
from hyai.capabilities.resolver import (
    CapabilityRequest,
    CapabilityResolver,
    ImplementationCandidate,
    SilentDowngradeForbiddenError,
)
from ._support import oracle

def _good() -> bool:
    resolver = CapabilityResolver()
    request = CapabilityRequest(
        task_id="task_high_q",
        capability_id="cap_transcribe",
        min_quality_class="CRITICAL",
        allow_explicit_fallback=False,
    )
    candidate_standard = ImplementationCandidate(
        implementation_ref="impl_standard",
        provided_capabilities=("cap_transcribe",),
        permissions=(),
        quality_class="STANDARD",
        risk_class="LOW",
    )
    try:
        resolver.resolve(request, [candidate_standard])
        return False
    except SilentDowngradeForbiddenError:
        return True

def _bad() -> bool:
    # Adversarial mutation: silent downgrade without authorization passes
    resolver = CapabilityResolver()
    request = CapabilityRequest(
        task_id="task_silent_down",
        capability_id="cap_transcribe",
        min_quality_class="CRITICAL",
        allow_explicit_fallback=False,
    )
    c = ImplementationCandidate(
        implementation_ref="impl_standard",
        provided_capabilities=("cap_transcribe",),
        permissions=(),
        quality_class="STANDARD",
        risk_class="LOW",
    )
    try:
        resolver.resolve(request, [c])
        return True
    except SilentDowngradeForbiddenError:
        return False

def test_l9_t_036():
    oracle("L9-REQ-CAP-006", "L9-T-036", _good, _bad)
