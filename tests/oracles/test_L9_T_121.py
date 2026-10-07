"""Oracle test for L9-REQ-SKL-006 / L9-T-121."""
from hyai.skills.composition import (
    CompositeSkillDAG,
    RecursionLimitExceededError,
    SchemaIncompatibilityError,
    SkillCycleError,
    SkillEdge,
)
from ._support import oracle

def _good() -> bool:
    edge = SkillEdge(
        source_skill_id="skill_a",
        target_skill_id="skill_b",
        output_schema_ref="schema_doc",
        input_schema_ref="schema_doc",
    )
    dag = CompositeSkillDAG(
        composite_id="dag_pipeline",
        nodes=("skill_a", "skill_b"),
        edges=(edge,),
        max_recursion_depth=5,
    )
    dag.assert_recursion_depth(3)
    # Self-loop cycle rejection
    try:
        SkillEdge("skill_a", "skill_a", "schema_doc", "schema_doc")
        return False
    except SkillCycleError:
        pass
    # Schema incompatibility rejection
    try:
        SkillEdge("skill_a", "skill_b", "schema_out", "schema_in_different")
        return False
    except SchemaIncompatibilityError:
        pass
    # Recursion limit exceeded rejection
    try:
        dag.assert_recursion_depth(6)
        return False
    except RecursionLimitExceededError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_121():
    oracle("L9-REQ-SKL-006", "L9-T-121", _good, _bad)
