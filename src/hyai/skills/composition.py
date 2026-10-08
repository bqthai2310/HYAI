"""Composite skills, explicit DAG composition, cycle detection, and recursion limits."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hyai.skills.spec import (
    RecursionLimitExceededError,
    SkillCycleError,
    SkillError,
    SkillValidationError,
)


class SchemaIncompatibilityError(SkillError):
    """Raised when output schema of a source node is incompatible with target input schema."""


@dataclass(frozen=True)
class SkillEdge:
    source_skill_id: str
    target_skill_id: str
    output_schema_ref: str
    input_schema_ref: str

    def __post_init__(self) -> None:
        if self.source_skill_id == self.target_skill_id:
            raise SkillCycleError(f"Self-loop detected on skill '{self.source_skill_id}'")
        if self.output_schema_ref != self.input_schema_ref:
            raise SchemaIncompatibilityError(
                f"Edge {self.source_skill_id} -> {self.target_skill_id} schema mismatch: "
                f"output '{self.output_schema_ref}' incompatible with input '{self.input_schema_ref}'"
            )


@dataclass(frozen=True)
class CompositeSkillDAG:
    composite_id: str
    nodes: tuple[str, ...]
    edges: tuple[SkillEdge, ...]
    max_recursion_depth: int = 10

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(sorted(set(self.nodes))))
        object.__setattr__(self, "edges", tuple(self.edges))
        self._validate_dag()

    def _validate_dag(self) -> None:
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {node: 0 for node in self.nodes}

        for edge in self.edges:
            if edge.source_skill_id not in in_degree:
                raise SkillValidationError(f"Edge source '{edge.source_skill_id}' not in DAG nodes")
            if edge.target_skill_id not in in_degree:
                raise SkillValidationError(f"Edge target '{edge.target_skill_id}' not in DAG nodes")
            adj[edge.source_skill_id].append(edge.target_skill_id)
            in_degree[edge.target_skill_id] += 1

        queue: deque[str] = deque([node for node, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.nodes):
            raise SkillCycleError(f"Composite skill '{self.composite_id}' contains a directed cycle")

    def assert_recursion_depth(self, current_depth: int) -> None:
        if current_depth > self.max_recursion_depth:
            raise RecursionLimitExceededError(
                f"Composite skill '{self.composite_id}' invocation depth {current_depth} "
                f"exceeds bounded recursion limit {self.max_recursion_depth}"
            )
