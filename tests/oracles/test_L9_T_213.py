"""L9-REQ-SCA-005 / L9-T-213: Dependency without required integrity/provenance cannot enter trusted build."""
from hyai.supply_chain import admit_dependency, UntrustedDependencyError
from ._support import oracle


def test_l9_t_213_dependency_admission_gate():
    def _pos():
        return admit_dependency(
            dependency_id="dep_requests_v2",
            has_integrity_hash=True,
            has_provenance=True,
            policy_approved=True,
        )

    def _neg():
        try:
            admit_dependency(
                dependency_id="dep_unverified_payload",
                has_integrity_hash=False,
                has_provenance=False,
                policy_approved=False,
            )
            return True
        except UntrustedDependencyError:
            return False

    oracle("L9-REQ-SCA-005", "L9-T-213", _pos, _neg)
