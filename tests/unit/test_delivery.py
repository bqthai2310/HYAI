from __future__ import annotations

import pytest

from hyai._contracts import content_digest
from hyai.delivery import DeliveryContractManager, DeliveryError, DeliveryReadinessManager
from hyai.product import ProductContractManager


def product_contract() -> dict:
    document = {
        "schema_version": "2.1.0", "product_contract_id": "productcontract_demo", "revision": 1,
        "product_ref": "product_demo", "goal_ref": "goal_demo", "executive_mandate_ref": "mandate_demo",
        "target_consumers": ["operators"], "expected_outcomes": ["outcome"], "required_features": ["feature"],
        "nonfunctional_requirements": ["reliable"], "explicit_exclusions": ["unbounded scope"],
        "deployment_target": "staging", "operational_expectations": ["monitor"], "risk_envelope_ref": "risk_demo",
        "budget_envelope_ref": "budget_demo", "acceptance_baseline_refs": ["acceptance_demo"],
        "definition_of_done": ["verified"], "delivery_expectations": ["deliver"], "lifecycle_state": "BASELINED",
    }
    document["content_digest"] = content_digest(document)
    return document


def delivery_contract() -> dict:
    return {
        "product_ref": "product_demo", "release_subject_ref": "release_demo",
        "required_acceptance_refs": ["acceptance_demo"], "required_security_gates": ["security_demo"],
        "required_operational_gates": ["operations_demo"], "required_recovery_gates": ["recovery_demo"],
        "required_bundle_items": ["bundle_demo"],
    }


def passed_criteria() -> list[dict]:
    return [
        {"criterion_id": criterion, "result": "PASS", "evidence_refs": [f"evidence_{criterion}"]}
        for criterion in ("acceptance_demo", "security_demo", "operations_demo", "recovery_demo", "bundle_demo")
    ]


def test_readiness_requires_a_current_delivery_contract_bound_to_the_product_contract():
    products = ProductContractManager()
    product = products.create_product_contract(product_contract())
    products.bind_to_product("product_demo", product)
    contracts = DeliveryContractManager(products)
    readiness = DeliveryReadinessManager(contracts)
    release_digest = {"algorithm": "sha256", "encoding": "hex", "value": "a" * 64}

    with pytest.raises(DeliveryError, match="no baselined DeliveryContract"):
        readiness.evaluate_readiness("product_demo", release_digest, passed_criteria())

    initial = contracts.create_delivery_contract(delivery_contract())
    record = readiness.evaluate_readiness(
        "product_demo", release_digest, passed_criteria(), independent_review_ref="reviewatt_demo",
    )
    assert record["state"] == "DELIVERY_READY"
    assert record["delivery_contract_ref"] == initial["delivery_contract_id"]

    products.supersede_contract(product["product_contract_id"], delivery_expectations=["deliver v2"])
    with pytest.raises(DeliveryError, match="current baselined ProductContract"):
        readiness.evaluate_readiness("product_demo", release_digest, passed_criteria())

    successor = contracts.supersede_contract(initial["delivery_contract_id"])
    assert successor["revision"] == 2
    assert readiness.evaluate_readiness(
        "product_demo", release_digest, passed_criteria(), independent_review_ref="verdict_demo",
    )["state"] == "DELIVERY_READY"


def test_delivery_ready_requires_all_criteria_to_pass_and_an_independent_review():
    products = ProductContractManager()
    product = products.create_product_contract(product_contract())
    products.bind_to_product("product_demo", product)
    contracts = DeliveryContractManager(products)
    contracts.create_delivery_contract(delivery_contract())
    readiness = DeliveryReadinessManager(contracts)
    release_digest = {"algorithm": "sha256", "encoding": "hex", "value": "b" * 64}

    without_review = readiness.evaluate_readiness("product_demo", release_digest, passed_criteria())
    assert without_review["state"] == "NOT_READY"

    criteria = passed_criteria()
    criteria[0]["result"] = "FAIL"
    failed = readiness.evaluate_readiness(
        "product_demo", release_digest, criteria, independent_review_ref="reviewatt_demo",
    )
    assert failed["state"] == "CORRECTION_REQUIRED"
