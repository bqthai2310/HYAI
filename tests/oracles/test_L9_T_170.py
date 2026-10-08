"""L9-REQ-DLV-007 / L9-T-170: Required rollback/restore/recovery path is tested before DELIVERY_READY."""
from hyai.delivery.bundle import verify_recovery_readiness, RecoveryReadinessError
from ._support import oracle


def test_l9_t_170_recovery_readiness_tested():
    def _pos():
        return verify_recovery_readiness(
            rollback_tested=True,
            restore_verified=True,
            recovery_plan_ref="plan_dr_production_v1",
        )

    def _neg():
        try:
            verify_recovery_readiness(
                rollback_tested=False,
                restore_verified=False,
                recovery_plan_ref="",
            )
            return True
        except RecoveryReadinessError:
            return False

    oracle("L9-REQ-DLV-007", "L9-T-170", _pos, _neg)
