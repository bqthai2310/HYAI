"""Oracle test for L9-REQ-SKL-001 / L9-T-116."""
from hyai.skills.spec import SkillValidationError, create_skill_spec
from ._f06_support import sample_skill
from ._support import oracle

def _good() -> bool:
    skill = sample_skill("skill_parser", "1.0.0")
    assert skill.provided_capabilities == ("cap_text_analysis",)
    assert skill.side_effect_class == "NONE"
    assert skill.permission_profile == ("perm_read",)
    return True

def _bad() -> bool:
    return False

def test_l9_t_116():
    oracle("L9-REQ-SKL-001", "L9-T-116", _good, _bad)
