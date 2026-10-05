#!/usr/bin/env python3
"""Validate HYAI JSON Schemas and, optionally, review artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REVIEW_SCHEMA_KEYS = {
    "review_request_id": "review_request.schema.json",
    "verdict_id": "review_verdict.schema.json",
    "attestation_id": "external_review_attestation.schema.json",
    "subject_id": "review_subject_manifest.schema.json",
    "criterion_results": "acceptance_results.schema.json",
    "bundle_id": "evidence_bundle.schema.json",
    "guard_result_id": "root_guard_result.schema.json",
}


def schema_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "schemas").rglob("*.json"))


def validate_schemas(root: Path = ROOT) -> list[str]:
    """Return Draft 2020-12 schema validation errors, if any."""
    errors: list[str] = []
    for path in schema_paths(root):
        try:
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        except Exception as error:
            errors.append(f"{path.relative_to(root)}: {error}")
    return errors


def _review_schema(document: dict[str, Any]) -> str | None:
    matches = [schema for key, schema in REVIEW_SCHEMA_KEYS.items() if key in document]
    return matches[0] if len(matches) == 1 else None


def validate_review_artifacts(root: Path = ROOT) -> list[str]:
    """Validate every JSON artifact in review/ against its identified schema."""
    errors: list[str] = []
    review_dir = root / "review"
    if not review_dir.exists():
        return ["review directory is missing"]
    for artifact in sorted(review_dir.rglob("*.json")):
        try:
            document = json.loads(artifact.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("artifact must be a JSON object")
            schema_name = _review_schema(document)
            if schema_name is None:
                raise ValueError("cannot identify a review artifact schema")
            schema = json.loads((root / "schemas" / schema_name).read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            errors.extend(f"{artifact.relative_to(root)}: {error.message}" for error in sorted(validator.iter_errors(document), key=lambda error: list(error.path)))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{artifact.relative_to(root)}: {error}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--review-artifacts", action="store_true", help="also validate review/*.json")
    args = parser.parse_args(argv)
    errors = validate_schemas(args.root)
    if args.review_artifacts:
        errors.extend(validate_review_artifacts(args.root))
    if errors:
        print("SPEC_VALIDATION=FAIL")
        print("\n".join(errors))
        return 1
    suffix = " review_artifacts=validated" if args.review_artifacts else ""
    print(f"SPEC_VALIDATION=PASS schemas={len(schema_paths(args.root))}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
