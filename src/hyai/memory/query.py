"""Query contracts and exact context bundles for material execution."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from hyai._contracts import canonical, timestamp, validate
from hyai.compatibility.crypto import compute_digest, validate_digest_spec
from hyai.constitution.authority import Principal, PrincipalType
from hyai.memory.record import (
    MemoryAuthority,
    MemoryLifecycle,
    MemoryRecord,
    MemoryValidationError,
    RetentionClass,
    authority_rank,
    _principal_dict,
)


class QueryValidationError(MemoryValidationError):
    """A query or context bundle does not satisfy its schema contract."""


QueryError = QueryValidationError


def _validate_schema(document: Mapping[str, Any], schema_name: str) -> None:
    try:
        validate(document, schema_name, QueryValidationError)
    except MemoryValidationError:
        raise
    except Exception as exc:
        raise QueryValidationError(str(exc)) from exc


def _verify_digest(document: Mapping[str, Any]) -> None:
    digest = document.get("bundle_digest")
    if not isinstance(digest, Mapping) or not validate_digest_spec(dict(digest)):
        raise QueryValidationError("bundle_digest must be a canonical supported digest")
    material = {key: value for key, value in dict(document).items() if key != "bundle_digest"}
    expected = compute_digest(canonical(material), algorithm=str(digest["algorithm"]))
    if expected.get("encoding") != digest.get("encoding") or expected.get("value") != digest.get("value"):
        raise QueryValidationError("bundle_digest does not match canonical bundle material")


def scope_matches(record: MemoryRecord, scope_filters: Sequence[str]) -> bool:
    for raw_filter in scope_filters:
        scope_filter = str(raw_filter).strip()
        if not scope_filter:
            continue
        if scope_filter in {"*", "ALL"}:
            return True
        if ":" in scope_filter:
            scope_type, scope_ref = scope_filter.split(":", 1)
            if record.scope_type == scope_type and record.scope_ref == scope_ref:
                return True
        elif record.scope_type == scope_filter or record.scope_ref == scope_filter:
            return True
    return False


def classify(record: MemoryRecord) -> str:
    if record.retention_class in {RetentionClass.REGULATED.value, RetentionClass.LEGAL_HOLD.value}:
        return "SENSITIVE"
    if record.scope_type == "PRINCIPAL" or record.kind == "USER_PREFERENCE_MEMORY":
        return "SENSITIVE"
    return "INTERNAL"


_FULL_ACCESS_PRINCIPALS = frozenset({
    PrincipalType.PO,
    PrincipalType.SYSTEM,
    PrincipalType.POLICY_ENGINE,
    PrincipalType.ASSURANCE_SERVICE,
    PrincipalType.INDEPENDENT_REVIEWER,
})


def can_read(record: MemoryRecord, principal: Principal | Mapping[str, Any]) -> bool:
    actor = principal if isinstance(principal, Principal) else Principal(principal["principal_type"], principal["id"])
    if actor.principal_type in _FULL_ACCESS_PRINCIPALS:
        return True
    if classify(record) != "SENSITIVE":
        return True
    allowed_ids = {record.scope_ref, str(_principal_dict(record.created_by).get("id", ""))}
    allowed_ids.update(str(item) for item in record.provenance_refs)
    return str(actor.id) in allowed_ids


def relevance(record: MemoryRecord, query_text: str) -> float:
    normalized_query = query_text.strip().lower()
    if normalized_query in {"*", "all"}:
        return 1.0
    haystack_parts = [
        str(record.statement or ""),
        str(record.content_ref or ""),
        record.scope_ref,
        record.kind,
        record.authority_class,
        record.retention_class,
        " ".join(record.source_refs),
        " ".join(record.provenance_refs),
    ]
    haystack = " ".join(part for part in haystack_parts if part).lower()
    if normalized_query in haystack:
        return 1.0
    tokens = {token for token in re.split(r"[^a-z0-9]+", normalized_query) if token}
    if not tokens:
        return 0.0
    matched = sum(1 for token in tokens if token in haystack)
    return matched / len(tokens)


@dataclass(frozen=True)
class MemoryQuery:
    schema_version: str
    query_id: str
    requester: Principal | Mapping[str, Any]
    scope_filters: Sequence[str]
    query_text: str
    max_items: int
    authority_floor: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope_filters", tuple(str(item) for item in self.scope_filters))
        if self.authority_floor is not None:
            object.__setattr__(self, "authority_floor", MemoryAuthority(self.authority_floor).value)

    @classmethod
    def create(
        cls,
        *,
        query_id: str,
        requester: Principal | Mapping[str, Any],
        scope_filters: Sequence[str],
        query_text: str,
        max_items: int = 10,
        authority_floor: str | None = None,
        schema_version: str = "2.1.0",
    ) -> "MemoryQuery":
        query = cls(
            schema_version=schema_version,
            query_id=query_id,
            requester=requester,
            scope_filters=scope_filters,
            query_text=query_text,
            max_items=max_items,
            authority_floor=authority_floor,
        )
        query.validate()
        return query

    def to_dict(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema_version": self.schema_version,
            "query_id": self.query_id,
            "requester": _principal_dict(self.requester),
            "scope_filters": list(self.scope_filters),
            "query_text": self.query_text,
            "max_items": int(self.max_items),
        }
        if self.authority_floor is not None:
            document["authority_floor"] = self.authority_floor
        return document

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "MemoryQuery":
        validate_memory_query_document(document)
        return cls(
            schema_version=str(document["schema_version"]),
            query_id=str(document["query_id"]),
            requester=dict(document["requester"]),
            scope_filters=tuple(str(item) for item in document["scope_filters"]),
            query_text=str(document["query_text"]),
            max_items=int(document["max_items"]),
            authority_floor=document.get("authority_floor"),
        )

    def allows_authority(self, record: MemoryRecord) -> bool:
        if not self.authority_floor:
            return record.authority_class != MemoryAuthority.QUARANTINED.value
        floor = MemoryAuthority(self.authority_floor)
        if floor is MemoryAuthority.QUARANTINED:
            return record.authority_class == MemoryAuthority.QUARANTINED.value
        if record.authority_class == MemoryAuthority.QUARANTINED.value:
            return False
        return authority_rank(record.authority_class) >= authority_rank(floor)

    def validate(self) -> "MemoryQuery":
        validate_memory_query_document(self.to_dict())
        return self

    def score(self, record: MemoryRecord) -> float:
        return relevance(record, self.query_text)

    def matches(self, record: MemoryRecord, moment: str | None = None) -> bool:
        if not record.is_active_at(moment):
            return False
        if not can_read(record, self.requester):
            return False
        if not self.allows_authority(record):
            return False
        if not scope_matches(record, self.scope_filters):
            return False
        return self.score(record) > 0.0

    def ranked(self, records: Sequence[MemoryRecord], moment: str | None = None) -> tuple[MemoryRecord, ...]:
        selected = [record for record in records if self.matches(record, moment)]
        selected.sort(key=lambda record: record.memory_id)
        selected.sort(key=lambda record: record.created_at, reverse=True)
        selected.sort(key=lambda record: authority_rank(record.authority_class), reverse=True)
        selected.sort(key=lambda record: self.score(record), reverse=True)
        return tuple(selected[: int(self.max_items)])


def validate_memory_query_document(document: Mapping[str, Any]) -> None:
    _validate_schema(document, "memory_query.schema.json")
    floor = document.get("authority_floor")
    if floor is not None:
        MemoryAuthority(str(floor))


def validate_memory_query(document_or_query: MemoryQuery | Mapping[str, Any]) -> MemoryQuery:
    if isinstance(document_or_query, MemoryQuery):
        validate_memory_query_document(document_or_query.to_dict())
        return document_or_query
    validate_memory_query_document(document_or_query)
    return MemoryQuery.from_dict(document_or_query)


@dataclass(frozen=True)
class MemoryContextItem:
    memory_id: str
    revision_or_digest: str

    def to_dict(self) -> dict[str, str]:
        return {"memory_id": self.memory_id, "revision_or_digest": self.revision_or_digest}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "MemoryContextItem":
        return cls(memory_id=str(document["memory_id"]), revision_or_digest=str(document["revision_or_digest"]))

    @classmethod
    def for_record(cls, record: MemoryRecord) -> "MemoryContextItem":
        return cls(memory_id=record.memory_id, revision_or_digest=record.revision)


@dataclass(frozen=True)
class MemoryContextBundle:
    schema_version: str
    bundle_id: str
    query_id: str
    memory_items: Sequence[MemoryContextItem]
    bundle_digest: Mapping[str, str]
    created_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_items", tuple(MemoryContextItem.from_dict(item) if isinstance(item, Mapping) else item for item in self.memory_items))

    @classmethod
    def create(
        cls,
        *,
        query_id: str,
        memory_items: Sequence[MemoryContextItem | Mapping[str, Any]],
        bundle_id: str | None = None,
        schema_version: str = "2.1.0",
        created_at: str | None = None,
    ) -> "MemoryContextBundle":
        """Build a digest-sealed bundle from explicit memory items."""
        items = tuple(
            MemoryContextItem.from_dict(item) if isinstance(item, Mapping) else item
            for item in memory_items
        )
        seen: set[str] = set()
        for item in items:
            if item.memory_id in seen:
                raise QueryValidationError(f"duplicate memory_id in context bundle: {item.memory_id}")
            seen.add(item.memory_id)
        resolved_bundle_id = bundle_id or (
            "memctx_"
            + compute_digest(canonical({"query_id": query_id, "memory_items": [item.to_dict() for item in items]}))["value"][:32]
        )
        material = {
            "schema_version": schema_version,
            "bundle_id": resolved_bundle_id,
            "query_id": query_id,
            "memory_items": [item.to_dict() for item in items],
            "created_at": created_at or timestamp(),
        }
        return cls(
            schema_version=schema_version,
            bundle_id=str(material["bundle_id"]),
            query_id=query_id,
            memory_items=items,
            bundle_digest=compute_digest(canonical(material)),
            created_at=str(material["created_at"]),
        )

    @classmethod
    def for_records(cls, query: MemoryQuery | str, records: Sequence[MemoryRecord], *, schema_version: str = "2.1.0", created_at: str | None = None) -> "MemoryContextBundle":
        query_id = query.query_id if isinstance(query, MemoryQuery) else str(query)
        created_at = created_at or timestamp()
        items = sorted((MemoryContextItem.for_record(record) for record in records), key=lambda item: item.memory_id)
        seen: set[str] = set()
        for item in items:
            if item.memory_id in seen:
                raise QueryValidationError(f"duplicate memory_id in context bundle: {item.memory_id}")
            seen.add(item.memory_id)
        bundle_id = "memctx_" + compute_digest(canonical({"query_id": query_id, "memory_items": [item.to_dict() for item in items]}))["value"][:32]
        material = {
            "schema_version": schema_version,
            "bundle_id": bundle_id,
            "query_id": query_id,
            "memory_items": [item.to_dict() for item in items],
            "created_at": created_at,
        }
        bundle = cls(
            schema_version=schema_version,
            bundle_id=bundle_id,
            query_id=query_id,
            memory_items=items,
            bundle_digest=compute_digest(canonical(material)),
            created_at=created_at,
        )
        bundle.validate()
        return bundle

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "query_id": self.query_id,
            "memory_items": [item.to_dict() for item in self.memory_items],
            "bundle_digest": dict(self.bundle_digest),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "MemoryContextBundle":
        validate_memory_context_bundle_document(document)
        return cls(
            schema_version=str(document["schema_version"]),
            bundle_id=str(document["bundle_id"]),
            query_id=str(document["query_id"]),
            memory_items=tuple(MemoryContextItem.from_dict(item) for item in document.get("memory_items", ())),
            bundle_digest=dict(document["bundle_digest"]),
            created_at=str(document["created_at"]),
        )

    def receipt(self) -> tuple[dict[str, str], ...]:
        return tuple(item.to_dict() for item in self.memory_items)

    @classmethod
    def create(cls, **fields: Any) -> "MemoryContextBundle":
        if "records" in fields:
            return cls.for_records(fields.get("query", fields.get("query_id", "")), fields["records"])
        material = dict(fields)
        material.setdefault("schema_version", "2.1.0")
        material.setdefault("created_at", timestamp())
        items = [MemoryContextItem.from_dict(it) if isinstance(it, Mapping) else it for it in material.get("memory_items", [])]
        if "bundle_id" not in material:
            material["bundle_id"] = "memctx_" + compute_digest(canonical({"query_id": str(material.get("query_id", "")), "memory_items": [item.to_dict() for item in items]}))["value"][:32]
        material_to_digest = {
            "schema_version": material["schema_version"],
            "bundle_id": material["bundle_id"],
            "query_id": material["query_id"],
            "memory_items": [item.to_dict() for item in items],
            "created_at": material["created_at"],
        }
        digest = compute_digest(canonical(material_to_digest))
        bundle = cls(
            schema_version=material["schema_version"],
            bundle_id=material["bundle_id"],
            query_id=material["query_id"],
            memory_items=items,
            bundle_digest=digest,
            created_at=material["created_at"],
        )
        bundle.validate()
        return bundle

    def validate(self) -> "MemoryContextBundle":
        validate_memory_context_bundle_document(self.to_dict())
        return self


def validate_memory_context_bundle_document(document: Mapping[str, Any]) -> None:
    _validate_schema(document, "memory_context_bundle.schema.json")
    _verify_digest(document)
    ids = [str(item.get("memory_id")) for item in document.get("memory_items", ())]
    if len(ids) != len(set(ids)):
        raise QueryValidationError("memory_items must reference each memory_id at most once")


def validate_memory_context_bundle(document_or_bundle: MemoryContextBundle | Mapping[str, Any]) -> MemoryContextBundle:
    if isinstance(document_or_bundle, MemoryContextBundle):
        validate_memory_context_bundle_document(document_or_bundle.to_dict())
        return document_or_bundle
    validate_memory_context_bundle_document(document_or_bundle)
    return MemoryContextBundle.from_dict(document_or_bundle)


def create_memory_query(**fields: Any) -> dict[str, Any]:
    """Build a canonical MemoryQuery document from explicit fields."""
    return MemoryQuery.create(**fields).to_dict()


def create_context_bundle(**fields: Any) -> dict[str, Any]:
    """Build a digest-sealed MemoryContextBundle document from explicit fields."""
    return MemoryContextBundle.create(**fields).to_dict()


def create_memory_query(**fields: Any) -> dict[str, Any]:
    return MemoryQuery.create(**fields).to_dict()


def create_context_bundle(**fields: Any) -> dict[str, Any]:
    return MemoryContextBundle.create(**fields).to_dict()
