"""L9-REQ-SCA-001 / L9-T-209: Material release binds source revision/build/artifact provenance."""
from hyai.supply_chain import create_supply_chain_attestation
from ._support import oracle


def test_l9_t_209_release_provenance_binding():
    def _pos():
        att = create_supply_chain_attestation(
            subject_digest={"algorithm": "sha256", "encoding": "hex", "value": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"},
            source_revision_ref="git_commit_sha_8a1d6e443cbc5388ccb93ffced0eda497236f360",
            builder_identity={"principal_type": "CI", "id": "builder_canonical_ci"},
            materials=["pip_lock_sha256_abcdef"],
            sbom_refs=["sbom_spdx_v1"],
            provenance_refs=["slsa_provenance_v1"],
            verification_results=["signature_verified_ok"],
        )
        return att["attestation_id"].startswith("supplyatt_") and len(att["provenance_refs"]) > 0

    def _neg():
        try:
            create_supply_chain_attestation(
                subject_digest={"algorithm": "sha256", "encoding": "hex", "value": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"},
                source_revision_ref="",
                builder_identity={"principal_type": "CI", "id": "builder_canonical_ci"},
                materials=[],
                sbom_refs=[],
                provenance_refs=[],
                verification_results=[],
            )
            return True
        except ValueError:
            return False

    oracle("L9-REQ-SCA-001", "L9-T-209", _pos, _neg)
