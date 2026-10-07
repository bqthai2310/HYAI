from hyai._contracts import content_digest
from hyai.compatibility import compute_digest
from hyai.delivery import DeliveryContractManager, DeliveryError, DeliveryReadinessManager
from hyai.product import ProductContractManager
from ._support import oracle


def _product_contract():
    document = {"schema_version": "2.1.0", "product_contract_id": "productcontract_demo", "revision": 1, "product_ref": "product_demo", "goal_ref": "goal_demo", "executive_mandate_ref": "mandate_demo", "target_consumers": ["operators"], "expected_outcomes": ["outcome"], "required_features": ["feature"], "nonfunctional_requirements": ["reliable"], "explicit_exclusions": ["unbounded"], "deployment_target": "staging", "operational_expectations": ["monitor"], "risk_envelope_ref": "risk_demo", "budget_envelope_ref": "budget_demo", "acceptance_baseline_refs": ["acceptance_demo"], "definition_of_done": ["verified"], "delivery_expectations": ["deliver"], "lifecycle_state": "BASELINED"}
    document["content_digest"] = content_digest(document)
    return document


def _criteria():
    return [{"criterion_id": name, "result": "PASS", "evidence_refs": ["ev_" + name]} for name in ["accept", "security", "operational", "recovery", "bundle"]]


def test_l9_t_164():
    products = ProductContractManager(); contract = products.create_product_contract(_product_contract()); products.bind_to_product("product_demo", contract)
    deliveries = DeliveryContractManager(products)
    deliveries.create_delivery_contract(product_ref="product_demo", release_subject_ref="release_demo", required_acceptance_refs=["accept"], required_security_gates=["security"], required_operational_gates=["operational"], required_recovery_gates=["recovery"], required_bundle_items=["bundle"])
    readiness = DeliveryReadinessManager(deliveries)
    oracle("L9-REQ-DLV-001", "L9-T-164", lambda: readiness.evaluate_readiness("product_demo", compute_digest(b"release"), _criteria(), independent_review_ref="verdict_demo")["state"] == "DELIVERY_READY", lambda: _bad())


def _bad():
    try:
        DeliveryReadinessManager(DeliveryContractManager()).evaluate_readiness("product_demo", compute_digest(b"release"), _criteria())
    except DeliveryError:
        return False
    return True
