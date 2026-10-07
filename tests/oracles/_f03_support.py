from __future__ import annotations

from hyai._contracts import content_digest


def product(product_id: str = "product_demo") -> dict:
    data = {"schema_version":"2.1.0", "product_id":product_id, "goal_refs":["goal_demo"], "name":"Demo", "purpose":"A bounded demo product", "lifecycle_state":"DEFINED", "owner":{"principal_type":"PO","id":"po-1"}, "component_refs":[], "repository_bindings":[], "environment_refs":[], "acceptance_baseline_refs":[], "created_at":"2026-01-01T00:00:00Z"}
    data["content_digest"] = content_digest(data); return data


def contract(product_ref: str = "product_demo") -> dict:
    data = {"schema_version":"2.1.0", "product_contract_id":"productcontract_demo", "revision":1, "product_ref":product_ref, "goal_ref":"goal_demo", "executive_mandate_ref":"mandate_demo", "target_consumers":["operators"], "expected_outcomes":["outcome"], "required_features":["feature"], "nonfunctional_requirements":["reliable"], "explicit_exclusions":["unbounded scope"], "deployment_target":"staging", "operational_expectations":["monitor"], "risk_envelope_ref":"risk_demo", "budget_envelope_ref":"budget_demo", "acceptance_baseline_refs":["acceptance_demo"], "definition_of_done":["verified"], "delivery_expectations":["deliver"], "lifecycle_state":"BASELINED"}
    data["content_digest"] = content_digest(data); return data


def task(task_id: str = "task_demo", workstream_id: str = "ws_demo", risk: str = "LOW") -> dict:
    return {"schema_version":"2.1.0", "task_id":task_id, "workstream_id":workstream_id, "objective":"Deliver bounded output", "scope":["one output"], "out_of_scope":["other output"], "requirement_refs":["REQ-1"], "acceptance_contract_ref":"acceptance_demo", "required_capabilities":["python"], "authority_class":"A1", "risk_class":risk, "state":"DEFINED"}


def workstream() -> dict:
    return {"schema_version":"2.1.0", "workstream_id":"ws_demo", "program_id":"prog_demo", "name":"Build", "outcome":"Built", "task_ids":["task_demo"], "dependency_refs":[], "state":"PLANNED"}


def program() -> dict:
    return {"schema_version":"2.1.0", "program_id":"prog_demo", "goal_id":"goal_demo", "product_refs":["product_demo"], "product_contract_refs":["productcontract_demo"], "name":"Demo program", "objective":"Deliver demo", "workstream_ids":["ws_demo"], "state":"PLANNED", "created_at":"2026-01-01T00:00:00Z"}
