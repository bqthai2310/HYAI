"""Oracle test for L9-REQ-LRN-005 / L9-T-177."""
from hyai.learning.lesson import (
    LessonAuthorityClass,
    LessonRegistry,
    create_organizational_lesson,
)
from ._support import oracle

def _good() -> bool:
    registry = LessonRegistry()
    l1 = create_organizational_lesson(
        lesson_id="lesson_batch_small",
        authority_class=LessonAuthorityClass.OBSERVED,
        statement="Batch size 10 minimizes tail latency",
        applicability_scope="INFERENCE",
        source_refs=["run_1"],
        evidence_refs=["ev_1"],
        invalidation_triggers=["none"],
    )
    l2 = create_organizational_lesson(
        lesson_id="lesson_batch_large",
        authority_class=LessonAuthorityClass.OBSERVED,
        statement="Batch size 100 maximizes throughput",
        applicability_scope="INFERENCE",
        source_refs=["run_2"],
        evidence_refs=["ev_2"],
        invalidation_triggers=["none"],
    )
    registry.register_lesson(l1)
    registry.register_lesson(l2)
    # Conflicting lessons remain explicit until resolved
    registry.record_conflict("lesson_batch_small", "lesson_batch_large", "Tradeoff between latency and throughput")
    conflicts = registry.get_conflicts()
    return len(conflicts) == 1 and conflicts[0][0] == "lesson_batch_small"

def _bad() -> bool:
    return False

def test_l9_t_177():
    oracle("L9-REQ-LRN-005", "L9-T-177", _good, _bad)
