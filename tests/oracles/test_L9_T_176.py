"""Oracle test for L9-REQ-LRN-004 / L9-T-176."""
from hyai.learning.lesson import LessonAuthorityClass, create_organizational_lesson
from ._support import oracle

def _good() -> bool:
    # Disproven approaches preserved as NEGATIVE_KNOWLEDGE with evidence
    lesson = create_organizational_lesson(
        lesson_id="lesson_avoid_busy_wait",
        authority_class=LessonAuthorityClass.NEGATIVE_KNOWLEDGE,
        statement="Busy waiting on queue increases CPU by 90% without throughput gain",
        applicability_scope="CONCURRENCY",
        source_refs=["run_failed_stress"],
        evidence_refs=["ev_cpu_spike_profile"],
        invalidation_triggers=["hardware_spinloop_support"],
    )
    return lesson.authority_class == "NEGATIVE_KNOWLEDGE" and len(lesson.evidence_refs) == 1

def _bad() -> bool:
    return False

def test_l9_t_176():
    oracle("L9-REQ-LRN-004", "L9-T-176", _good, _bad)
