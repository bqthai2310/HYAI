from hyai.memory.record import MemoryValidationError, validate_memory_record

from ._mem_support import memory_document
from ._support import oracle


def _good():
    document = memory_document()
    validate_memory_record(document)
    return (
        document["scope_type"] == "PRODUCT"
        and document["scope_ref"] == "product_alpha"
        and bool(document["source_refs"])
        and bool(document["provenance_refs"])
        and document["content_digest"]["algorithm"] == "sha256"
        and len(document["content_digest"]["value"]) == 64
    )


def _bad():
    # Adversarial mutation: a durable record without provenance must not persist.
    document = memory_document()
    document.pop("provenance_refs")
    try:
        validate_memory_record(document)
    except MemoryValidationError:
        return False
    return True


def test_l9_t_107():
    oracle("L9-REQ-MEM-002", "L9-T-107", _good, _bad)
