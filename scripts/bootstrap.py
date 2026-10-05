#!/usr/bin/env python3
"""Run deterministic, secret-free HYAI bootstrap validation."""
from __future__ import annotations

import json
from pathlib import Path

import root_guard
import validate_spec

ROOT = Path(__file__).resolve().parents[1]


def validate_configuration(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    config_dir = root / "config"
    if not config_dir.is_dir():
        errors.append("missing config directory")
    if not (root / "src" / "hyai" / "ports" / "__init__.py").is_file():
        errors.append("missing declared ports package: src/hyai/ports")
    if config_dir.is_dir():
        for path in sorted(config_dir.rglob("*.json")):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"invalid configuration {path.relative_to(root)}: {error}")
    return errors


def main() -> int:
    snapshot = root_guard.take_snapshot(ROOT)
    root_result = root_guard.verify_root(snapshot, "bootstrap", ROOT)
    schema_errors = validate_spec.validate_schemas(ROOT)
    config_errors = validate_configuration(ROOT)
    if root_result["result"] != "PASS" or schema_errors or config_errors:
        print("BOOTSTRAP=FAIL")
        for error in root_result["unauthorized_entries"] + schema_errors + config_errors:
            print(f"BOOTSTRAP_ERROR={error}")
        return 1
    print("BOOTSTRAP=PASS secrets=not-required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
