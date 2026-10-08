"""L9-REQ-ORG-005 / L9-T-069: PO goal can drive full program lifecycle."""
from hyai.product import ProductContractManager
from hyai.organization import OrganizationRouter
from ._support import oracle


def test_l9_t_069_po_goal_drives_lifecycle():
    def _pos():
        contracts = ProductContractManager()
        c = {
            "schema_version": "2.1.0",
            "product_contract_id": "productcontract_f13",
            "revision": 1,
            "product_ref": "product_f13",
            "goal_ref": "goal_po_autonomous_delivery",
            "executive_mandate_ref": "mandate_f13",
            "target_consumers": ["operators"],
            "expected_outcomes": ["autonomous operation"],
            "required_features": ["full lifecycle router"],
            "nonfunctional_requirements": ["governed"],
            "explicit_exclusions": ["unbounded sprawl"],
            "deployment_target": "production",
            "operational_expectations": ["24/7 monitoring"],
            "risk_envelope_ref": "risk_f13",
            "budget_envelope_ref": "budget_f13",
            "acceptance_baseline_refs": ["acceptance_baseline_f13"],
            "definition_of_done": ["verified"],
            "delivery_expectations": ["continuous delivery"],
            "lifecycle_state": "BASELINED",
        }
        current = contracts.create_product_contract(c)
        contracts.bind_to_product("product_f13", current)
        router = OrganizationRouter()
        route = router.route_product("product_f13", contract_manager=contracts, risk_class="HIGH")
        return "goal_po_autonomous_delivery" in current["goal_ref"] and len(route["department_nodes"]) >= 3

    def _neg():
        try:
            contracts = ProductContractManager()
            router = OrganizationRouter()
            router.route_product("unbound_product", contract_manager=contracts)
            return True
        except Exception:
            return False

    oracle("L9-REQ-ORG-005", "L9-T-069", _pos, _neg)
