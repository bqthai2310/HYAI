"""L9-REQ-DLV-009 / L9-T-172: Non-converging correction returns Blocker Package rather than false DELIVERY_READY."""
from hyai.delivery.bundle import handle_correction_outcome, NonConvergingCorrectionError
from ._support import oracle


def test_l9_t_172_non_converging_correction_blocker_package():
    def _pos():
        try:
            handle_correction_outcome(
                converged=False,
                product_ref="product_f14",
                unresolved_criteria=["criterion_latency_budget"],
                attempts=5,
            )
            return False
        except NonConvergingCorrectionError:
            return True

    def _neg():
        res = handle_correction_outcome(
            converged=True,
            product_ref="product_f14",
        )
        return res.get("status") != "CONVERGED"

    oracle("L9-REQ-DLV-009", "L9-T-172", _pos, _neg)
