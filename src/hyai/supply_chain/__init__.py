"""HYAI supply_chain boundary."""

from .attestation import (
    DigestBindingError,
    IncompleteBOMError,
    IncompleteModelProvenanceError,
    SupplyChainError,
    UntrustedBuilderError,
    UntrustedDependencyError,
    admit_dependency,
    assert_exact_digest_binding,
    create_supply_chain_attestation,
    record_build_reproducibility,
    verify_ai_model_provenance,
    verify_bom_metadata,
    verify_builder_policy,
)

__all__ = [
    "DigestBindingError",
    "IncompleteBOMError",
    "IncompleteModelProvenanceError",
    "SupplyChainError",
    "UntrustedBuilderError",
    "UntrustedDependencyError",
    "admit_dependency",
    "assert_exact_digest_binding",
    "create_supply_chain_attestation",
    "record_build_reproducibility",
    "verify_ai_model_provenance",
    "verify_bom_metadata",
    "verify_builder_policy",
]
