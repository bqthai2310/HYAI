"""Oracle test for L9-REQ-DAT-002 / L9-T-125."""
from hyai.workflow.data_governance import create_data_retention_policy
from ._support import oracle

def _good() -> bool:
    policy = create_data_retention_policy(
        policy_id="retention_audit_logs",
        data_class="EVIDENCE",
        retention_period="7y",
        deletion_semantics="CRYPTO_ERASURE_AND_PURGE",
        backup_required=True,
    )
    return policy.retention_period == "7y" and policy.deletion_semantics == "CRYPTO_ERASURE_AND_PURGE"

def _bad() -> bool:
    return False

def test_l9_t_125():
    oracle("L9-REQ-DAT-002", "L9-T-125", _good, _bad)
