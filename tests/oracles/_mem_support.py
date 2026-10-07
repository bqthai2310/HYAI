from __future__ import annotations

from typing import Any

from hyai.memory.query import create_memory_query
from hyai.memory.record import create_memory_record


def principal_dict(principal_type: str = "PO", id: str = "po_1") -> dict[str, str]:
    return {"principal_type": principal_type, "id": id}


def memory_document(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "memory_id": "memory_default",
        "kind": "TASK_MEMORY",
        "scope_type": "PRODUCT",
        "scope_ref": "product_alpha",
        "authority_class": "CANONICAL_REFERENCE",
        "source_refs": ["src_default"],
        "provenance_refs": ["prov_default"],
        "lifecycle_state": "ACTIVE",
        "retention_class": "SHORT",
        "created_by": principal_dict("PO", "po_1"),
        "statement": "Default memory statement.",
    }
    defaults.update(overrides)
    if "created_by" in overrides and isinstance(overrides["created_by"], tuple):
        defaults["created_by"] = principal_dict(*overrides["created_by"])
    if (
        defaults.get("authority_class") == "CANONICAL_REFERENCE"
        and defaults["created_by"].get("principal_type")
        not in (
            "PO",
            "ARCHITECT",
            "INDEPENDENT_REVIEWER",
            "ASSURANCE_SERVICE",
            "POLICY_ENGINE",
        )
    ):
        defaults["created_by"] = principal_dict("PO", "po_1")
    return create_memory_record(**defaults)


def query_document(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "query_id": "memq_default",
        "requester": principal_dict("PO", "po_1"),
        "scope_filters": ["*"],
        "query_text": "default",
        "max_items": 10,
    }
    defaults.update(overrides)
    return create_memory_query(**defaults)
