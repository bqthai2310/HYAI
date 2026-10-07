"""Compatibility profiles and stable-core dependency checks."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .crypto import validate_digest_spec

_VENDOR_TOKENS = ("boto3", "openai", "anthropic", "fastapi", "httpx")


def _schema() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    return json.loads((root / "schemas" / "compatibility_profile.schema.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class CompatibilityProfile:
    schema_version: str
    profile_id: str
    subject_ref: str
    contract_version: str
    compatibility_class: str
    supported_versions: list[str]
    migration_refs: list[str]
    content_digest: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["supported_versions"] = list(self.supported_versions)
        value["migration_refs"] = list(self.migration_refs)
        value["content_digest"] = dict(self.content_digest)
        return value

    def validate(self) -> bool:
        errors = list(Draft202012Validator(_schema()).iter_errors(self.to_dict()))
        if errors:
            raise ValueError("compatibility profile invalid: " + "; ".join(error.message for error in errors))
        if not validate_digest_spec(dict(self.content_digest)):
            raise ValueError("compatibility profile content_digest is invalid")
        return True


def is_stable_core_isolated(module_or_contract: object) -> bool:
    """Ensure a stable core contract does not pull in vendor/protocol SDKs."""
    if isinstance(module_or_contract, Path):
        text = module_or_contract.read_text(encoding="utf-8")
    elif isinstance(module_or_contract, str):
        path = Path(module_or_contract)
        text = path.read_text(encoding="utf-8") if path.is_file() else module_or_contract
    else:
        path = Path(getattr(module_or_contract, "__file__", ""))
        text = path.read_text(encoding="utf-8") if path.is_file() else repr(module_or_contract)
    return not any(token in text.lower() for token in _VENDOR_TOKENS)


def validate_breaking_change(profile: CompatibilityProfile, migration_plan: dict | None) -> tuple[bool, str]:
    try:
        profile.validate()
    except ValueError as error:
        return False, str(error)
    if profile.compatibility_class != "BREAKING":
        return True, "not a breaking change"
    if not profile.contract_version or not profile.migration_refs:
        return False, "breaking changes require a new version and migration references"
    if not isinstance(migration_plan, dict):
        return False, "breaking changes require a migration plan"
    version = migration_plan.get("new_version", migration_plan.get("contract_version"))
    rollback = migration_plan.get("rollback_analysis", migration_plan.get("rollback"))
    invalidation = migration_plan.get("invalidation_analysis", migration_plan.get("invalidation"))
    if not version or str(version) == profile.contract_version:
        return False, "breaking changes require a new version"
    if not rollback or not invalidation:
        return False, "breaking changes require rollback and invalidation analysis"
    return True, "breaking change migration is complete"
