from __future__ import annotations

import pytest

from hyai._contracts import content_digest
from hyai.product import ProductContractManager, ProductError, ProductManager


def product() -> dict:
    value = {
        "schema_version": "2.1.0", "product_id": "product_demo", "goal_refs": ["goal_demo"],
        "name": "Demo", "purpose": "A bounded demo product", "lifecycle_state": "DEFINED",
        "owner": {"principal_type": "PO", "id": "po-1"}, "component_refs": [],
        "repository_bindings": [], "environment_refs": [], "acceptance_baseline_refs": [],
        "created_at": "2026-01-01T00:00:00Z",
    }
    value["content_digest"] = content_digest(value)
    return value


def contract() -> dict:
    value = {
        "schema_version": "2.1.0", "product_contract_id": "productcontract_demo", "revision": 1,
        "product_ref": "product_demo", "goal_ref": "goal_demo", "executive_mandate_ref": "mandate_demo",
        "target_consumers": ["operators"], "expected_outcomes": ["outcome"], "required_features": ["feature"],
        "nonfunctional_requirements": ["reliable"], "explicit_exclusions": ["unbounded scope"],
        "deployment_target": "staging", "operational_expectations": ["monitor"], "risk_envelope_ref": "risk_demo",
        "budget_envelope_ref": "budget_demo", "acceptance_baseline_refs": ["acceptance_demo"],
        "definition_of_done": ["verified"], "delivery_expectations": ["deliver"], "lifecycle_state": "BASELINED",
    }
    value["content_digest"] = content_digest(value)
    return value


def test_product_contract_binding_and_supersession_preserve_versioned_lineage():
    manager = ProductContractManager()
    original = manager.create_product_contract(contract())
    manager.bind_to_product("product_demo", original)
    successor = manager.supersede_contract(original["product_contract_id"], delivery_expectations=["deliver v2"])

    assert successor["revision"] == 2
    assert successor["supersedes_ref"] == original["product_contract_id"]
    assert manager.get_contract(original["product_contract_id"])["lifecycle_state"] == "SUPERSEDED"
    assert manager.contract_for_product("product_demo")["product_contract_id"] == successor["product_contract_id"]


def test_product_records_repository_component_release_and_retirement_lineage():
    manager = ProductManager()
    manager.create_product(product())
    bound = manager.bind_repository("product_demo", "repo://demo@abc")
    component = manager.register_component("product_demo", name="api", component_type="service", owner_boundary="team-a")
    release = manager.record_release(
        "product_demo", source_commits=["a" * 40],
        artifact_digests=[{"algorithm": "sha256", "encoding": "hex", "value": "b" * 64}],
        verdict_refs=["verdict_demo"], environment_ref="env_staging", status="PROMOTED",
    )
    retired = manager.retire_product("product_demo", "decision_demo", ["evidence_demo"], "retention_demo")

    assert bound["repository_bindings"] == ["repo://demo@abc"]
    assert component["component_id"] in manager.get_product("product_demo")["component_refs"]
    assert release["product_id"] == "product_demo"
    assert retired["lifecycle_state"] == "RETIRED"
    assert manager.get_retirement_lineage("product_demo")["data_retention_ref"] == "retention_demo"


def test_task_completion_cannot_accept_or_operate_a_product():
    manager = ProductManager()
    with pytest.raises(ProductError):
        manager.check_task_does_not_accept_product({"state": "PASS"}, {"lifecycle_state": "OPERATING"})
    with pytest.raises(ProductError):
        manager.check_task_does_not_accept_product({"state": "PASS", "product_state": "OPERATING"}, {"lifecycle_state": "DEFINED"})
