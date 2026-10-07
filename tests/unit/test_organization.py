from __future__ import annotations

import pytest

from hyai._contracts import content_digest
from hyai.organization import OrganizationRouter, OrganizationRoutingError
from hyai.product import ProductContractManager, ProductWorkspaceManager, WorkspaceError


def contract() -> dict:
    value = {"schema_version": "2.1.0", "product_contract_id": "productcontract_demo", "revision": 1, "product_ref": "product_demo", "goal_ref": "goal_demo", "executive_mandate_ref": "mandate_demo", "target_consumers": ["operators"], "expected_outcomes": ["outcome"], "required_features": ["feature"], "nonfunctional_requirements": ["reliable"], "explicit_exclusions": ["unbounded scope"], "deployment_target": "staging", "operational_expectations": ["monitor"], "risk_envelope_ref": "risk_demo", "budget_envelope_ref": "budget_demo", "acceptance_baseline_refs": ["acceptance_demo"], "definition_of_done": ["verified"], "delivery_expectations": ["deliver"], "lifecycle_state": "BASELINED"}
    value["content_digest"] = content_digest(value)
    return value


def test_router_requires_bound_contract_and_activates_only_needed_departments():
    contracts = ProductContractManager()
    current = contracts.create_product_contract(contract())
    contracts.bind_to_product("product_demo", current)
    router = OrganizationRouter()
    low = router.route_product("product_demo", contract_manager=contracts, risk_class="LOW")
    high = router.route_product("product_demo", contract_manager=contracts, risk_class="HIGH", complexity="HIGH")

    assert low["department_nodes"] == ["product", "engineering", "quality"]
    assert {"security", "assurance", "architecture", "operations"}.issubset(high["department_nodes"])
    with pytest.raises(OrganizationRoutingError):
        router.route_product("product_demo", current)


def test_workspace_guard_allows_only_managed_or_explicit_external_locations(tmp_path):
    root = tmp_path / "hyai"
    manager = ProductWorkspaceManager(root)
    managed = root / "workspaces" / "product_demo" / "output"
    external = tmp_path / "external-repo"
    assert manager.ensure_workspace_isolation("product_demo", managed) == managed.resolve()
    assert manager.ensure_workspace_isolation("product_demo", external, external_repo=True) == external.resolve()
    with pytest.raises(WorkspaceError):
        manager.ensure_workspace_isolation("product_demo", root / "src" / "sprawl.py")
