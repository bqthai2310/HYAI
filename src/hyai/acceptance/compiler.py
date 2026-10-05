"""Acceptance-first compiler for TestSpecs and their immutable fixtures."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class AcceptanceCompilationError(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceCompilationError(str(error)) from error
    if not isinstance(data, dict):
        raise AcceptanceCompilationError("acceptance documents must be JSON objects")
    return data


def compile_test_spec(spec: Mapping[str, Any], repository_root: str | Path) -> dict[str, Any]:
    required = {"test_id", "requirement_id", "entrypoint", "fixture_bindings", "negative_cases", "authority_locked"}
    missing = required - set(spec)
    if missing or spec.get("authority_locked") is not True:
        raise AcceptanceCompilationError(f"invalid acceptance lock; missing={sorted(missing)}")
    root = Path(repository_root)
    entrypoint = root / str(spec["entrypoint"])
    if not entrypoint.is_file():
        raise AcceptanceCompilationError(f"missing oracle entrypoint: {spec['entrypoint']}")
    bindings = spec["fixture_bindings"]
    if not isinstance(bindings, list) or {item.get("kind") for item in bindings} != {"POSITIVE_BASELINE", "NEGATIVE_VECTOR"}:
        raise AcceptanceCompilationError("both positive and negative fixture bindings are required")
    for binding in bindings:
        path = binding.get("path")
        if not isinstance(path, str) or not (root / path).is_file():
            raise AcceptanceCompilationError(f"missing fixture: {path}")
    if not spec["negative_cases"]:
        raise AcceptanceCompilationError("at least one negative case is required")
    return {"test_id": spec["test_id"], "requirement_id": spec["requirement_id"], "entrypoint": str(entrypoint)}


def compile_requirement(requirement_id: str, test_id: str, entrypoint: str, repository_root: str | Path) -> dict[str, Any]:
    """Compile the repository's standard positive/negative fixture pair."""
    root = Path(repository_root)
    fixture_dir = root / "tests" / "fixtures" / requirement_id
    spec = {"test_id": test_id, "requirement_id": requirement_id, "entrypoint": entrypoint,
            "authority_locked": True, "negative_cases": [{"case_id": "negative_001"}],
            "fixture_bindings": [{"kind": "POSITIVE_BASELINE", "path": str((fixture_dir / "positive.json").relative_to(root))},
                                 {"kind": "NEGATIVE_VECTOR", "path": str((fixture_dir / "negative_001.json").relative_to(root))}]}
    return compile_test_spec(spec, root)
