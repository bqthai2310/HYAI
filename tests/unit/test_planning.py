from __future__ import annotations

import pytest

from hyai.planning import PlanCompiler, PlanningError


def task(*, risk: str = "LOW") -> dict:
    return {"schema_version": "2.1.0", "task_id": "task_demo", "workstream_id": "ws_demo", "objective": "Deliver output", "scope": ["output"], "out_of_scope": ["other"], "requirement_refs": ["REQ-1"], "acceptance_contract_ref": "acceptance_demo", "required_capabilities": ["python"], "authority_class": "A1", "risk_class": risk, "state": "DEFINED"}


def test_compiler_requires_bounded_task_and_machine_verification_reference():
    compiler = PlanCompiler()
    assert compiler.compile_task(task(), {"machine_verifiable": True, "verification_ref": "tests/test_demo.py"})["task_id"] == "task_demo"
    with pytest.raises(PlanningError):
        compiler.compile_task({**task(), "scope": []})
    with pytest.raises(PlanningError, match="verification_ref"):
        compiler.compile_task(task(), {"machine_verifiable": True})


def test_compiler_requires_exact_workstream_and_program_membership():
    compiler = PlanCompiler()
    workstream = {"schema_version": "2.1.0", "workstream_id": "ws_demo", "program_id": "prog_demo", "name": "Build", "outcome": "Built", "task_ids": ["task_demo"], "dependency_refs": [], "state": "PLANNED"}
    program = {"schema_version": "2.1.0", "program_id": "prog_demo", "goal_id": "goal_demo", "product_refs": ["product_demo"], "product_contract_refs": ["productcontract_demo"], "name": "Program", "objective": "Deliver", "workstream_ids": ["ws_demo"], "state": "PLANNED", "created_at": "2026-01-01T00:00:00Z"}
    assert compiler.compile_workstream(workstream, [task()])["workstream_id"] == "ws_demo"
    assert compiler.compile_program(program, [workstream])["program_id"] == "prog_demo"
    with pytest.raises(PlanningError):
        compiler.compile_workstream({**workstream, "task_ids": []}, [task()])


def test_compiler_rejects_orphans_and_high_risk_without_adversarial_cases():
    compiler = PlanCompiler()
    assert compiler.check_no_orphans(["REQ-1"], [task()], [{"requirement_ref": "REQ-1", "task_ref": "task_demo"}])
    with pytest.raises(PlanningError):
        compiler.check_no_orphans(["REQ-1"], [task()], [])
    with pytest.raises(PlanningError):
        compiler.validate_high_risk_adversarial(task(risk="HIGH"), [])
    assert compiler.validate_high_risk_adversarial(task(risk="HIGH"), [{"kind": "ADVERSARIAL"}])
