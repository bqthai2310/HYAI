"""Compile frozen TestSpecs and register evidence-bound oracle results."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from hyai._contracts import timestamp, validate
from hyai.compatibility.crypto import compute_digest, validate_digest_spec


class AcceptanceCompilationError(ValueError):
    """Raised when a TestSpec or OracleResult cannot be trusted."""


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceCompilationError(str(error)) from error
    if not isinstance(data, dict):
        raise AcceptanceCompilationError("acceptance documents must be JSON objects")
    return data


def _document(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AcceptanceCompilationError("acceptance documents must be JSON objects")
    return deepcopy(dict(value))


def _within(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise AcceptanceCompilationError(f"fixture path escapes repository: {relative_path}") from error
    return candidate


def _fixture_path(root: Path, binding_path: str) -> Path:
    """Resolve canonical fixture paths, with a migration adapter for this repo."""
    candidate = _within(root, binding_path)
    if candidate.is_file():
        return candidate
    prefix = "30_executable_acceptance/fixtures/"
    if binding_path.startswith(prefix):
        legacy = _within(root, "tests/fixtures/" + binding_path[len(prefix):])
        if legacy.is_file():
            return legacy
    return candidate


def _validate_fixture_bindings(spec: Mapping[str, Any], root: Path) -> None:
    bindings = spec["fixture_bindings"]
    kinds = [item["kind"] for item in bindings]
    if "POSITIVE_BASELINE" not in kinds or "NEGATIVE_VECTOR" not in kinds:
        raise AcceptanceCompilationError("both positive and negative fixture bindings are required")
    fixture_ids = [item["fixture_id"] for item in bindings]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise AcceptanceCompilationError("fixture bindings must have unique fixture_id values")

    negative_bindings: dict[str, Mapping[str, Any]] = {}
    for binding in bindings:
        fixture = _fixture_path(root, binding["path"])
        if not fixture.is_file():
            raise AcceptanceCompilationError(f"missing fixture: {binding['path']}")
        if compute_digest(fixture.read_bytes()) != binding["digest"]:
            raise AcceptanceCompilationError(f"fixture digest does not match: {binding['fixture_id']}")
        payload = load_json(fixture)
        if payload.get("fixture_id") != binding["fixture_id"] or payload.get("kind") != binding["kind"]:
            raise AcceptanceCompilationError(f"fixture identity does not match binding: {binding['fixture_id']}")
        if binding["kind"] == "NEGATIVE_VECTOR":
            negative_bindings[binding["fixture_id"]] = binding

    case_ids: set[str] = set()
    for case in spec["negative_cases"]:
        if case["case_id"] in case_ids:
            raise AcceptanceCompilationError("negative case identifiers must be unique")
        case_ids.add(case["case_id"])
        binding = negative_bindings.get(case["fixture_id"])
        if binding is None:
            raise AcceptanceCompilationError(f"negative case is not bound to a negative fixture: {case['fixture_id']}")
        payload = load_json(_fixture_path(root, binding["path"]))
        for key in ("expected_result", "forbidden_result", "required_assertions", "frozen_predicate"):
            if payload.get(key) != case[key]:
                raise AcceptanceCompilationError(f"negative fixture does not match case {case['case_id']}: {key}")


def compile_test_spec(spec: Mapping[str, Any], repository_root: str | Path) -> dict[str, Any]:
    """Validate and compile a canonical, frozen TestSpec."""
    document = _document(spec)
    validate(document, "test_spec.schema.json", AcceptanceCompilationError)
    if document["authority_locked"] is not True:
        raise AcceptanceCompilationError("TestSpec must be authority locked before execution")
    assertions = document["expected_assertions"]
    if len(assertions) != len(set(assertions)):
        raise AcceptanceCompilationError("pre-declared expected assertions must be unique")
    entrypoint = _within(Path(repository_root), document["entrypoint"])
    if not entrypoint.is_file():
        raise AcceptanceCompilationError(f"missing oracle entrypoint: {document['entrypoint']}")
    _validate_fixture_bindings(document, Path(repository_root))
    return document


def validate_external_review_attestation(attestation: Mapping[str, Any], subject_digest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an explicit human/external-review decision for a subject."""
    document = _document(attestation)
    validate(document, "external_review_attestation.schema.json", AcceptanceCompilationError)
    if document["review_subject_digest"] != dict(subject_digest):
        raise AcceptanceCompilationError("external review attestation is bound to another subject")
    return document


