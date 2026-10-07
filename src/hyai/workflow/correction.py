"""Bounded internal correction and retest loop for delivery criteria (L9-REQ-DLV-002)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from hyai.delivery.contract import DeliveryError, DeliveryReadinessManager
from hyai.workflow.instance import WorkflowError


class CorrectionLoopExhaustedError(WorkflowError):
    """Raised when internal correction attempts exceed the configured cycle limit without passing."""


class PrematurePODeliveryError(WorkflowError):
    """Raised when uncorrected or failed delivery is submitted to Product Owner without passing criteria."""


@dataclass
class InternalCorrectionLoop:
    max_correction_cycles: int = 3
    current_cycle: int = 0
    po_delivery_attempted: bool = False

    def evaluate_and_correct(
        self,
        readiness_record: Mapping[str, Any],
        remediation_action: Callable[[], Sequence[Mapping[str, Any]]],
    ) -> dict[str, Any]:
        """Triggers bounded internal correction/retest when delivery criterion fails (L9-REQ-DLV-002)."""
        state = readiness_record.get("state")

        if state == "CORRECTION_REQUIRED":
            if self.po_delivery_attempted:
                raise PrematurePODeliveryError("Delivery submitted to PO while in CORRECTION_REQUIRED state")

            while self.current_cycle < self.max_correction_cycles:
                self.current_cycle += 1
                # Execute internal bounded repair and retest
                new_results = remediation_action()
                if all(item.get("result") == "PASS" for item in new_results):
                    return {
                        "status": "CORRECTED",
                        "cycles_used": self.current_cycle,
                        "results": list(new_results),
                    }

            raise CorrectionLoopExhaustedError(
                f"Internal correction loop exhausted after {self.current_cycle} cycles without achieving PASS"
            )

        if state == "DELIVERY_READY":
            return {"status": "DELIVERY_READY", "cycles_used": 0, "results": list(readiness_record.get("criterion_results", []))}

        return {"status": state, "cycles_used": 0, "results": list(readiness_record.get("criterion_results", []))}
