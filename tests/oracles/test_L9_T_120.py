"""Oracle test for L9-REQ-SKL-005 / L9-T-120."""
from hyai.capabilities.worker import UnpermittedActionError, create_resource_lease
from hyai.skills.binding import create_skill_binding
from ._f06_support import sample_skill
from ._support import oracle

def _good() -> bool:
    skill = sample_skill("skill_worker", "1.0.0")
    lease = create_resource_lease(
        lease_id="lease_w1",
        task_id="task_w1",
        task_revision=1,
        worker_id="worker_01",
        expires_at="2099-01-01T00:00:00Z",
        permitted_actions=["action_read"],
    )
    binding = create_skill_binding(
        binding_id="skillbind_w1",
        task_id="task_w1",
        attempt_id="att_1",
        skill_id="skill_worker",
        skill_version="1.0.0",
        skill_digest=skill.content_digest,
        resolved_capabilities=["cap_text_analysis"],
        lease=lease,
    )
    binding.assert_executable(skill, "action_read")
    try:
        binding.assert_executable(skill, "action_admin_elevate")
        return False
    except UnpermittedActionError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_120():
    oracle("L9-REQ-SKL-005", "L9-T-120", _good, _bad)
