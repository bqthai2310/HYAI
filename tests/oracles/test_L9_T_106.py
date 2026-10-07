from hyai.memory.record import MemoryKind, is_working_context

from ._mem_support import memory_document
from ._support import oracle

_DURABLE_KINDS = tuple(kind.value for kind in MemoryKind)


def _distinguishes_durable_kinds() -> bool:
    documents = [
        memory_document(memory_id=f"memory_kind_{index}", kind=kind)
        for index, kind in enumerate(_DURABLE_KINDS)
    ]
    return (
        len(set(_DURABLE_KINDS)) == 7
        and len({document["kind"] for document in documents}) == 7
        and is_working_context("WORKING")
        and is_working_context(" WORKING_CONTEXT ")
        and not any(is_working_context(kind) for kind in _DURABLE_KINDS)
    )


def test_l9_t_106():
    oracle("L9-REQ-MEM-001", "L9-T-106", _good, _bad)


def _good():
    return _distinguishes_durable_kinds()


def _bad():
    # Adversarial mutation: collapse the working/durable distinction so a durable
    # memory kind is reported as working context.
    return _distinguishes_durable_kinds() and is_working_context(MemoryKind.TASK_MEMORY.value)
