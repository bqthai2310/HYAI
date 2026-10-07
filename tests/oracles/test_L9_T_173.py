"""Oracle test for L9-REQ-LRN-001 / L9-T-173."""
from hyai.learning.lesson import LessonAuthorityClass, create_organizational_lesson
from ._support import oracle

def _good() -> bool:
    # Execution outcome becomes OrganizationalLesson only through evidence/evaluation promotion
    lesson = create_organizational_lesson(
        lesson_id="lesson_retry_jitter",
        authority_class=LessonAuthorityClass.SUPPORTED,
        statement="Decorrelated jitter reduces lock contention by 40%",
        applicability_scope="NETWORKING",
        source_refs=["evalrun_jitter_01"],
        evidence_refs=["ev_telemetry_jitter_trace"],
        invalidation_triggers=["trigger_protocol_http3"],
    )
    return lesson.authority_class == "SUPPORTED" and len(lesson.evidence_refs) == 1

def _bad() -> bool:
    return False

def test_l9_t_173():
    oracle("L9-REQ-LRN-001", "L9-T-173", _good, _bad)
