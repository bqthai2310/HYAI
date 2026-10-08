"""Oracle test for L9-REQ-SKL-002 / L9-T-117."""
from hyai._contracts import sha256_digest
from hyai.skills.binding import UnboundExecutionError, create_skill_binding
from hyai.skills.spec import SkillIntegrityError
from ._f06_support import sample_skill
from ._support import oracle

def _good() -> bool:
    skill = sample_skill("skill_auth", "1.2.0")
    binding = create_skill_binding(
        binding_id="skillbind_auth_01",
        task_id="task_login",
        attempt_id="att_1",
        skill_id="skill_auth",
        skill_version="1.2.0",
        skill_digest=skill.content_digest,
        resolved_capabilities=["cap_text_analysis"],
    )
    binding.assert_bound_to(skill)
    # Tampered version must fail
    tampered_skill = sample_skill("skill_auth", "1.2.1")
    try:
        binding.assert_bound_to(tampered_skill)
        return False
    except UnboundExecutionError:
        return True

def _bad() -> bool:
    return False

def test_l9_t_117():
    oracle("L9-REQ-SKL-002", "L9-T-117", _good, _bad)
