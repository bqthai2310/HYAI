"""Oracle test for L9-REQ-SKL-008 / L9-T-123."""
from hyai.skills.registry import SkillRegistry
from ._f06_support import sample_skill
from ._support import oracle

def _good() -> bool:
    # Skill lifecycle and registry exist independently of any product lifecycle or ownership
    registry = SkillRegistry()
    s = sample_skill("skill_reusable", "1.0.0")
    registry.register_skill(s)
    stored = registry.get_skill("skill_reusable", "1.0.0")
    return stored is not None and not hasattr(stored, "product_id") and not hasattr(stored, "product_ownership")

def _bad() -> bool:
    return False

def test_l9_t_123():
    oracle("L9-REQ-SKL-008", "L9-T-123", _good, _bad)
