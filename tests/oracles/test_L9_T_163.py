"""L9-REQ-DPT-008 / L9-T-163: Material OrganizationRoute change invalidates affected plan/handoff and records provenance."""
from hyai.organization import OrganizationRouter, OrganizationRoute
from ._support import oracle


def test_l9_t_163_organization_route_change_invalidates():
    def _pos():
        route = OrganizationRoute(
            organization_route_id="route_f13_001",
            program_ref="program_demo",
            department_nodes=("product", "engineering", "quality"),
            coordination_mode="SYNCHRONOUS",
            handoff_contract_refs=("handoff_001",),
            escalation_path=("product", "executive"),
        )
        invalidated = route.invalidate(reason="Risk envelope upgraded to CRITICAL", recorded_by="security_officer")
        return invalidated.is_invalidated and "CRITICAL" in invalidated.invalidation_reason

    def _neg():
        route = OrganizationRoute(
            organization_route_id="route_f13_002",
            program_ref="program_demo",
            department_nodes=("product", "engineering"),
            coordination_mode="SYNCHRONOUS",
            handoff_contract_refs=(),
            escalation_path=("product",),
        )
        return route.is_invalidated

    oracle("L9-REQ-DPT-008", "L9-T-163", _pos, _neg)
