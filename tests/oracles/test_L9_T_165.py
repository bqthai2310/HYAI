"""Oracle test for L9-REQ-DLV-002 / L9-T-165."""
from hyai.workflow.correction import (
    CorrectionLoopExhaustedError,
    InternalCorrectionLoop,
    PrematurePODeliveryError,
)
from ._support import oracle

def _good() -> bool:
    # 1. Failed delivery criterion triggers bounded internal repair and passes on retest
    loop = InternalCorrectionLoop(max_correction_cycles=3)
    readiness_failing = {"state": "CORRECTION_REQUIRED", "criterion_results": [{"criterion_id": "c1", "result": "FAIL"}]}
    remediated = loop.evaluate_and_correct(
        readiness_failing,
        remediation_action=lambda: [{"criterion_id": "c1", "result": "PASS"}],
    )
    assert remediated["status"] == "CORRECTED" and loop.current_cycle == 1

    # 2. Premature delivery to PO while in CORRECTION_REQUIRED state raises PrematurePODeliveryError
    premature_loop = InternalCorrectionLoop(max_correction_cycles=3, po_delivery_attempted=True)
    try:
        premature_loop.evaluate_and_correct(
            readiness_failing,
            remediation_action=lambda: [{"criterion_id": "c1", "result": "PASS"}],
        )
        return False
    except PrematurePODeliveryError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_165():
    oracle("L9-REQ-DLV-002", "L9-T-165", _good, _bad)
