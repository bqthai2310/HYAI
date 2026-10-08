"""L9-REQ-DLV-004 / L9-T-167: Task/Program PASS cannot directly mark Product DELIVERY_READY."""
from hyai.delivery.bundle import assert_no_task_pass_shortcut, DeliveryShortcutError
from ._support import oracle


def test_l9_t_167_no_task_pass_shortcut():
    def _pos():
        return assert_no_task_pass_shortcut(
            task_passed=True,
            readiness_evaluated=True,
            delivery_readiness_ref="deliveryready_f14_001",
        )

    def _neg():
        try:
            assert_no_task_pass_shortcut(
                task_passed=True,
                readiness_evaluated=False,
                delivery_readiness_ref=None,
            )
            return True
        except DeliveryShortcutError:
            return False

    oracle("L9-REQ-DLV-004", "L9-T-167", _pos, _neg)
