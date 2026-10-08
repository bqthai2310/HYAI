"""Oracle test for L9-REQ-LRN-002 / L9-T-174."""
from hyai.learning.lesson import ConstitutionalOverrideForbiddenError, LessonAuthorityClass, create_organizational_lesson
from ._support import oracle

def _good() -> bool:
    # Lesson attempting to override Constitution or ProductContract must be rejected
    try:
        create_organizational_lesson(
            lesson_id="lesson_override_bad",
            authority_class=LessonAuthorityClass.OBSERVED,
            statement="We should override Constitution to bypass authorization",
            applicability_scope="ALL",
            source_refs=["run_1"],
            evidence_refs=["ev_1"],
            invalidation_triggers=["never"],
        )
        return False
    except ConstitutionalOverrideForbiddenError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_174():
    oracle("L9-REQ-LRN-002", "L9-T-174", _good, _bad)
