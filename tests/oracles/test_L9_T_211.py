"""L9-REQ-SCA-003 / L9-T-211: Supply-chain attestation verified against trusted builder policy."""
from hyai.supply_chain import verify_builder_policy, UntrustedBuilderError
from ._support import oracle


def test_l9_t_211_trusted_builder_policy():
    def _pos():
        att = {"builder_identity": {"id": "builder_canonical_ci"}}
        return verify_builder_policy(att)

    def _neg():
        att = {"builder_identity": {"id": "rogue_external_builder"}}
        try:
            verify_builder_policy(att)
            return True
        except UntrustedBuilderError:
            return False

    oracle("L9-REQ-SCA-003", "L9-T-211", _pos, _neg)
