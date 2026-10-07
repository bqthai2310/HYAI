"""Oracle test for L9-REQ-DLV-003 / L9-T-166."""
from hyai._contracts import content_digest
from hyai.delivery.contract import DeliveryContractManager, DeliveryError, DeliveryReadinessManager
from hyai.product import ProductContractManager
from ._support import oracle


def _product_contract() -> dict:
    doc = {
        "schema_version": "2.1.0",
        "product_contract_id": "productcontract_demo",
        "revision": 1,
        "product_ref": "product_demo",
        "goal_ref": "goal_demo",
        "executive_mandate_ref": "mandate_demo",
        "target_consumers": ["operators"],
        "expected_outcomes": ["outcome"],
        "required_features": ["feature"],
        "nonfunctional_requirements": ["reliable"],
        "explicit_exclusions": ["unbounded scope"],
        "deployment_target": "staging",
        "operational_expectations": ["monitor"],
        "risk_envelope_ref": "risk_demo",
        "budget_envelope_ref": "budget_demo",
        "acceptance_baseline_refs": ["acceptance_demo"],
        "definition_of_done": ["verified"],
        "delivery_expectations": ["deliver"],
        "lifecycle_state": "BASELINED",
    }
    doc["content_digest"] = content_digest(doc)
    return doc


def _delivery_contract() -> dict:
    return {
        "product_ref": "product_demo",
        "release_subject_ref": "release_demo",
        "required_acceptance_refs": ["acceptance_demo"],
        "required_security_gates": ["security_demo"],
        "required_operational_gates": ["operations_demo"],
        "required_recovery_gates": ["recovery_demo"],
        "required_bundle_items": ["bundle_demo"],
    }


def _good() -> bool:
    products = ProductContractManager()
    prod = products.create_product_contract(_product_contract())
    products.bind_to_product("product_demo", prod)
    contracts = DeliveryContractManager(products)
    contracts.create_delivery_contract(_delivery_contract())
    manager = DeliveryReadinessManager(contracts)
    release_digest = {"algorithm": "sha256", "encoding": "hex", "value": "a" * 64}

    # Criteria reports PASS, but one criterion has empty evidence_refs -> must NOT be DELIVERY_READY
    criteria_empty_ev = [
        {
            "criterion_id": c,
            "result": "PASS",
            "evidence_refs": [] if c == "acceptance_demo" else [f"ev_{c}"],
        }
        for c in ("acceptance_demo", "security_demo", "operations_demo", "recovery_demo", "bundle_demo")
    ]
    try:
        readiness = manager.evaluate_readiness(
            "product_demo",
            release_digest,
            criteria_empty_ev,
            independent_review_ref="review_pass_01",
        )
        return readiness["state"] != "DELIVERY_READY"
    except DeliveryError:
        return True


def _bad() -> bool:
    return False


def test_l9_t_166():
    oracle("L9-REQ-DLV-003", "L9-T-166", _good, _bad)
