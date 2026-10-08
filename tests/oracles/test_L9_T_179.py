"""Oracle test for L9-REQ-LRN-007 / L9-T-179."""
from hyai.learning.lesson import (
    GlobalOvergeneralizationError,
    LessonAuthorityClass,
    LessonRegistry,
    create_organizational_lesson,
)
from ._support import oracle

def _good() -> bool:
    registry = LessonRegistry()
    lesson_local = create_organizational_lesson(
        lesson_id="lesson_single_product_trick",
        authority_class=LessonAuthorityClass.OBSERVED,
        statement="Product A specific caching trick",
        applicability_scope="GLOBAL",
        source_refs=["run_product_a"],
        evidence_refs=["ev_a"],
        invalidation_triggers=["none"],
    )
    # One-product success cannot silently become organization-wide (GLOBAL) rule
    try:
        registry.register_lesson(lesson_local, product_scope="product_alpha")
        return False
    except GlobalOvergeneralizationError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_179():
    oracle("L9-REQ-LRN-007", "L9-T-179", _good, _bad)
