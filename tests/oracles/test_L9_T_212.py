"""L9-REQ-SCA-004 / L9-T-212: Attestation/SBOM/provenance bind exact artifact digest, not release name only."""
from hyai.supply_chain import assert_exact_digest_binding, DigestBindingError
from ._support import oracle


def test_l9_t_212_exact_digest_binding():
    def _pos():
        digest = {"algorithm": "sha256", "encoding": "hex", "value": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"}
        return assert_exact_digest_binding(
            bound_subject_digest=digest,
            exact_artifact_bytes_digest=digest,
            release_name_only=False,
        )

    def _neg():
        digest = {"algorithm": "sha256", "encoding": "hex", "value": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"}
        try:
            assert_exact_digest_binding(
                bound_subject_digest=digest,
                exact_artifact_bytes_digest=digest,
                release_name_only=True,
            )
            return True
        except DigestBindingError:
            return False

    oracle("L9-REQ-SCA-004", "L9-T-212", _pos, _neg)
