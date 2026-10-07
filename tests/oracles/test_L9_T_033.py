"""Oracle test for L9-REQ-CAP-003 / L9-T-033."""
from hyai.capabilities.worker import (
    LeaseExpiredError,
    ResourceLease,
    UnpermittedActionError,
    create_resource_lease,
)
from ._support import oracle

def _good() -> bool:
    lease = create_resource_lease(
        lease_id="lease_worker_01",
        task_id="task_build",
        task_revision=1,
        worker_id="worker_py_01",
        expires_at="2099-01-01T00:00:00Z",
        permitted_actions=["action_read", "action_write"],
    )
    lease.assert_valid_for("action_read")
    try:
        lease.assert_valid_for("action_delete")
        return False
    except UnpermittedActionError:
        pass
    expired = create_resource_lease(
        lease_id="lease_worker_02",
        task_id="task_build",
        task_revision=1,
        worker_id="worker_py_01",
        expires_at="2020-01-01T00:00:00Z",
        permitted_actions=["action_read"],
    )
    try:
        expired.assert_valid_for("action_read")
        return False
    except LeaseExpiredError:
        return True

def _bad() -> bool:
    # Adversarial mutation: worker operates with expired lease without rejection
    expired = create_resource_lease(
        lease_id="lease_worker_03",
        task_id="task_build",
        task_revision=1,
        worker_id="worker_py_01",
        expires_at="2020-01-01T00:00:00Z",
        permitted_actions=["action_read"],
    )
    return not expired.is_expired()

def test_l9_t_033():
    oracle("L9-REQ-CAP-003", "L9-T-033", _good, _bad)
