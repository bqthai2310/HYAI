"""Oracle test for L9-REQ-LRN-003 / L9-T-175."""
from hyai.learning.lesson import LessonAuthorityClass, create_organizational_lesson
from ._support import oracle

def _good() -> bool:
    lesson = create_organizational_lesson(
        lesson_id="lesson_chunk_size",
        authority_class=LessonAuthorityClass.VERIFIED,
        statement="Chunk size 512 is optimal for embedding retrieval",
        applicability_scope="VECTOR_SEARCH",
        source_refs=["bench_embed_eval"],
        evidence_refs=["ev_eval_results"],
        invalidation_triggers=["model_context_expansion_to_32k"],
    )
    # Records explicit applicability limits and invalidation triggers
    return lesson.applicability_scope == "VECTOR_SEARCH" and lesson.invalidation_triggers == ("model_context_expansion_to_32k",)

def _bad() -> bool:
    return False

def test_l9_t_175():
    oracle("L9-REQ-LRN-003", "L9-T-175", _good, _bad)
