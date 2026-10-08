"""Support helpers and fixtures for F06 capability and skill oracle tests."""
from __future__ import annotations

from hyai._contracts import sha256_digest
from hyai.capabilities.spec import CapabilitySpec, create_capability_spec
from hyai.skills.spec import SkillSpec, create_skill_spec


def sample_capability(cap_id: str = "cap_text_analysis") -> CapabilitySpec:
    return create_capability_spec(
        capability_id=cap_id,
        name="Text Analysis Capability",
        input_contract="contract_in_text",
        output_contract="contract_out_text",
        permissions=["perm_read"],
    )


def sample_skill(
    skill_id: str = "skill_summarizer",
    version: str = "1.0.0",
    caps: tuple[str, ...] = ("cap_text_analysis",),
    side_effect: str = "NONE",
    state: str = "ACTIVE",
    eval_policy: str = "eval_standard_v1",
    tools: tuple[str, ...] = ("tool_parser",),
    providers: tuple[str, ...] = ("prov_anthropic",),
) -> SkillSpec:
    digest = sha256_digest(f"{skill_id}:{version}:code".encode())
    return create_skill_spec(
        skill_id=skill_id,
        semantic_version=version,
        content_digest=digest,
        provided_capabilities=caps,
        permission_profile=["perm_read"],
        side_effect_class=side_effect,
        evaluation_policy_ref=eval_policy,
        lifecycle_state=state,
        required_tools=tools,
        required_providers=providers,
    )