def build_oracle_result(
    test_id: str, subject_digest: Mapping[str, Any], result: str,
    assertion_results: list[Mapping[str, Any]], raw_evidence_refs: list[str], *,
    oracle_result_id: str | None = None, executed_at: str | None = None,
    test_spec: Mapping[str, Any] | None = None,
    external_review_attestation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a schema-valid OracleResult after enforcing its frozen TestSpec."""
    document = {
        "schema_version": "2.1.0", "oracle_result_id": oracle_result_id or f"oracleres_{uuid4().hex}",
        "test_id": test_id, "subject_digest": _document(subject_digest), "result": result,
        "assertion_results": [_document(item) for item in assertion_results],
        "raw_evidence_refs": list(raw_evidence_refs), "executed_at": executed_at or timestamp(),
    }
    return validate_oracle_result(document, test_spec, external_review_attestation)


def validate_oracle_result(
    result: Mapping[str, Any], test_spec: Mapping[str, Any] | None = None,
    external_review_attestation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate an OracleResult, including frozen assertions and subject binding."""
    document = _document(result)
    validate(document, "oracle_result.schema.json", AcceptanceCompilationError)
    if not validate_digest_spec(document["subject_digest"]):
        raise AcceptanceCompilationError("OracleResult subject_digest is not a supported canonical digest")
    if not all(isinstance(ref, str) and ref.strip() for ref in document["raw_evidence_refs"]):
        raise AcceptanceCompilationError("OracleResult requires non-empty raw evidence references")
    if test_spec is not None:
        spec = _document(test_spec)
        validate(spec, "test_spec.schema.json", AcceptanceCompilationError)
        if document["test_id"] != spec["test_id"]:
            raise AcceptanceCompilationError("OracleResult is for another TestSpec")
        expected = spec["expected_assertions"]
        reported = [item["assertion"] for item in document["assertion_results"]]
        if len(reported) != len(set(reported)) or set(reported) != set(expected):
            raise AcceptanceCompilationError("OracleResult must report exactly the pre-declared assertions")
        if spec["verification_kind"] == "EXTERNAL_REVIEW":
            if document["result"] == "PASS":
                raise AcceptanceCompilationError("EXTERNAL_REVIEW TestSpecs cannot emit automated PASS")
            if external_review_attestation is not None:
                validate_external_review_attestation(external_review_attestation, document["subject_digest"])
    return document


class OracleRegistry:
    """In-memory registry that freezes TestSpecs before recording executions."""

    def __init__(self, repository_root: str | Path) -> None:
        self._root = Path(repository_root)
        self._specs: dict[str, dict[str, Any]] = {}
        self._results: dict[str, dict[str, Any]] = {}

    def register_test_spec(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        document = compile_test_spec(spec, self._root)
        prior = self._specs.get(document["test_id"])
        if prior is not None and prior != document:
            raise AcceptanceCompilationError("a registered TestSpec is frozen and cannot be changed")
        self._specs[document["test_id"]] = deepcopy(document)
        return deepcopy(document)

    def get_test_spec(self, test_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self._specs[test_id])
        except KeyError as error:
            raise AcceptanceCompilationError(f"unknown TestSpec: {test_id}") from error

    def record_oracle_result(self, result: Mapping[str, Any], *, external_review_attestation: Mapping[str, Any] | None = None) -> dict[str, Any]:
        candidate = _document(result)
        spec = self.get_test_spec(str(candidate.get("test_id", "")))
        document = validate_oracle_result(candidate, spec, external_review_attestation)
        prior = self._results.get(document["oracle_result_id"])
        if prior is not None and prior != document:
            raise AcceptanceCompilationError("OracleResult identifiers are immutable")
        self._results[document["oracle_result_id"]] = deepcopy(document)
        return deepcopy(document)

    def get_oracle_result(self, oracle_result_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self._results[oracle_result_id])
        except KeyError as error:
            raise AcceptanceCompilationError(f"unknown OracleResult: {oracle_result_id}") from error


def compile_requirement(requirement_id: str, test_id: str, entrypoint: str, repository_root: str | Path) -> dict[str, Any]:
    """Compile the repository's standard pair while emitting a canonical TestSpec."""
    root = Path(repository_root)
    fixture_dir = root / "tests" / "fixtures" / requirement_id
    positive, negative = fixture_dir / "positive.json", fixture_dir / "negative_001.json"
    if not positive.is_file() or not negative.is_file():
        raise AcceptanceCompilationError(f"missing standard fixtures for {requirement_id}")
    positive_payload, negative_payload = load_json(positive), load_json(negative)
    canonical_dir = f"30_executable_acceptance/fixtures/{requirement_id}"
    spec = {
        "schema_version": "2.1.0", "test_id": test_id, "requirement_id": requirement_id,
        "phase_id": "F04", "acceptance_id": "F04-AC-001", "verification_kind": "UNIT",
        "objective": f"Verify {requirement_id}", "preconditions": ["Frozen TestSpec is available"],
        "expected_assertions": list(positive_payload.get("frozen_assertions", [f"{requirement_id} passes"])),
        "negative_cases": [{"case_id": "negative_001", "fixture_id": negative_payload["fixture_id"],
            "mutation_operator": negative_payload["mutation_operator"], "frozen_predicate": negative_payload["frozen_predicate"],
            "expected_result": negative_payload["expected_result"], "forbidden_result": negative_payload["forbidden_result"],
            "required_assertions": negative_payload["required_assertions"]}],
        "fixture_bindings": [
            {"fixture_id": positive_payload["fixture_id"], "kind": "POSITIVE_BASELINE", "path": f"{canonical_dir}/positive.json", "digest": compute_digest(positive.read_bytes())},
            {"fixture_id": negative_payload["fixture_id"], "kind": "NEGATIVE_VECTOR", "path": f"{canonical_dir}/negative_001.json", "digest": compute_digest(negative.read_bytes())},
        ],
        "required_evidence": ["raw_oracle_output"], "entrypoint": entrypoint, "authority_locked": True,
    }
    return compile_test_spec(spec, root)
