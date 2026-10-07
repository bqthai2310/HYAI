from __future__ import annotations

import pytest

from hyai.portfolio import DependencyCycleError, PortfolioError, PortfolioKernel


def hierarchy() -> tuple[dict, list[dict], list[dict], list[dict], list[dict]]:
    return (
        {"goal_id": "goal_demo"},
        [{"product_id": "product_demo", "goal_refs": ["goal_demo"]}],
        [{"program_id": "prog_demo", "goal_id": "goal_demo", "product_refs": ["product_demo"], "workstream_ids": ["ws_demo"]}],
        [{"workstream_id": "ws_demo", "program_id": "prog_demo", "task_ids": ["task_demo"]}],
        [{"task_id": "task_demo", "workstream_id": "ws_demo"}],
    )


def test_hierarchy_requires_every_canonical_link():
    kernel = PortfolioKernel()
    assert kernel.validate_hierarchy(*hierarchy())
    goal, products, programs, workstreams, tasks = hierarchy()
    tasks[0]["workstream_id"] = "ws_missing"
    with pytest.raises(PortfolioError):
        kernel.validate_hierarchy(goal, products, programs, workstreams, tasks)


def test_dependency_cycles_are_detected_or_reported():
    kernel = PortfolioKernel()
    assert kernel.detect_dependency_cycles({"a": ["b"], "b": []}) is True
    with pytest.raises(DependencyCycleError):
        kernel.detect_dependency_cycles({"a": ["b"], "b": ["a"]})
    assert kernel.detect_dependency_cycles({"a": ["b"], "b": ["a"]}, raise_on_cycle=False) == [["a", "b", "a"]]


def test_priority_hard_gates_and_lifecycle_provenance():
    kernel = PortfolioKernel()
    assert kernel.priority_gate(authority_ok=True, risk_ok=True, dependencies_ok=True, budget_ok=True)
    with pytest.raises(PortfolioError, match="authority"):
        kernel.priority_gate(authority_ok=False, risk_ok=True, dependencies_ok=True, budget_ok=True)
    cancelled = kernel.cancel_or_supersede({"task_id": "task_demo"}, "CANCEL", reason="obsolete", provenance_ref="decision_demo")
    assert cancelled["lifecycle_provenance"]["writer"] == "PortfolioKernel"
    assert kernel.lifecycle_events[0]["provenance_ref"] == "decision_demo"
