"""Schema-backed compiler for bounded program planning."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from hyai._contracts import validate


class PlanningError(ValueError):
    pass


class PlanCompiler:
    def _compile(self, spec: Mapping[str, Any], schema: str) -> dict[str, Any]:
        document = deepcopy(dict(spec))
        validate(document, schema, PlanningError)
        return document

    def compile_task(self, spec: Mapping[str, Any], acceptance: Mapping[str, Any] | None = None) -> dict[str, Any]:
        task = self._compile(spec, "task_spec.schema.json")
        if not task["scope"] or not task["objective"].strip():
            raise PlanningError("a Task must have a bounded outcome and non-empty scope")
        if set(task["scope"]) & set(task["out_of_scope"]):
            raise PlanningError("Task scope conflicts with out_of_scope")
        if acceptance is not None:
            self.validate_machine_verifiable_acceptance(acceptance)
        return task

    def validate_machine_verifiable_acceptance(self, criterion: Mapping[str, Any]) -> bool:
        """Reject an automated criterion that lacks an executable verification ref."""
        automated = criterion.get("machine_verifiable", criterion.get("verification_method") in {"oracle_test_execution", "automated_test", "schema_validation"})
        if automated and not criterion.get("verification_ref"):
            raise PlanningError("machine-verifiable acceptance requires a verification_ref")
        return True

    def compile_workstream(self, spec: Mapping[str, Any], tasks: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
        stream = self._compile(spec, "workstream_spec.schema.json")
        if tasks is not None and set(stream["task_ids"]) != {task.get("task_id") for task in tasks}:
            raise PlanningError("Workstream task_ids must exactly represent its compiled tasks")
        return stream

    def compile_program(self, spec: Mapping[str, Any], workstreams: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
        program = self._compile(spec, "program_spec.schema.json")
        if workstreams is not None and set(program["workstream_ids"]) != {stream.get("workstream_id") for stream in workstreams}:
            raise PlanningError("Program workstream_ids must exactly represent its compiled Workstreams")
        return program

    def check_no_orphans(self, requirements: Iterable[str] | Mapping[str, Any], tasks: Iterable[Mapping[str, Any]], criteria: Iterable[Mapping[str, Any]]) -> bool:
        required = set(requirements if not isinstance(requirements, Mapping) else requirements.keys())
        task_items, criterion_items = list(tasks), list(criteria)
        task_refs = {ref for task in task_items for ref in task.get("requirement_refs", [])}
        criterion_refs = {ref for criterion in criterion_items for ref in criterion.get("requirement_refs", criterion.get("requirement_ref", []) if isinstance(criterion.get("requirement_ref"), list) else [criterion.get("requirement_ref")]) if ref}
        if required - task_refs or required - criterion_refs:
            raise PlanningError("orphan requirement lacks a task or acceptance criterion")
        if task_refs - required or criterion_refs - required:
            raise PlanningError("task or criterion references an unknown requirement")
        task_ids = {task.get("task_id") for task in task_items}
        linked_task_ids = {task_id for criterion in criterion_items for task_id in criterion.get("task_refs", criterion.get("task_ref", []) if isinstance(criterion.get("task_ref"), list) else [criterion.get("task_ref")]) if task_id}
        if linked_task_ids and linked_task_ids != task_ids:
            raise PlanningError("orphan task lacks an acceptance criterion")
        return True

    def validate_high_risk_adversarial(self, task: Mapping[str, Any], acceptance: Mapping[str, Any] | Iterable[Mapping[str, Any]]) -> bool:
        if task.get("risk_class") not in {"HIGH", "CRITICAL"}:
            return True
        cases = acceptance.get("negative_cases", acceptance.get("cases", [])) if isinstance(acceptance, Mapping) else list(acceptance)
        if not cases or not any((isinstance(case, Mapping) and (case.get("kind") in {"NEGATIVE", "ADVERSARIAL"} or case.get("adversarial") is True)) for case in cases):
            raise PlanningError("high-risk task acceptance requires adversarial negative cases")
        return True
