from __future__ import annotations

import json

import pytest

from hyai.acceptance import AcceptanceCompilationError, OracleRegistry, build_oracle_result, compile_test_spec
from hyai.compatibility import compute_digest


def _spec(tmp_path):
    fixture_dir = tmp_path / "30_executable_acceptance" / "fixtures" / "L9-REQ-ORC-001"
    fixture_dir.mkdir(parents=True)
    oracle_dir = tmp_path / "tests" / "oracles"; oracle_dir.mkdir(parents=True)
    (oracle_dir / "test_example.py").write_text("# oracle\n", encoding="utf-8")
    positive = {"fixture_id": "fixture-positive", "kind": "POSITIVE_BASELINE"}
    negative = {"fixture_id": "fixture-negative", "kind": "NEGATIVE_VECTOR", "expected_result": "FAIL", "forbidden_result": "PASS", "required_assertions": ["must fail"], "frozen_predicate": "predicate is frozen"}
    positive_path, negative_path = fixture_dir / "positive.json", fixture_dir / "negative.json"
    positive_path.write_text(json.dumps(positive), encoding="utf-8"); negative_path.write_text(json.dumps(negative), encoding="utf-8")
    return {"schema_version": "2.1.0", "test_id": "L9-T-100", "requirement_id": "L9-REQ-ORC-001", "phase_id": "F04", "acceptance_id": "F04-AC-001", "verification_kind": "UNIT", "objective": "Compile a frozen TestSpec", "preconditions": ["fixtures exist"], "expected_assertions": ["must compile"], "negative_cases": [{"case_id": "case-1", "fixture_id": "fixture-negative", "mutation_operator": "FORCE_FROZEN_PREDICATE_FALSE", "frozen_predicate": "predicate is frozen", "expected_result": "FAIL", "forbidden_result": "PASS", "required_assertions": ["must fail"]}], "fixture_bindings": [{"fixture_id": "fixture-positive", "kind": "POSITIVE_BASELINE", "path": "30_executable_acceptance/fixtures/L9-REQ-ORC-001/positive.json", "digest": compute_digest(positive_path.read_bytes())}, {"fixture_id": "fixture-negative", "kind": "NEGATIVE_VECTOR", "path": "30_executable_acceptance/fixtures/L9-REQ-ORC-001/negative.json", "digest": compute_digest(negative_path.read_bytes())}], "required_evidence": ["ev_raw"], "entrypoint": "tests/oracles/test_example.py", "authority_locked": True}


def test_compiles_canonical_spec_and_rejects_changed_fixture(tmp_path):
    spec = _spec(tmp_path)
    compiled = compile_test_spec(spec, tmp_path)
    assert compiled["test_id"] == "L9-T-100"
    path = tmp_path / "30_executable_acceptance" / "fixtures" / "L9-REQ-ORC-001" / "positive.json"
    path.write_text('{"fixture_id":"fixture-positive","kind":"POSITIVE_BASELINE","changed":true}', encoding="utf-8")
    with pytest.raises(AcceptanceCompilationError, match="digest"):
        compile_test_spec(spec, tmp_path)


def test_registry_locks_assertions_and_oracle_results_bind_subject(tmp_path):
    spec = _spec(tmp_path); registry = OracleRegistry(tmp_path); registry.register_test_spec(spec)
    subject = compute_digest(b"subject")
    result = build_oracle_result("L9-T-100", subject, "PASS", [{"assertion": "must compile", "result": "PASS"}], ["ev_raw"], test_spec=spec)
    assert registry.record_oracle_result(result)["subject_digest"] == subject
    changed = dict(spec); changed["expected_assertions"] = ["late assertion"]
    with pytest.raises(AcceptanceCompilationError, match="frozen"):
        registry.register_test_spec(changed)
    with pytest.raises(AcceptanceCompilationError):
        build_oracle_result("L9-T-100", subject, "PASS", [{"assertion": "must compile", "result": "FAIL"}], ["ev_raw"])
