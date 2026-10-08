"""Product delivery bundle, runnable deployment verification, operational readiness, and blocker packages (L9-REQ-DLV-004..009)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from uuid import uuid4

from hyai._contracts import canonical, content_digest, validate
from hyai.compatibility.crypto import compute_digest


class DeliveryShortcutError(ValueError):
    """Raised when Task/Program PASS attempts to mark Product DELIVERY_READY without readiness evaluation (L9-REQ-DLV-004)."""


class DeploymentVerificationError(ValueError):
    """Raised when required deployment or environment verification is missing (L9-REQ-DLV-005)."""


class OperationalReadinessError(ValueError):
    """Raised when operational software lacks observability, SLO, or operational readiness (L9-REQ-DLV-006)."""


class NonConvergingCorrectionError(ValueError):
    """Raised when non-converging correction returns a Blocker Package instead of false delivery (L9-REQ-DLV-009)."""


@dataclass(frozen=True)
class BlockerPackage:
    schema_version: str
    blocker_id: str
    product_ref: str
    unresolved_criteria: tuple[str, ...]
    correction_attempts: int
    reason: str
    content_digest: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "blocker_id": self.blocker_id,
            "product_ref": self.product_ref,
            "unresolved_criteria": list(self.unresolved_criteria),
            "correction_attempts": self.correction_attempts,
            "reason": self.reason,
            "content_digest": dict(self.content_digest),
        }


def create_blocker_package(
    *,
    product_ref: str,
    unresolved_criteria: Sequence[str],
    correction_attempts: int,
    reason: str,
    blocker_id: str | None = None,
    schema_version: str = "2.1.0",
) -> BlockerPackage:
    bid = blocker_id or f"blocker_{uuid4().hex[:16]}"
    payload = {
        "schema_version": schema_version,
        "blocker_id": bid,
        "product_ref": product_ref,
        "unresolved_criteria": tuple(unresolved_criteria),
        "correction_attempts": correction_attempts,
        "reason": reason,
    }
    digest = compute_digest(canonical(payload))
    return BlockerPackage(
        schema_version=schema_version,
        blocker_id=bid,
        product_ref=product_ref,
        unresolved_criteria=tuple(unresolved_criteria),
        correction_attempts=correction_attempts,
        reason=reason,
        content_digest=digest,
    )


def assert_no_task_pass_shortcut(
    *,
    task_passed: bool,
    readiness_evaluated: bool,
    delivery_readiness_ref: str | None = None,
) -> bool:
    """L9-REQ-DLV-004: Task/Program PASS cannot directly mark Product DELIVERY_READY."""
    if task_passed and (not readiness_evaluated or not delivery_readiness_ref):
        raise DeliveryShortcutError(
            "Task or Program PASS cannot directly mark Product DELIVERY_READY without a verified DeliveryReadinessRecord (L9-REQ-DLV-004)"
        )
    return True


def verify_runnable_deployment(
    *,
    environment_verified: bool,
    config_verified: bool,
    deploy_verified: bool,
    start_verified: bool,
) -> bool:
    """L9-REQ-DLV-005: Delivery includes environment/config/deploy/start verification."""
    if not (environment_verified and config_verified and deploy_verified and start_verified):
        raise DeploymentVerificationError(
            "Delivery requires environment, configuration, deployment, and start verification (L9-REQ-DLV-005)"
        )
    return True


def verify_operational_readiness(
    *,
    product_type: str,
    observability_ready: bool,
    slo_monitored: bool,
    operations_ready: bool,
) -> bool:
    """L9-REQ-DLV-006: Operational software requires observability/SLO/operations readiness."""
    if product_type.upper() in ("OPERATIONAL_SOFTWARE", "SERVICE", "PRODUCTION_APPLICATION"):
        if not (observability_ready and slo_monitored and operations_ready):
            raise OperationalReadinessError(
                "Operational software requires complete observability, SLO monitoring, and operational readiness (L9-REQ-DLV-006)"
            )
    return True


def create_product_delivery_bundle(
    *,
    product_ref: str,
    release_subject_digest: Mapping[str, str],
    artifact_refs: Sequence[str],
    config_refs: Sequence[str],
    documentation_refs: Sequence[str],
    evidence_refs: Sequence[str],
    delivery_readiness_ref: str,
    rollback_ref: str,
    bundle_id: str | None = None,
    schema_version: str = "2.1.0",
) -> dict[str, Any]:
    """L9-REQ-DLV-008: Complete ProductDeliveryBundle bound to exact release subject."""
    bid = bundle_id or f"deliverybundle_{uuid4().hex[:16]}"
    doc = {
        "schema_version": schema_version,
        "bundle_id": bid,
        "product_ref": product_ref,
        "release_subject_digest": dict(release_subject_digest),
        "artifact_refs": list(artifact_refs),
        "config_refs": list(config_refs),
        "documentation_refs": list(documentation_refs),
        "evidence_refs": list(evidence_refs),
        "delivery_readiness_ref": delivery_readiness_ref,
        "rollback_ref": rollback_ref,
    }
    doc["content_digest"] = content_digest(doc)
    validate(doc, "product_delivery_bundle.schema.json", ValueError)
    return doc


def handle_correction_outcome(
    *,
    converged: bool,
    product_ref: str,
    unresolved_criteria: Sequence[str] = (),
    attempts: int = 1,
) -> BlockerPackage | dict[str, str]:
    """L9-REQ-DLV-009: Non-converging correction returns Blocker Package rather than false delivery."""
    if not converged:
        pkg = create_blocker_package(
            product_ref=product_ref,
            unresolved_criteria=unresolved_criteria,
            correction_attempts=attempts,
            reason="Correction loop failed to converge within bounded budget",
        )
        raise NonConvergingCorrectionError(
            f"Non-converging correction produced blocker package {pkg.blocker_id} (L9-REQ-DLV-009)"
        )
    return {"status": "CONVERGED"}
