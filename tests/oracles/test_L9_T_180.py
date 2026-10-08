"""Oracle test for L9-REQ-UPG-001 / L9-T-180."""
from hyai.observability.lifecycle import SignalSeverity, SignalType, create_upgrade_signal
from ._support import oracle

def _good() -> bool:
    signal = create_upgrade_signal(
        signal_id="upgradesignal_security_cve_99",
        signal_type=SignalType.SECURITY,
        subject_ref="dep_openssl_3.0",
        evidence_refs=["ev_nvd_cve_2026_1111"],
        severity=SignalSeverity.CRITICAL,
    )
    return signal.signal_type == "SECURITY" and signal.severity == "CRITICAL"

def _bad() -> bool:
    return False

def test_l9_t_180():
    oracle("L9-REQ-UPG-001", "L9-T-180", _good, _bad)
