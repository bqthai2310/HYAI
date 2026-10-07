from hyai.memory.registry import CanonicalMemoryRegistry

from ._mem_support import memory_document, query_document
from ._support import oracle

_CANONICAL = "memory_canonical"
_UNVERIFIED = "memory_unverified"


def _ranked():
    registry = CanonicalMemoryRegistry()
    registry.store_record(
        memory_document(
            memory_id=_CANONICAL,
            authority_class="CANONICAL_REFERENCE",
            statement="Offline sync is supported.",
        )
    )
    registry.store_record(
        memory_document(
            memory_id=_UNVERIFIED,
            authority_class="UNVERIFIED",
            statement="Offline sync is supported.",
        )
    )
    return registry, registry.query(query_document(scope_filters=["*"], query_text="offline"))


def _good():
    registry, ranked = _ranked()
    return (
        [record.authority_class for record in ranked] == ["CANONICAL_REFERENCE", "UNVERIFIED"]
        and ranked[0].memory_id == _CANONICAL
        and registry.record(_UNVERIFIED).authority_class == "UNVERIFIED"
    )


def _bad():
    # Adversarial mutation: retrieval ranking promotes a derived record above the
    # canonical source and silently rewrites its authority.
    registry, ranked = _ranked()
    return bool(ranked) and ranked[0].memory_id != _CANONICAL


def test_l9_t_108():
    oracle("L9-REQ-MEM-003", "L9-T-108", _good, _bad)
