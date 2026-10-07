"""Independent review, immutable subject binding, and verdict validation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from hyai.compatibility.crypto import validate_digest_spec
from hyai.constitution.authority import AuthorityClass, AuthorityDecision, Principal, PrincipalType


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _principal_dict(value: Principal | Mapping[str, Any]) -> dict[str, str]:
    if isinstance(value, Principal):
        return {"principal_type": value.principal_type.value, "id": value.id}
    return {"principal_type": str(value["principal_type"]), "id": str(value["id"])}


@dataclass(frozen=True)
class ReviewSubject:
    head_commit_sha: str
    files: Sequence[Mapping[str, Any]]
    config_digests: Sequence[Mapping[str, Any] | str] = ()
    acceptance_versions: Sequence[str] = ()
    policy_snapshot_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "files", tuple(MappingProxyType(dict(item)) for item in self.files))
        object.__setattr__(self, "config_digests", tuple(MappingProxyType(dict(item)) if isinstance(item, Mapping) else item for item in self.config_digests))
        object.__setattr__(self, "acceptance_versions", tuple(self.acceptance_versions))

    def digest(self) -> dict[str, str]:
        payload = {"head_commit_sha": self.head_commit_sha, "files": sorted((_plain(item) for item in self.files), key=lambda item: item.get("path", "")), "config_digests": sorted((_plain(item) for item in self.config_digests), key=lambda item: _canonical(item)), "acceptance_versions": sorted(self.acceptance_versions), "policy_snapshot_id": self.policy_snapshot_id}
        return {"algorithm": "sha256", "encoding": "hex", "value": hashlib.sha256(_canonical(payload)).hexdigest()}

    @property
    def subject_id(self) -> str:
        """A stable content address, rather than a caller-provided identifier."""
        return "subject_" + self.digest()["value"]


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    producer: Principal | Mapping[str, Any]
    subject_ref: str
    content_digest: Mapping[str, str]
    schema_version: str = "2.0.0"
    metadata: Mapping[str, Any] | None = None
    type: str = "review_evidence"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    media_type: str = "application/json"
    storage_ref: str = "inline://evidence"
    criterion_refs: Sequence[str] = ("review",)

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id, "type": self.type, "producer": _principal_dict(self.producer), "subject_ref": self.subject_ref, "created_at": self.created_at, "media_type": self.media_type, "storage_ref": self.storage_ref, "digest": dict(self.content_digest), "criterion_refs": list(self.criterion_refs)}


def validate_evidence_item(item: EvidenceItem | Mapping[str, Any]) -> tuple[bool, str]:
    document = item.to_dict() if isinstance(item, EvidenceItem) else dict(item)
    if "content_digest" in document and "digest" not in document:
        document["digest"] = document.pop("content_digest")
    digest = document.get("digest", {})
    producer, subject = document.get("producer"), document.get("subject_ref")
    if not subject or not producer or not isinstance(producer, Mapping) or not producer.get("id"):
        return False, "evidence requires a non-empty digest, producer, and subject_ref"
    if not validate_digest_spec(dict(digest)):
        return False, "evidence digest is invalid"
    schema = json.loads((Path(__file__).resolve().parents[3] / "schemas" / "evidence_bundle.schema.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema["properties"]["items"]["items"], format_checker=FormatChecker()).iter_errors(document))
    if errors:
        return False, "; ".join(error.message for error in errors)
    return True, "valid evidence"


@dataclass(frozen=True)
class ReviewRequest:
    review_request_id: str
    requested_by: Principal
    head_commit_sha: str


@dataclass(frozen=True)
class ReviewVerdict:
    review_request_id: str
    reviewed_commit_sha: str
    review_subject_digest: Mapping[str, str]
    reviewer: Principal
    verdict: str
    criterion_results: Sequence[Mapping[str, Any]] = field(default_factory=tuple)


def validate_verdict(request: ReviewRequest, subject: ReviewSubject, verdict: ReviewVerdict, current_target_commit_sha: str | None = None) -> tuple[bool, str]:
    target_sha = current_target_commit_sha or subject.head_commit_sha
    if verdict.review_request_id != request.review_request_id:
        return False, "verdict is for another review request"
    if verdict.reviewed_commit_sha != target_sha or request.head_commit_sha != target_sha:
        return False, "verdict is not bound to the exact head commit"
    if dict(verdict.review_subject_digest) != subject.digest():
        return False, "verdict is not bound to the exact review subject digest"
    requester, reviewer = request.requested_by, verdict.reviewer
    if requester.principal_type is PrincipalType.EXECUTOR and (reviewer.principal_type is PrincipalType.EXECUTOR or reviewer.id == requester.id):
        return False, "NO_SELF_APPROVAL violated"
    if verdict.verdict == "PASS":
        if reviewer.principal_type not in {PrincipalType.INDEPENDENT_REVIEWER, PrincipalType.ASSURANCE_SERVICE}:
            return False, "PASS requires an independent reviewer or assurance service"
        if not verdict.criterion_results or any(result.get("result") != "PASS" or not result.get("evidence_refs") for result in verdict.criterion_results):
            return False, "PASS requires passing criteria with evidence"
    return True, "valid verdict"


def validate_adversarial_coverage(subject: ReviewSubject, criteria_results: Sequence[Mapping[str, Any]], risk_level: str) -> tuple[bool, str]:
    if risk_level.lower() not in {"high", "critical"}:
        return True, "adversarial coverage not required"
    adversarial = [result for result in criteria_results if any(token in str(result.get(field, "")).lower() for field in ("criterion_id", "type", "category", "name") for token in ("adversarial", "negative"))]
    if not adversarial or any(result.get("result") != "PASS" for result in adversarial):
        return False, "high-risk review requires passing adversarial or negative checks"
    return True, "adversarial coverage complete"


def can_promote_to_production(verdict: ReviewVerdict, authorization: AuthorityDecision | Principal | Mapping[str, Any] | None) -> bool:
    """A passing review remains distinct from release authorization."""
    if verdict.verdict != "PASS" or authorization is None:
        return False
    if isinstance(authorization, AuthorityDecision):
        return authorization.status == "APPROVED" and authorization.required_class is AuthorityClass.A4 and authorization.authority.principal_type is PrincipalType.PO
    if isinstance(authorization, Principal):
        return authorization.principal_type in {PrincipalType.PO, PrincipalType.RELEASE_MANAGER}
    principal = authorization.get("authority", authorization.get("principal", authorization))
    role = principal.get("principal_type") if isinstance(principal, Mapping) else None
    return authorization.get("status", "APPROVED") == "APPROVED" and authorization.get("required_class", authorization.get("authority_class", "A4")) == "A4" and role in {"PO", "RELEASE_MANAGER"}
