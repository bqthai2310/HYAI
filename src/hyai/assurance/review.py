"""Independent review, immutable subject binding, and verdict validation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from hyai.constitution.authority import Principal, PrincipalType


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class ReviewSubject:
    head_commit_sha: str
    files: Sequence[Mapping[str, Any]]
    config_digests: Sequence[Mapping[str, Any] | str] = ()
    acceptance_versions: Sequence[str] = ()
    policy_snapshot_id: str = ""

    def digest(self) -> dict[str, str]:
        """A stable SHA-256 digest over all review-relevant state."""
        payload = {
            "head_commit_sha": self.head_commit_sha,
            "files": sorted((dict(item) for item in self.files), key=lambda item: item.get("path", "")),
            "config_digests": sorted(self.config_digests, key=lambda item: _canonical(item)),
            "acceptance_versions": sorted(self.acceptance_versions),
            "policy_snapshot_id": self.policy_snapshot_id,
        }
        return {"algorithm": "sha256", "encoding": "hex", "value": hashlib.sha256(_canonical(payload)).hexdigest()}


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


def validate_verdict(request: ReviewRequest, subject: ReviewSubject, verdict: ReviewVerdict) -> tuple[bool, str]:
    if verdict.review_request_id != request.review_request_id:
        return False, "verdict is for another review request"
    if verdict.reviewed_commit_sha != request.head_commit_sha or verdict.reviewed_commit_sha != subject.head_commit_sha:
        return False, "verdict is not bound to the exact head commit"
    if dict(verdict.review_subject_digest) != subject.digest():
        return False, "verdict is not bound to the exact review subject digest"
    requester, reviewer = request.requested_by, verdict.reviewer
    if requester.principal_type is PrincipalType.EXECUTOR:
        if reviewer.principal_type is PrincipalType.EXECUTOR or reviewer.id == requester.id:
            return False, "NO_SELF_APPROVAL violated"
    if verdict.verdict == "PASS":
        if reviewer.principal_type not in {PrincipalType.INDEPENDENT_REVIEWER, PrincipalType.ASSURANCE_SERVICE}:
            return False, "PASS requires an independent reviewer or assurance service"
        if not verdict.criterion_results or any(result.get("result") != "PASS" or not result.get("evidence_refs") for result in verdict.criterion_results):
            return False, "PASS requires passing criteria with evidence"
    return True, "valid verdict"
