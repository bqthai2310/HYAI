"""Oracle test for L9-REQ-SKL-007 / L9-T-122."""
from hyai.skills.registry import SkillRegistry
from ._f06_support import sample_skill
from ._support import oracle

def _good() -> bool:
    registry = SkillRegistry()
    s_active = sample_skill("skill_active", "1.0.0", state="ACTIVE")
    s_quarantined = sample_skill("skill_bad", "1.0.0", state="REGISTERED")
    registry.register_skill(s_active)
    registry.register_skill(s_quarantined)
    registry.transition_lifecycle("skill_bad", "1.0.0", "QUARANTINED")
    active_skills = registry.query_active_skills(required_capability="cap_text_analysis")
    ids = [s.skill_id for s in active_skills]
    return "skill_active" in ids and "skill_bad" not in ids

def _bad() -> bool:
    return False

def test_l9_t_122():
    oracle("L9-REQ-SKL-007", "L9-T-122", _good, _bad)
