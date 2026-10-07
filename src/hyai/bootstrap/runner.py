"""Deterministic, secret-free bootstrap validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from hyai.ports.base import ProviderPort, ReviewPort, StoragePort


def bootstrap(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    errors: list[str] = []
    manifest_path = base / "ROOT_LAYOUT_MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        allowed = set(manifest["allowed_root_directories"]) | set(manifest["allowed_root_files"]) | {".git"}
        errors.extend(f"unauthorized root entry: {path.name}" for path in base.iterdir() if path.name not in allowed)
        if manifest.get("executor_may_modify_manifest") is not False:
            errors.append("manifest permits executor modification")
    except (OSError, ValueError, KeyError) as error:
        errors.append(f"invalid root manifest: {error}")
    for schema in sorted((base / "schemas").glob("*.json")):
        try:
            Draft202012Validator.check_schema(json.loads(schema.read_text(encoding="utf-8")))
        except Exception as error:  # jsonschema exposes several exception classes
            errors.append(f"invalid schema {schema.name}: {error}")
    for config in sorted((base / "config").rglob("*.json")):
        try:
            json.loads(config.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            errors.append(f"invalid config {config.name}: {error}")
    if not all(isinstance(port, type) for port in (StoragePort, ProviderPort, ReviewPort)):
        errors.append("required ports unavailable")
    return {"result": "PASS" if not errors else "FAIL", "errors": errors, "secrets_required": False}
