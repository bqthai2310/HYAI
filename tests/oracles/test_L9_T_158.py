"""L9-REQ-DPT-003 / L9-T-158: Policy forces Assurance/Security/Ops participation when Product risk/profile requires them."""
from hyai.organization import OrganizationRouter
from hyai.product import ProductContractManager
from ._support import oracle


def test_l9_t_158_policy_forces_mandatory_departments():
    def _pos():
        contracts = ProductContractManager()
        c = {
            "schema_version": "2.1.0",
            "product_contract_id": "productcontract_sec",
            "revision": 1,
            "product_ref": "product_sec",
            "goal_ref": "goal_sec",
            "executive_mandate_ref": "mandate_sec",
            "target_consumers": ["users"],
            "expected_outcomes": ["secure service"],
            "required_features": ["auth"],
            "nonfunctional_requirements": ["zero trust"],
            "explicit_exclusions": ["none"],
            "deployment_target": "production",
            "operational_expectations": ["secure"],
            "risk_envelope_ref": "risk_high",
            "budget_envelope_ref": "budget_sec",
            "acceptance_baseline_refs": ["acceptance_sec"],
            "definition_of_done": ["audited"],
            "delivery_expectations": ["gated"],
            "lifecycle_state": "BASELINED",
        }
        current = contracts.create_product_contract(c)
        contracts.bind_to_product("product_sec", current)
        router = OrganizationRouter()
        high = router.route_product("product_sec", contract_manager=contracts, risk_class="HIGH", complexity="HIGH")
        return {"security", "assurance", "operations"}.issubset(set(high["department_nodes"]))

    def _neg():
        router = OrganizationRouter()
        try:
            router.route_product("non_existent_product")
            return True
        except Exception:
            return False

    oracle("L9-REQ-DPT-003", "L9-T-158", _pos, _neg)
