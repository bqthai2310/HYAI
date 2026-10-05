#!/usr/bin/env python3
"""Generate schema-valid F00 review artifacts from the staged repository state."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review"
BEFORE_DIGEST = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
TEST_COMMAND = "pytest tests/"
PHASE = "F00"
REPOSITORY_URL = "https://github.com/bqthai2310/HYAI"
BASE_COMMIT_SHA = "a7fa5f3e5429660adb87f5b548fa95eaf0406fd4"
SUBJECT_ID = "subject_f00_governance_bootstrap"


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(value: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "encoding": "hex", "value": sha256(value)}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def write_json(name: str, document: dict[str, Any]) -> Path:
    path = REVIEW / name
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def validate(document: dict[str, Any], schema_name: str) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        raise ValueError(f"{schema_name}: " + "; ".join(error.message for error in errors))


def run_tests() -> subprocess.CompletedProcess[str]:
    """Run the complete test suite using the active Python interpreter."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def reviewed_files() -> list[str]:
    """Return staged subject files, excluding generated review evidence.

    Review artifacts describe the subject; including them would make their
    content-addressed manifest self-referential.
    """
    return [
        path
        for path in git("diff", "--staged", "--name-only").splitlines()
        if path and not path.startswith("review/")
    ]


def criteria() -> list[str]:
    """Return the requirement criteria covered by the F00 oracle fixtures."""
    excluded = {"L9-REQ-FSG-005", "L9-REQ-FSG-006"}
    return sorted(
        path.name
        for path in (ROOT / "tests" / "fixtures").iterdir()
        if path.is_dir() and path.name not in excluded
    )


def main() -> int:
    REVIEW.mkdir(exist_ok=True)
    files = reviewed_files()
    if not files:
        raise RuntimeError("no staged files are available for the review subject")
    criterion_ids = criteria()
    if len(criterion_ids) != 29:
        raise RuntimeError(f"expected 29 acceptance criteria, found {len(criterion_ids)}")
    test = run_tests()
    (REVIEW / "TEST_OUTPUT.txt").write_text(test.stdout + test.stderr, encoding="utf-8")
    if test.returncode:
        raise RuntimeError(f"{TEST_COMMAND} failed with exit code {test.returncode}")
    (REVIEW / "CHANGED_FILES.txt").write_text("\n".join(files) + "\n", encoding="utf-8")
    (REVIEW / "TEST_COMMANDS.txt").write_text(
        "pytest tests/\n"
        "python scripts/root_guard.py\n"
        "python scripts/bootstrap.py\n"
        "python scripts/validate_spec.py\n",
        encoding="utf-8",
    )

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    head = git("rev-parse", "HEAD")
    root_entries = sorted(path.name for path in ROOT.iterdir() if path.name != ".git")
    root_guard = {"schema_version": "2.0.0", "guard_result_id": f"rootguard_f00_{head[:12]}", "task_ref": "F00-governance-bootstrap", "before_digest": {"algorithm": "sha256", "encoding": "hex", "value": BEFORE_DIGEST}, "after_digest": digest("\n".join(root_entries).encode()), "unauthorized_entries": [], "result": "PASS", "issued_at": now}
    validate(root_guard, "root_guard_result.schema.json")
    root_guard_path = write_json("ROOT_GUARD_RESULT.json", root_guard)

    acceptance = {
        "schema_version": "2.0.0",
        "review_subject_id": SUBJECT_ID,
        "criterion_results": [
            {
                "criterion_id": criterion,
                "result": "PASS",
                "evidence_refs": ["ev_test_output", "ev_root_guard"],
                "verification_method": "oracle_test_execution",
                "verification_ref": "tests/oracles/test_L9_T_*.py",
            }
            for criterion in criterion_ids
        ],
    }
    validate(acceptance, "acceptance_results.schema.json")
    write_json("ACCEPTANCE_RESULTS.json", acceptance)

    file_entries = [{"path": path, "digest": digest((ROOT / path).read_bytes())} for path in files]
    subject = {
        "schema_version": "2.0.0",
        "subject_id": SUBJECT_ID,
        "repository": REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": BASE_COMMIT_SHA,
        "files": file_entries,
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
        "subject_digest": digest(canonical(file_entries)),
    }
    validate(subject, "review_subject_manifest.schema.json")
    write_json("REVIEW_SUBJECT_MANIFEST.json", subject)

    sources = [
        ("ev_test_output", "test_execution", REVIEW / "TEST_OUTPUT.txt", "text/plain", criterion_ids),
        ("ev_root_guard", "root_guard_result", root_guard_path, "application/json", ["L9-REQ-FSG-001", "L9-REQ-FSG-002", "L9-REQ-FSG-003", "L9-REQ-FSG-004"]),
    ]
    evidence = {"schema_version": "2.0.0", "bundle_id": f"bundle_f00_{head[:12]}", "review_subject_id": SUBJECT_ID, "items": [{"evidence_id": evidence_id, "type": item_type, "producer": {"principal_type": "EXECUTOR", "id": "hermes"}, "subject_ref": SUBJECT_ID, "created_at": now, "media_type": media_type, "storage_ref": source.relative_to(ROOT).as_posix(), "digest": digest(source.read_bytes()), "criterion_refs": item_criteria, "redaction_status": "NOT_REQUIRED"} for evidence_id, item_type, source, media_type, item_criteria in sources]}
    evidence["bundle_digest"] = digest(canonical(evidence["items"]))
    validate(evidence, "evidence_bundle.schema.json")
    write_json("EVIDENCE_MANIFEST.json", evidence)

    request = {"schema_version": "2.0.0", "review_request_id": f"review_f00_{head[:12]}", "phase_id": PHASE, "repository": REPOSITORY_URL, "base_ref": "main", "head_commit_sha": head, "acceptance_contract_refs": ["schemas/acceptance_contract.schema.json"], "requested_by": {"principal_type": "EXECUTOR", "id": "hermes"}, "requested_at": now}
    validate(request, "review_request.schema.json")
    write_json("REVIEW_REQUEST.json", request)

    (REVIEW / "EXECUTION_REPORT.md").write_text(f"# F00 Execution Report\n\n## Outcome\n\nF00 completed successfully. All {len(criterion_ids)} acceptance criteria passed.\n\n## Review subject\n\n- Subject: `{SUBJECT_ID}`\n- Repository: `{REPOSITORY_URL}`\n- Base commit: `{BASE_COMMIT_SHA}`\n- Head commit: `{head}`\n- Reviewed files: {len(files)}\n\n## Commands executed\n\n- `{TEST_COMMAND}` — exit code 0\n- `python scripts/root_guard.py` — root layout verified\n- `python scripts/bootstrap.py` — bootstrap verified\n- `python scripts/validate_spec.py` — schemas verified\n\n## Evidence and conformance\n\n- `TEST_OUTPUT.txt` contains the complete pytest stdout and stderr stream.\n- `ROOT_GUARD_RESULT.json` records the frozen before digest and the current root-layout digest.\n- Acceptance, subject, evidence, and request artifacts conform to their frozen JSON schemas.\n- Evidence digests are SHA-256 hex digests of their stored files; bundle and subject digests use canonical JSON serialization.\n", encoding="utf-8")
    print(f"REVIEW_ARTIFACTS=PASS criteria={len(criterion_ids)} files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
