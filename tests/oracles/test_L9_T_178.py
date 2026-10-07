"""Oracle test for L9-REQ-LRN-006 / L9-T-178."""
from hyai.learning.lesson import LessonAuthorityClass, create_organizational_lesson
from ._support import oracle

def _good() -> bool:
    lesson = create_organizational_lesson(
        lesson_id="lesson_plan_heuristic",
        authority_class=LessonAuthorityClass.VERIFIED,
        statement="Heuristic H2 reduces search space in plan compiler",
        applicability_scope="PLANNING",
        source_refs=["bench_plan"],
        evidence_refs=["ev_search_trace"],
        invalidation_triggers=["trigger_full_sat_solver"],
    )
    # Planning provenance can reference exact lesson_id and content_digest
    return lesson.lesson_id == "lesson_plan_heuristic" and bool(lesson.content_digest.get("value"))

def _bad() -> bool:
    return False

def test_l9_t_178():
    oracle("L9-REQ-LRN-006", "L9-T-178", _good, _bad)
