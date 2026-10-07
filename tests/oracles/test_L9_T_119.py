"""Oracle test for L9-REQ-SKL-004 / L9-T-119."""
from hyai.skills.registry import SkillRegistry
from hyai.skills.spec import SkillEvaluationError
from ._f06_support import sample_skill
from ._support import oracle

def _good() -> bool:
    registry = SkillRegistry()
    s = sample_skill("skill_candidate", "1.0.0", state="REGISTERED", eval_policy="eval_strict_v2")
    registry.register_skill(s)
    # Transition to ACTIVE before passing evaluation policy must be rejected
    try:
        registry.transition_lifecycle("skill_candidate", "1.0.0", "ACTIVE")
        return False
    except SkillEvaluationError:
        pass
    # Pass evaluation policy and verify transition succeeds
    registry.record_evaluation("eval_strict_v2", passed=True)
    active = registry.transition_lifecycle("skill_candidate", "1.0.0", "ACTIVE")
    return active.lifecycle_state == "ACTIVE"

def _bad() -> bool:
    return False

def test_l9_t_119():
    oracle("L9-REQ-SKL-004", "L9-T-119", _good, _bad)
