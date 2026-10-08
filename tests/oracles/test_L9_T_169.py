"""L9-REQ-DLV-006 / L9-T-169: Delivery includes observability/SLO/operations readiness when Product is operational software."""
from hyai.delivery.bundle import verify_operational_readiness, OperationalReadinessError
from ._support import oracle


def test_l9_t_169_operational_readiness_verification():
    def _pos():
        return verify_operational_readiness(
            product_type="OPERATIONAL_SOFTWARE",
            observability_ready=True,
            slo_monitored=True,
            operations_ready=True,
        )

    def _neg():
        try:
            verify_operational_readiness(
                product_type="OPERATIONAL_SOFTWARE",
                observability_ready=True,
                slo_monitored=False,
                operations_ready=False,
            )
            return True
        except OperationalReadinessError:
            return False

    oracle("L9-REQ-DLV-006", "L9-T-169", _pos, _neg)
