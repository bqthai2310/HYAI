"""Oracle test for L9-REQ-SKL-003 / L9-T-118."""
from hyai.skills.registry import SkillRegistry
from hyai.skills.resolver import HardConstraints, SkillResolutionError, SkillResolver
from ._f06_support import sample_skill
from ._support import oracle

def _good() -> bool:
    registry = SkillRegistry()
    s1 = sample_skill("skill_risky", "1.0.0", side_effect="IRREVERSIBLE")
    s2 = sample_skill("skill_safe", "1.0.0", side_effect="NONE")
    registry.register_skill(s1)
    registry.register_skill(s2)
    resolver = SkillResolver(registry)
    # Hard constraint: ceiling max_side_effect NONE excludes s1 (IRREVERSIBLE)
    chosen = resolver.resolve(HardConstraints(
        required_capability="cap_text_analysis",
        max_side_effect="NONE",
    ))
    return chosen.skill_id == "skill_safe"

def _bad() -> bool:
    return False

def test_l9_t_118():
    oracle("L9-REQ-SKL-003", "L9-T-118", _good, _bad)
