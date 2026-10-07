"""Portfolio graph invariants and lifecycle provenance."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping


class PortfolioError(ValueError):
    pass


class DependencyCycleError(PortfolioError):
    pass


class PortfolioKernel:
    """The sole writer for hierarchy cancellation and supersession lifecycle events."""

    lifecycle_writer = "PortfolioKernel"

    def __init__(self) -> None:
        self.lifecycle_events: list[dict[str, Any]] = []

    def validate_hierarchy(
        self,
        goal: Mapping[str, Any],
        products: Iterable[Mapping[str, Any]],
        programs: Iterable[Mapping[str, Any]],
        workstreams: Iterable[Mapping[str, Any]],
        tasks: Iterable[Mapping[str, Any]],
    ) -> bool:
        """Enforce the canonical Goal -> Product -> Program -> Workstream -> Task chain."""
        goal_id = goal.get("goal_id")
        product_items, program_items = list(products), list(programs)
        workstream_items, task_items = list(workstreams), list(tasks)
        product_ids = {item.get("product_id") for item in product_items}
        if not goal_id or None in product_ids or not product_ids or any(goal_id not in item.get("goal_refs", []) for item in product_items):
            raise PortfolioError("each Product must be attached to the canonical Goal")
        program_ids = {item.get("program_id") for item in program_items}
        if not program_ids or None in program_ids or any(item.get("goal_id") != goal_id or not item.get("product_refs") or not set(item.get("product_refs", [])) <= product_ids for item in program_items):
            raise PortfolioError("each Program must attach to the Goal and known Products")
        workstream_ids = {item.get("workstream_id") for item in workstream_items}
        if None in workstream_ids or any(item.get("program_id") not in program_ids for item in workstream_items):
            raise PortfolioError("each Workstream must attach to a known Program")
        if any(not item.get("task_id") or item.get("workstream_id") not in workstream_ids for item in task_items):
            raise PortfolioError("each Task must attach to a known Workstream")
        for program in program_items:
            if not set(program.get("workstream_ids", [])) <= workstream_ids:
                raise PortfolioError("Program references an unknown Workstream")
        for stream in workstream_items:
            if not set(stream.get("task_ids", [])) <= {item.get("task_id") for item in task_items}:
                raise PortfolioError("Workstream references an unknown Task")
        return True

    def detect_dependency_cycles(self, dependencies: Mapping[str, Iterable[str]] | Iterable[Mapping[str, Any]], *, raise_on_cycle: bool = True) -> bool | list[list[str]]:
        """Detect cycles in a dependency graph, including nodes referenced only as dependencies."""
        if isinstance(dependencies, Mapping):
            graph = {str(node): [str(item) for item in refs] for node, refs in dependencies.items()}
        else:
            graph = {str(item.get("id", item.get("task_id", item.get("workstream_id")))): [str(ref) for ref in item.get("dependency_refs", [])] for item in dependencies}
        for refs in list(graph.values()):
            for ref in refs:
                graph.setdefault(ref, [])
        visiting: set[str] = set(); visited: set[str] = set(); cycles: list[list[str]] = []

        def visit(node: str, trail: list[str]) -> None:
            if node in visiting:
                # ``trail`` already includes the back-edge node, so adding it
                # again would produce an invalid duplicated cycle terminator.
                cycles.append(trail[trail.index(node):]); return
            if node in visited:
                return
            visiting.add(node)
            for child in graph[node]: visit(child, trail + [child])
            visiting.remove(node); visited.add(node)

        for node in graph: visit(node, [node])
        if cycles and raise_on_cycle:
            raise DependencyCycleError("dependency cycle: " + " -> ".join(cycles[0]))
        return cycles if not raise_on_cycle else True

    def priority_gate(
        self,
        candidate: Mapping[str, Any] | None = None,
        *,
        authority_ok: bool | None = None,
        risk_ok: bool | None = None,
        dependencies_ok: bool | None = None,
        budget_ok: bool | None = None,
    ) -> bool:
        values = dict(candidate or {})
        gates = {
            "authority": values.get("authority_ok", authority_ok),
            "risk": values.get("risk_ok", risk_ok),
            "dependency": values.get("dependencies_ok", values.get("dependency_ok", dependencies_ok)),
            "budget": values.get("budget_ok", budget_ok),
        }
        failed = [name for name, value in gates.items() if value is not True]
        if failed:
            raise PortfolioError("priority optimization blocked until hard gates pass: " + ", ".join(failed))
        return True

    def cancel_or_supersede(
        self, entity: Mapping[str, Any], action: str, *, reason: str, provenance_ref: str, replacement_ref: str | None = None
    ) -> dict[str, Any]:
        if action not in {"CANCEL", "CANCELLED", "SUPERSEDE", "SUPERSEDED"}:
            raise PortfolioError("action must be cancel or supersede")
        if not reason or not provenance_ref:
            raise PortfolioError("cancellation/supersession requires reason and provenance")
        if action.startswith("SUPER") and not replacement_ref:
            raise PortfolioError("supersession requires replacement provenance")
        item = deepcopy(dict(entity))
        item["state"] = "CANCELLED" if action.startswith("CANCEL") else "SUPERSEDED"
        event = {"writer": self.lifecycle_writer, "entity_ref": item.get("task_id", item.get("workstream_id", item.get("program_id", item.get("product_id")))), "action": item["state"], "reason": reason, "provenance_ref": provenance_ref}
        if replacement_ref: event["replacement_ref"] = replacement_ref
        item["lifecycle_provenance"] = event
        self.lifecycle_events.append(deepcopy(event))
        return item
