"""Canonical, auditable memory registry with contradiction preservation."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hyai._contracts import canonical, timestamp
from hyai.compatibility.crypto import compute_digest
from hyai.constitution.authority import Principal
from hyai.memory.query import (
    MemoryContextBundle,
    MemoryQuery,
    QueryValidationError,
    validate_memory_context_bundle,
    validate_memory_query,
)
from hyai.memory.record import (
    MemoryAuthority,
    MemoryLifecycle,
    MemoryRecord,
    MemoryValidationError,
    RetentionClass,
    SecretMaterialError,
    PoisoningError,
    authority_rank,
    document_contains_secret,
    document_is_poisoned,
    validate_memory_record,
    _principal_dict,
)
from hyai.memory.tombstone import (
    DataRetentionPolicy,
    MemoryTombstone,
    TombstoneValidationError,
    validate_data_retention_policy,
    validate_memory_tombstone,
)


class RegistryError(ValueError):
    """A registry operation would violate canonical memory semantics."""


MemoryRegistryError = RegistryError


MemoryRegistryError = RegistryError


class ContradictionResolutionError(RegistryError):
    """A contradiction cannot be resolved without an explicit memory reference."""


def _now() -> datetime:
    return datetime.fromisoformat(timestamp().replace("Z", "+00:00"))


@dataclass(frozen=True)
class Contradiction:
    contradiction_id: str
    memory_ids: tuple[str, ...]
    kind: str
    reason: str
    status: str = "UNRESOLVED"
    detected_at: str = ""
    resolved_at: str | None = None
    resolution_memory_id: str | None = None
    resolution_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        document = {
            "contradiction_id": self.contradiction_id,
            "memory_ids": list(self.memory_ids),
            "kind": self.kind,
            "reason": self.reason,
            "status": self.status,
            "detected_at": self.detected_at,
        }
        if self.resolved_at is not None:
            document["resolved_at"] = self.resolved_at
        if self.resolution_memory_id is not None:
            document["resolution_memory_id"] = self.resolution_memory_id
        if self.resolution_reason is not None:
            document["resolution_reason"] = self.resolution_reason
        return document

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "Contradiction":
        memory_ids = tuple(str(item) for item in document["memory_ids"])
        if len(memory_ids) < 2:
            raise ContradictionResolutionError("a contradiction must reference at least two memories")
        return cls(
            contradiction_id=str(document["contradiction_id"]),
            memory_ids=memory_ids,
            kind=str(document["kind"]),
            reason=str(document["reason"]),
            status=str(document.get("status", "UNRESOLVED")),
            detected_at=str(document.get("detected_at", "")),
            resolved_at=document.get("resolved_at"),
            resolution_memory_id=document.get("resolution_memory_id"),
            resolution_reason=document.get("resolution_reason"),
        )


@dataclass(frozen=True)
class MemorySearchResult:
    query: MemoryQuery
    records: tuple[MemoryRecord, ...]
    unresolved_contradictions: tuple[Contradiction, ...]
    canonical_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "unresolved_contradictions": [item.to_dict() for item in self.unresolved_contradictions],
            "canonical_refs": list(self.canonical_refs),
        }


_NEGATIVE_WORDS = frozenset({
    "not",
    "no",
    "never",
    "cannot",
    "disabled",
    "disable",
    "forbidden",
    "prohibited",
    "false",
    "unverified",
    "contradicts",
})
_POSITIVE_WORDS = frozenset({
    "enabled",
    "enable",
    "allowed",
    "allow",
    "permitted",
    "permit",
    "required",
    "require",
    "true",
    "yes",
    "active",
    "verified",
})
_POLARITY_WORDS = _NEGATIVE_WORDS | _POSITIVE_WORDS

_STOPWORDS = frozenset({
    "is",
    "are",
    "the",
    "a",
    "an",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "as",
    "at",
    "be",
    "will",
    "should",
    "must",
    "can",
    "by",
})

_EXPLICIT_CONFLICT = re.compile(r"(?:contradicts|conflicts_with)\s*[:=]?\s*(memory_[A-Za-z0-9_]+)", re.I)


def _explicit_conflict_targets(record: MemoryRecord) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_EXPLICIT_CONFLICT.findall(record.text)))


def _claim_signature(record: MemoryRecord) -> tuple[str, frozenset[str]]:
    text = record.text.lower()
    tokens = [token for token in re.split(r"[^a-z0-9]+", text) if token]
    polarity = "NEGATIVE" if any(token in _NEGATIVE_WORDS for token in tokens) else "POSITIVE"
    subject = frozenset(token for token in tokens if token not in _STOPWORDS and token not in _POLARITY_WORDS)
    return polarity, subject


def _is_contradiction(left: MemoryRecord, right: MemoryRecord) -> tuple[bool, str]:
    left_targets = _explicit_conflict_targets(left)
    right_targets = _explicit_conflict_targets(right)
    if right.memory_id in left_targets or left.memory_id in right_targets:
        return True, "explicit contradiction marker in memory statement"
    if (left.kind, left.scope_type, left.scope_ref) != (right.kind, right.scope_type, right.scope_ref):
        return False, ""
    left_polarity, left_subject = _claim_signature(left)
    right_polarity, right_subject = _claim_signature(right)
    if left_subject and left_subject == right_subject and left_polarity != right_polarity:
        return True, "same scoped claim carries opposite polarity"
    return False, ""


class CanonicalMemoryRegistry:
    """Canonical memory is content-addressed, append-only in history, and explicit about loss."""

    def __init__(self, policies: Iterable[DataRetentionPolicy | Mapping[str, Any]] | None = None) -> None:
        self._schema_version = "2.1.0"
        self._records: dict[str, MemoryRecord] = {}
        self._history: dict[str, list[MemoryRecord]] = {}
        self._tombstones: dict[str, MemoryTombstone] = {}
        self._policies_by_id: dict[str, DataRetentionPolicy] = {}
        self._policies_by_class: dict[str, DataRetentionPolicy] = {}
        self._contradictions: dict[str, Contradiction] = {}
        self._bundles: dict[str, MemoryContextBundle] = {}
        self._audit: list[dict[str, Any]] = []
        self._derived_index: dict[str, Any] = {}
        for retention_class in RetentionClass:
            self.register_policy(DataRetentionPolicy.for_retention_class(retention_class))
        for policy in policies or ():
            self.register_policy(policy)
        self._rebuild_derived_index()

    @property
    def tombstones(self) -> tuple[MemoryTombstone, ...]:
        return tuple(sorted(self._tombstones.values(), key=lambda item: item.memory_id))

    @property
    def contradictions(self) -> tuple[Contradiction, ...]:
        return tuple(sorted(self._contradictions.values(), key=lambda item: item.contradiction_id))

    @property
    def bundles(self) -> tuple[MemoryContextBundle, ...]:
        return tuple(sorted(self._bundles.values(), key=lambda item: item.bundle_id))

    @property
    def audit_log(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(entry) for entry in self._audit)

    def active_records(self) -> tuple[MemoryRecord, ...]:
        return tuple(record for record in self._records.values() if record.lifecycle_state == MemoryLifecycle.ACTIVE.value)

    def record(self, memory_id: str) -> MemoryRecord | None:
        return self._records.get(memory_id)

    def history(self, memory_id: str) -> tuple[MemoryRecord, ...]:
        return tuple(self._history.get(memory_id, ()))

    def register_policy(self, policy_or_document: DataRetentionPolicy | Mapping[str, Any]) -> DataRetentionPolicy:
        policy = validate_data_retention_policy(policy_or_document)
        self._policies_by_id[policy.policy_id] = policy
        if policy.data_class.startswith("MEMORY:"):
            self._policies_by_class[policy.data_class.split(":", 1)[1]] = policy
        self._rebuild_derived_index()
        return policy

    def store_record(self, record_or_document: MemoryRecord | Mapping[str, Any]) -> MemoryRecord:
        record = self._coerce_record(record_or_document)
        if record.memory_id in self._tombstones:
            raise RegistryError(f"{record.memory_id} is tombstoned; resurrection is forbidden")
        if record.lifecycle_state == MemoryLifecycle.TOMBSTONED.value:
            raise RegistryError("use tombstone() to record a deletion state")
        existing = self._records.get(record.memory_id)
        if existing is not None:
            if existing.content_digest == record.content_digest and existing.lifecycle_state == record.lifecycle_state:
                return existing
            raise RegistryError(f"{record.memory_id} already exists; use supersede() or tombstone()")
        self._insert_record(record)
        self._audit.append({
            "event": "STORE",
            "memory_id": record.memory_id,
            "digest": dict(record.content_digest),
            "authority_class": record.authority_class,
            "at": timestamp(),
        })
        self._detect_contradictions()
        self._rebuild_derived_index()
        return record

    def supersede(self, old_memory_id: str, new_record_or_document: MemoryRecord | Mapping[str, Any]) -> MemoryRecord:
        new_record = self._coerce_record(new_record_or_document)
        old_record = self._records.get(old_memory_id)
        if old_record is None:
            raise RegistryError(f"{old_memory_id} is not present in canonical memory")
        if new_record.memory_id == old_memory_id:
            raise RegistryError("supersede requires a new memory_id")
        if new_record.memory_id in self._records or new_record.memory_id in self._tombstones:
            raise RegistryError(f"{new_record.memory_id} already exists or is tombstoned")
        if old_memory_id not in new_record.supersedes:
            raise RegistryError("new record must declare the superseded memory_id")
        if new_record.lifecycle_state != MemoryLifecycle.ACTIVE.value:
            raise RegistryError("superseding record must be ACTIVE")
        updated_old = old_record.mark_superseded()
        self._insert_record(updated_old)
        self._insert_record(new_record)
        self._audit.append({
            "event": "SUPERSEDE",
            "old_memory_id": old_memory_id,
            "new_memory_id": new_record.memory_id,
            "old_digest": dict(old_record.content_digest),
            "new_digest": dict(new_record.content_digest),
            "at": timestamp(),
        })
        self._detect_contradictions()
        self._rebuild_derived_index()
        return new_record

    def expire_record(self, memory_id: str, when: str | None = None) -> MemoryRecord:
        record = self._records.get(memory_id)
        if record is None:
            raise RegistryError(f"{memory_id} is not present in canonical memory")
        updated = record.mark_expired(when)
        self._insert_record(updated)
        self._audit.append({"event": "EXPIRE", "memory_id": memory_id, "at": when or timestamp()})
        self._rebuild_derived_index()
        return updated

    def quarantine_record(self, memory_id: str) -> MemoryRecord:
        record = self._records.get(memory_id)
        if record is None:
            raise RegistryError(f"{memory_id} is not present in canonical memory")
        updated = record.mark_quarantined()
        self._insert_record(updated)
        self._audit.append({"event": "QUARANTINE", "memory_id": memory_id, "at": timestamp()})
        self._rebuild_derived_index()
        return updated

    store = store_record
    expire = expire_record
    quarantine = quarantine_record

    def tombstone(
        self,
        memory_id: str,
        reason: str,
        authority: Principal | Mapping[str, Any],
        purge_required: bool = False,
        issued_at: str | None = None,
    ) -> MemoryTombstone:
        issued_at = issued_at or timestamp()
        existing = self._tombstones.get(memory_id)
        if existing is not None:
            return existing
        tombstone_id = "memtomb_" + compute_digest(canonical({"memory_id": memory_id, "issued_at": issued_at}))["value"][:32]
        tombstone = MemoryTombstone.create(
            tombstone_id=tombstone_id,
            memory_id=memory_id,
            reason=reason,
            authority=authority,
            issued_at=issued_at,
            purge_required=purge_required,
        )
        validate_memory_tombstone(tombstone)
        record = self._records.get(memory_id)
        if record is not None:
            self._insert_record(record.mark_tombstoned(issued_at))
        self._tombstones[memory_id] = tombstone
        entry: dict[str, Any] = {
            "event": "TOMBSTONE",
            "memory_id": memory_id,
            "tombstone_id": tombstone_id,
            "reason": reason,
            "authority": _principal_dict(authority),
            "purge_required": purge_required,
            "at": issued_at,
        }
        if record is not None:
            entry.update(self._policy_for(record).audit_entry("TOMBSTONE", memory_id, issued_at))
        self._audit.append(entry)
        self._detect_contradictions()
        self._rebuild_derived_index()
        return tombstone

    def purge(self, memory_id: str, authority: Principal | Mapping[str, Any], when: str | None = None) -> None:
        tombstone = self._tombstones.get(memory_id)
        record = self._records.get(memory_id)
        if tombstone is None or record is None:
            raise RegistryError("purge requires a tombstoned canonical record")
        policy = self._policy_for(record)
        if not policy.allows_purge(tombstone):
            raise RegistryError(f"retention policy {policy.policy_id} forbids purge for {memory_id}")
        self._records.pop(memory_id, None)
        self._history.pop(memory_id, None)
        entry = {
            "event": "PURGE",
            "memory_id": memory_id,
            "authority": _principal_dict(authority),
            "at": when or timestamp(),
        }
        entry.update(policy.audit_entry("PURGE", memory_id, when or timestamp()))
        self._audit.append(entry)
        self._detect_contradictions()
        self._rebuild_derived_index()

    def apply_retention(self, now: str | datetime | None = None) -> dict[str, int]:
        moment = now.isoformat().replace("+00:00", "Z") if isinstance(now, datetime) else (now or timestamp())
        expired = 0
        for memory_id, record in list(self._records.items()):
            if record.lifecycle_state == MemoryLifecycle.ACTIVE.value and record.valid_until is not None and record.valid_until < moment:
                self._insert_record(record.mark_expired(moment))
                expired += 1
        purged = 0
        for memory_id, tombstone in list(self._tombstones.items()):
            record = self._records.get(memory_id)
            if record is None or not tombstone.requires_purge():
                continue
            if self._policy_for(record).allows_purge(tombstone):
                self.purge(memory_id, tombstone.authority, moment)
                purged += 1
        if expired or purged:
            self._audit.append({"event": "RETENTION_SWEEP", "expired": expired, "purged": purged, "at": moment})
        return {"expired": expired, "purged": purged}

    def search(self, query_or_document: MemoryQuery | Mapping[str, Any], moment: str | None = None) -> MemorySearchResult:
        query = validate_memory_query(query_or_document)
        records = query.ranked(tuple(self._records.values()), moment)
        record_ids = {record.memory_id for record in records}
        contradictions = tuple(
            contradiction
            for contradiction in sorted(self._contradictions.values(), key=lambda item: item.contradiction_id)
            if contradiction.status == "UNRESOLVED" and record_ids & set(contradiction.memory_ids)
        )
        canonical_refs = tuple(record.memory_id for record in records if record.authority_class == MemoryAuthority.CANONICAL_REFERENCE.value)
        return MemorySearchResult(query=query, records=records, unresolved_contradictions=contradictions, canonical_refs=canonical_refs)

    def query(self, query_or_document: MemoryQuery | Mapping[str, Any], moment: str | None = None) -> tuple[MemoryRecord, ...]:
        return self.search(query_or_document, moment).records

    def assemble_context_bundle(
        self,
        query_or_document: MemoryQuery | Mapping[str, Any],
        records: Sequence[MemoryRecord | Mapping[str, Any]] | None = None,
        created_at: str | None = None,
    ) -> MemoryContextBundle:
        query = validate_memory_query(query_or_document)
        selected: Sequence[MemoryRecord | Mapping[str, Any]] = records if records is not None else self.query(query)
        canonical: list[MemoryRecord] = []
        seen: set[str] = set()
        for item in selected:
            record = self._coerce_record(item)
            if record.memory_id in self._tombstones or record.memory_id in seen:
                continue
            stored = self._records.get(record.memory_id)
            if stored is not None:
                if stored.lifecycle_state != MemoryLifecycle.ACTIVE.value:
                    continue
                record = stored
            elif record.lifecycle_state != MemoryLifecycle.ACTIVE.value:
                continue
            seen.add(record.memory_id)
            canonical.append(record)
        bundle = MemoryContextBundle.for_records(query, canonical, created_at=created_at)
        validate_memory_context_bundle(bundle)
        self._bundles[bundle.bundle_id] = bundle
        self._audit.append({
            "event": "CONTEXT_BUNDLE",
            "bundle_id": bundle.bundle_id,
            "query_id": query.query_id,
            "memory_ids": [record.memory_id for record in canonical],
            "bundle_digest": dict(bundle.bundle_digest),
            "at": bundle.created_at,
        })
        return bundle

    def resolve_contradiction(
        self,
        contradiction_id: str,
        resolution_memory_id: str,
        resolved_by: Principal | Mapping[str, Any],
        reason: str,
    ) -> Contradiction:
        contradiction = self._contradictions.get(contradiction_id)
        if contradiction is None:
            raise RegistryError(f"unknown contradiction: {contradiction_id}")
        if resolution_memory_id not in contradiction.memory_ids:
            raise ContradictionResolutionError("resolution must reference one of the conflicting memories")
        resolved = Contradiction(
            contradiction_id=contradiction.contradiction_id,
            memory_ids=contradiction.memory_ids,
            kind=contradiction.kind,
            reason=contradiction.reason,
            status="RESOLVED",
            detected_at=contradiction.detected_at,
            resolved_at=timestamp(),
            resolution_memory_id=resolution_memory_id,
            resolution_reason=reason,
        )
        self._contradictions[contradiction_id] = resolved
        self._audit.append({
            "event": "RESOLVE_CONTRADICTION",
            "contradiction_id": contradiction_id,
            "resolution_memory_id": resolution_memory_id,
            "authority": _principal_dict(resolved_by),
            "reason": reason,
            "at": resolved.resolved_at,
        })
        return resolved

    def export_state(self) -> dict[str, Any]:
        state: dict[str, Any] = {
            "schema_version": self._schema_version,
            "exported_at": timestamp(),
            "derived_index_included": False,
            "records": [record.to_dict() for record in sorted(self._records.values(), key=lambda item: item.memory_id)],
            "tombstones": [tombstone.to_dict() for tombstone in sorted(self._tombstones.values(), key=lambda item: item.memory_id)],
            "retention_policies": [policy.to_dict() for policy in sorted(self._policies_by_id.values(), key=lambda item: item.policy_id)],
            "contradictions": [item.to_dict() for item in self.contradictions],
            "context_bundles": [bundle.to_dict() for bundle in self.bundles],
            "audit": [dict(entry) for entry in self._audit],
        }
        state["state_digest"] = compute_digest(canonical(state))
        return state

    def restore_state(self, state: Mapping[str, Any]) -> "CanonicalMemoryRegistry":
        expected = compute_digest(canonical({key: value for key, value in state.items() if key != "state_digest"}))
        if expected.get("encoding") != state.get("state_digest", {}).get("encoding") or expected.get("value") != state.get("state_digest", {}).get("value"):
            raise RegistryError("exported state digest does not match canonical state")
        tombstone_ids = set()
        for tombstone_document in state.get("tombstones", ()):
            tombstone_ids.add(validate_memory_tombstone(tombstone_document).memory_id)
        for policy_document in state.get("retention_policies", ()):
            validate_data_retention_policy(policy_document)
        for record_document in state.get("records", ()):
            record = validate_memory_record(record_document)
            if record.memory_id in tombstone_ids and record.lifecycle_state not in {MemoryLifecycle.TOMBSTONED.value, MemoryLifecycle.EXPIRED.value}:
                raise RegistryError(f"{record.memory_id} is tombstoned but was restored as {record.lifecycle_state}")
        for contradiction_document in state.get("contradictions", ()):
            Contradiction.from_dict(contradiction_document)
        for bundle_document in state.get("context_bundles", ()):
            validate_memory_context_bundle(bundle_document)
        self._records = {}
        self._history = {}
        self._tombstones = {}
        self._policies_by_id = {}
        self._policies_by_class = {}
        self._contradictions = {}
        self._bundles = {}
        self._audit = []
        for policy_document in state.get("retention_policies", ()):
            self.register_policy(policy_document)
        for retention_class in RetentionClass:
            if retention_class.value not in self._policies_by_class:
                self.register_policy(DataRetentionPolicy.for_retention_class(retention_class))
        for tombstone_document in state.get("tombstones", ()):
            tombstone = validate_memory_tombstone(tombstone_document)
            self._tombstones[tombstone.memory_id] = tombstone
        for record_document in state.get("records", ()):
            record = validate_memory_record(record_document)
            tombstone = self._tombstones.get(record.memory_id)
            if tombstone is not None and record.lifecycle_state not in {MemoryLifecycle.TOMBSTONED.value, MemoryLifecycle.EXPIRED.value}:
                raise RegistryError(f"{record.memory_id} is tombstoned but was restored as {record.lifecycle_state}")
            self._insert_record(record)
        for contradiction_document in state.get("contradictions", ()):
            contradiction = Contradiction.from_dict(contradiction_document)
            self._contradictions[contradiction.contradiction_id] = contradiction
        for bundle_document in state.get("context_bundles", ()):
            bundle = validate_memory_context_bundle(bundle_document)
            self._bundles[bundle.bundle_id] = bundle
        self._audit = [dict(entry) for entry in state.get("audit", ())]
        self._rebuild_derived_index()
        self._audit.append({"event": "RESTORE", "at": timestamp(), "record_count": len(self._records)})
        return self

    def _coerce_record(self, record_or_document: MemoryRecord | Mapping[str, Any]) -> MemoryRecord:
        return validate_memory_record(record_or_document)

    def _insert_record(self, record: MemoryRecord) -> None:
        self._policy_for(record)
        self._records[record.memory_id] = record
        self._history.setdefault(record.memory_id, []).append(record)

    def _policy_for(self, record: MemoryRecord) -> DataRetentionPolicy:
        policy = self._policies_by_class.get(record.retention_class)
        if policy is None:
            policy = self.register_policy(DataRetentionPolicy.for_retention_class(record.retention_class))
        return policy

    def _detect_contradictions(self) -> None:
        active = [record for record in self._records.values() if record.lifecycle_state == MemoryLifecycle.ACTIVE.value]
        for index, left in enumerate(active):
            for right in active[index + 1:]:
                if left.memory_id == right.memory_id:
                    continue
                is_conflict, reason = _is_contradiction(left, right)
                if not is_conflict:
                    continue
                memory_ids = tuple(sorted({left.memory_id, right.memory_id}))
                contradiction_id = "contradiction_" + compute_digest(canonical({"memory_ids": memory_ids, "reason": reason}))["value"][:32]
                if contradiction_id not in self._contradictions:
                    self._contradictions[contradiction_id] = Contradiction(
                        contradiction_id=contradiction_id,
                        memory_ids=memory_ids,
                        kind="MEMORY_CONTRADICTION",
                        reason=reason,
                        status="UNRESOLVED",
                        detected_at=timestamp(),
                    )

    def _rebuild_derived_index(self) -> None:
        by_scope: dict[str, list[str]] = {}
        by_kind: dict[str, list[str]] = {}
        tokens: dict[str, tuple[str, ...]] = {}
        for record in self._records.values():
            if record.lifecycle_state != MemoryLifecycle.ACTIVE.value or record.memory_id in self._tombstones:
                continue
            by_scope.setdefault(f"{record.scope_type}:{record.scope_ref}", []).append(record.memory_id)
            by_kind.setdefault(record.kind, []).append(record.memory_id)
            tokens[record.memory_id] = tuple(sorted({token for token in re.split(r"[^a-z0-9]+", record.text.lower()) if token}))
        self._derived_index = {
            "by_scope": {key: sorted(value) for key, value in sorted(by_scope.items())},
            "by_kind": {key: sorted(value) for key, value in sorted(by_kind.items())},
            "tokens": {key: value for key, value in sorted(tokens.items())},
        }
