"""Supply chain attestation, SBOM, dependency admission, build reproducibility, and AI model provenance (L9-REQ-SCA-001..007)."""
from __future__ import annotations

from typing import Any, Mapping, Sequence
from uuid import uuid4

from hyai._contracts import content_digest, timestamp, validate


class SupplyChainError(ValueError):
    """Raised when supply chain integrity, attestation, or dependency admission fails."""


class UntrustedDependencyError(SupplyChainError):
    """Raised when an untrusted or unprovenanced dependency attempts to enter trusted build (L9-REQ-SCA-005)."""


class UntrustedBuilderError(SupplyChainError):
    """Raised when attestation was not produced by a trusted builder (L9-REQ-SCA-003)."""


class IncompleteBOMError(SupplyChainError):
    """Raised when release BOM metadata is missing required dependencies (L9-REQ-SCA-002)."""


class IncompleteModelProvenanceError(SupplyChainError):
    """Raised when AI model or dataset dependency lacks license, version, or integrity (L9-REQ-SCA-007)."""


class DigestBindingError(SupplyChainError):
    """Raised when attestation is bound to a release name rather than an exact artifact digest (L9-REQ-SCA-004)."""


def create_supply_chain_attestation(
    *,
    subject_digest: Mapping[str, str],
    source_revision_ref: str,
    builder_identity: Mapping[str, str],
    materials: Sequence[str],
    sbom_refs: Sequence[str],
    provenance_refs: Sequence[str],
    verification_results: Sequence[str],
    attestation_id: str | None = None,
    issued_at: str | None = None,
    schema_version: str = "2.1.0",
) -> dict[str, Any]:
    """L9-REQ-SCA-001: Material release binds source revision, build, and artifact provenance."""
    aid = attestation_id or f"supplyatt_{uuid4().hex[:16]}"
    doc = {
        "schema_version": schema_version,
        "attestation_id": aid,
        "subject_digest": dict(subject_digest),
        "source_revision_ref": source_revision_ref,
        "builder_identity": dict(builder_identity),
        "materials": list(materials),
        "sbom_refs": list(sbom_refs),
        "provenance_refs": list(provenance_refs),
        "verification_results": list(verification_results),
        "issued_at": issued_at or timestamp(),
    }
    doc["content_digest"] = content_digest(doc)
    validate(doc, "supply_chain_attestation.schema.json", SupplyChainError)
    return doc


def verify_bom_metadata(
    *,
    has_software_bom: bool,
    has_dependency_bom: bool,
    ai_model_deps_present: bool = False,
    has_ai_model_bom: bool = False,
) -> bool:
    """L9-REQ-SCA-002: Material release has dependency/software/AI/data BOM metadata."""
    if not (has_software_bom and has_dependency_bom):
        raise IncompleteBOMError("Release requires complete software and dependency BOM metadata (L9-REQ-SCA-002)")
    if ai_model_deps_present and not has_ai_model_bom:
        raise IncompleteBOMError("AI model dependencies require complete model/data BOM metadata (L9-REQ-SCA-002)")
    return True


def verify_builder_policy(
    attestation: Mapping[str, Any],
    trusted_builders: Sequence[str] = ("builder_canonical_ci", "builder_secure_enclave"),
) -> bool:
    """L9-REQ-SCA-003: Attestation is verified against trusted builder policy."""
    builder = attestation.get("builder_identity", {}).get("id", "")
    if builder not in trusted_builders:
        raise UntrustedBuilderError(f"Builder '{builder}' is not authorized by trusted builder policy (L9-REQ-SCA-003)")
    return True


def assert_exact_digest_binding(
    *,
    bound_subject_digest: Mapping[str, Any],
    exact_artifact_bytes_digest: Mapping[str, Any],
    release_name_only: bool = False,
) -> bool:
    """L9-REQ-SCA-004: Attestation/SBOM/provenance bind exact artifact digest, not release name only."""
    if release_name_only:
        raise DigestBindingError("Attestation cannot bind to release name only; exact digest is required (L9-REQ-SCA-004)")
    if bound_subject_digest.get("value") != exact_artifact_bytes_digest.get("value"):
        raise DigestBindingError("Bound subject digest does not match exact artifact digest (L9-REQ-SCA-004)")
    return True


def admit_dependency(
    *,
    dependency_id: str,
    has_integrity_hash: bool,
    has_provenance: bool,
    policy_approved: bool,
) -> bool:
    """L9-REQ-SCA-005: Dependency without required integrity/provenance cannot enter trusted build."""
    if not (has_integrity_hash and has_provenance and policy_approved):
        raise UntrustedDependencyError(
            f"Dependency '{dependency_id}' lacks required integrity or provenance and is rejected (L9-REQ-SCA-005)"
        )
    return True


def record_build_reproducibility(
    *,
    is_deterministic: bool,
    reproducibility_evidence: str | None = None,
    explicit_limitation: str | None = None,
) -> dict[str, Any]:
    """L9-REQ-SCA-006: Release records deterministic build evidence or explicit limitation."""
    if not is_deterministic and not explicit_limitation:
        raise SupplyChainError("Non-deterministic build must record an explicit limitation (L9-REQ-SCA-006)")
    return {
        "is_deterministic": is_deterministic,
        "evidence": reproducibility_evidence or explicit_limitation,
    }


def verify_ai_model_provenance(
    *,
    model_id: str,
    version: str,
    license_id: str,
    integrity_digest: str,
    source_origin: str,
) -> bool:
    """L9-REQ-SCA-007: AI model/dataset dependencies carry provenance, version, license, and integrity."""
    if not (model_id and version and license_id and integrity_digest and source_origin):
        raise IncompleteModelProvenanceError(
            f"AI model '{model_id}' lacks complete provenance, version, license, or integrity references (L9-REQ-SCA-007)"
        )
    return True
