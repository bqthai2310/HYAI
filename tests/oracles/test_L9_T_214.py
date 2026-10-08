"""L9-REQ-SCA-006 / L9-T-214: Release records deterministic build evidence or explicit limitation."""
from hyai.supply_chain import record_build_reproducibility
from ._support import oracle


def test_l9_t_214_build_reproducibility():
    def _pos():
        rec = record_build_reproducibility(
            is_deterministic=True,
            reproducibility_evidence="sha256_matches_across_independent_builders",
        )
        return rec["is_deterministic"] and len(rec["evidence"]) > 0

    def _neg():
        try:
            record_build_reproducibility(
                is_deterministic=False,
                reproducibility_evidence=None,
                explicit_limitation=None,
            )
            return True
        except ValueError:
            return False

    oracle("L9-REQ-SCA-006", "L9-T-214", _pos, _neg)
