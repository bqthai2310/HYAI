"""Regression coverage for the F00 review hardening corrections."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_review_artifacts
import root_guard
import validate_spec


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _root_copy(tmp_path: Path) -> Path:
    manifest = _json(ROOT / "ROOT_LAYOUT_MANIFEST.json")
    (tmp_path / "ROOT_LAYOUT_MANIFEST.json").write_bytes(
        (ROOT / "ROOT_LAYOUT_MANIFEST.json").read_bytes()
    )
    for name in manifest["allowed_root_directories"]:
        (tmp_path / name).mkdir()
    for name in manifest["allowed_root_files"]:
        if name != "ROOT_LAYOUT_MANIFEST.json":
            (tmp_path / name).write_text("", encoding="utf-8")
    return tmp_path


@pytest.fixture(scope="session", autouse=True)
def ensure_runtime_review_artifacts():
    """Ensure review artifacts are generated in review/ if not present."""
    manifest_path = ROOT / "review" / "REVIEW_SUBJECT_MANIFEST.json"
    live_path = ROOT / "review" / "LIVE_GITHUB_STATE.json"
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    if not live_path.is_file():
        subprocess.run(
            [sys.executable, "scripts/collect_github_live_state.py", "--head-sha", head],
            cwd=ROOT,
            check=True,
        )
    needs_gen = not manifest_path.is_file()
    if not needs_gen:
        try:
            needs_gen = _json(manifest_path).get("head_commit_sha") != head
        except Exception:
            needs_gen = True
    if needs_gen:
        generate_review_artifacts.main(["--head-sha", head, "--skip-tests"])


def _patched_read_text(monkeypatch, replacements: dict[Path, Any]) -> None:
    """Provide JSON replacements without recursively calling a patched method."""
    original_read_text = Path.read_text

    def read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in replacements:
            return json.dumps(replacements[self])
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)


# 1. Parent HEAD artifact -> FAIL (even if review only).
def test_parent_head_sha_rejected_even_if_review_only(monkeypatch):
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD~1"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    req_path = ROOT / "review" / "REVIEW_REQUEST.json"
    request = _json(req_path)
    request["head_commit_sha"] = parent
    _patched_read_text(monkeypatch, {req_path: request})

    errors = validate_spec.validate_review_artifacts(ROOT, head)
    assert any(
        "REVIEW_REQUEST.head_commit_sha does not match current head commit SHA" in error
        for error in errors
    )


# 2. Exact current HEAD artifact -> PASS.
def test_exact_current_head_accepted():
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    errors = validate_spec.validate_review_artifacts(ROOT, head)
    assert not any("head_commit_sha does not match current head commit SHA" in error for error in errors)


# 3. Changing HEAD -> ReviewSubject digest changes.
def test_changing_head_changes_review_subject_digest():
    subject = _json(ROOT / "review" / "REVIEW_SUBJECT_MANIFEST.json")
    changed = dict(subject)
    changed["head_commit_sha"] = "0" * 40
    assert generate_review_artifacts.compute_subject_digest(
        subject
    ) != generate_review_artifacts.compute_subject_digest(changed)


# 4. Stale subject digest -> FAIL.
def test_stale_subject_digest_rejected(monkeypatch):
    path = ROOT / "review" / "REVIEW_SUBJECT_MANIFEST.json"
    document = _json(path)
    document["subject_digest"]["value"] = "0" * 64
    _patched_read_text(monkeypatch, {path: document})
    assert any("Review subject digest mismatch" in error for error in validate_spec.validate_review_artifacts(ROOT))


# 5. Stale evidence digest -> FAIL.
def test_stale_evidence_digest_rejected(monkeypatch):
    path = ROOT / "review" / "EVIDENCE_MANIFEST.json"
    document = _json(path)
    document["items"][0]["digest"]["value"] = "0" * 64
    _patched_read_text(monkeypatch, {path: document})
    assert any(
        error.startswith("Evidence digest mismatch:")
        for error in validate_spec.validate_review_artifacts(ROOT)
    )


# 6. Modified frozen Root Manifest -> FAIL.
def test_modified_frozen_root_manifest_rejected(tmp_path):
    root = _root_copy(tmp_path)
    (root / "ROOT_LAYOUT_MANIFEST.json").write_text("{}", encoding="utf-8")
    assert root_guard.verify_root(root_guard._digest("before"), "test", root)["result"] == "FAIL_QUARANTINED"


# 7. Unauthorized root entry -> FAIL.
def test_unauthorized_root_entry_rejected(tmp_path):
    root = _root_copy(tmp_path)
    snapshot = root_guard.take_snapshot(root)
    (root / "rogue_entry").mkdir()
    assert root_guard.verify_root(snapshot, "test", root)["result"] == "FAIL_QUARANTINED"


# 8. Static YAML cannot prove live GitHub state.
def test_static_yaml_presence_does_not_prove_live_platform_state(monkeypatch):
    workflow = (ROOT / ".github/workflows/review-artifact-gate.yml").read_text(encoding="utf-8")
    assert "pull_request" in workflow
    live_path = ROOT / "review" / "LIVE_GITHUB_STATE.json"
    original_is_file = Path.is_file
    monkeypatch.setattr(Path, "is_file", lambda self: False if self == live_path else original_is_file(self))
    errors = validate_spec.validate_review_artifacts(ROOT)
    assert any("Git criterion PASS requires live GitHub state evidence" in error for error in errors)


# 9. GIT criterion without live evidence cannot be executor PASS.
def test_git_criterion_without_live_evidence_cannot_be_pass(monkeypatch):
    live_path = ROOT / "review" / "LIVE_GITHUB_STATE.json"
    original_is_file = Path.is_file
    monkeypatch.setattr(Path, "is_file", lambda self: False if self == live_path else original_is_file(self))
    errors = validate_spec.validate_review_artifacts(ROOT)
    assert any("Git criterion PASS requires live GitHub state evidence" in error for error in errors)


# 10. An attestation in the reviewed commit cannot be the canonical external verdict.
def test_independent_attestation_in_reviewed_commit_rejected(monkeypatch, tmp_path, capsys):
    import verify_independent_review

    monkeypatch.setattr(
        verify_independent_review.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0})(),
    )
    assert verify_independent_review.main(["--attestation-file", str(tmp_path / "external.json")]) == 1
    assert "self-referential" in capsys.readouterr().out


# 11. Missing external independent PASS -> merge gate BLOCKED.
def test_missing_external_independent_pass_blocks_gate():
    path = ROOT / "review" / "EXTERNAL_REVIEW_ATTESTATION.json"
    if path.exists():
        pytest.skip("repository contains an external attestation")
    run = subprocess.run(
        [sys.executable, "scripts/verify_independent_review.py"], cwd=ROOT, capture_output=True, text=True
    )
    assert run.returncode == 1 and "INDEPENDENT_REVIEW_GATE=BLOCKED" in run.stdout


# 12. Executor cannot self-create an independent PASS.
def test_executor_cannot_self_approve():
    schema = _json(ROOT / "schemas/external_review_attestation.schema.json")
    document = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_x",
        "repository": "r",
        "pr_number": 1,
        "reviewed_commit_sha": "0" * 40,
        "review_subject_digest": {"algorithm": "sha256", "encoding": "hex", "value": "0" * 64},
        "reviewer": {"principal_type": "EXECUTOR", "id": "hermes"},
        "verdict": "PASS",
        "criterion_results": [{"criterion_id": "x", "result": "PASS", "evidence_refs": ["e"]}],
        "source_ref": "x",
        "issued_at": "2026-01-01T00:00:00Z",
    }
    assert list(Draft202012Validator(schema).iter_errors(document))


# 13. GitHub API SUCCESS nhưng protection sai -> GIT-001 FAIL
def test_git_001_fail_when_protection_invalid(monkeypatch):
    live_path = ROOT / "review" / "LIVE_GITHUB_STATE.json"
    data = _json(live_path)
    data["api_status"] = "SUCCESS"
    data["rulesets"] = [{"deletion_protected": False, "non_fast_forward_protected": False, "pull_request_required": False, "executor_bypass_prohibited": False}]
    _patched_read_text(monkeypatch, {live_path: data})
    errors = validate_spec.validate_review_artifacts(ROOT)
    assert any("L9-REQ-GIT-001 predicate failed" in error for error in errors)


# 14. PR evidence thiếu -> GIT-002 không PASS
def test_git_002_fail_when_pr_evidence_missing(monkeypatch):
    live_path = ROOT / "review" / "LIVE_GITHUB_STATE.json"
    acc_path = ROOT / "review" / "ACCEPTANCE_RESULTS.json"
    data = _json(live_path)
    acceptance = _json(acc_path)
    data["state"] = "closed"
    for result in acceptance["criterion_results"]:
        if result["criterion_id"] == "L9-REQ-GIT-002":
            result["result"] = "PASS"
    _patched_read_text(monkeypatch, {live_path: data, acc_path: acceptance})
    errors = validate_spec.validate_review_artifacts(ROOT)
    assert "Git criterion L9-REQ-GIT-002 predicate failed: PR evidence missing or invalid" in errors


# 15. required checks từ stale SHA -> GIT-003 FAIL
def test_git_003_fail_when_required_checks_from_stale_sha(monkeypatch):
    live_path = ROOT / "review" / "LIVE_GITHUB_STATE.json"
    acc_path = ROOT / "review" / "ACCEPTANCE_RESULTS.json"
    data = _json(live_path)
    acceptance = _json(acc_path)
    data["check_runs"] = [{"name": "acceptance", "head_sha": "0" * 40}]
    for result in acceptance["criterion_results"]:
        if result["criterion_id"] == "L9-REQ-GIT-003":
            result["result"] = "PASS"
    _patched_read_text(monkeypatch, {live_path: data, acc_path: acceptance})
    errors = validate_spec.validate_review_artifacts(ROOT)
    assert "Git criterion L9-REQ-GIT-003 predicate failed: required status checks from stale SHA or missing" in errors


# 16. review artifact không bind exact HEAD -> GIT-004 FAIL
def test_git_004_fail_when_review_artifact_does_not_bind_exact_head(monkeypatch):
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    req_path = ROOT / "review" / "REVIEW_REQUEST.json"
    data = _json(req_path)
    data["head_commit_sha"] = "0" * 40
    _patched_read_text(monkeypatch, {req_path: data})
    errors = validate_spec.validate_review_artifacts(ROOT, head)
    assert any("L9-REQ-GIT-004 predicate failed" in error or "REVIEW_REQUEST.head_commit_sha does not match" in error for error in errors)


# 17. workflow changed nhưng chưa governance review -> GIT-006 không PASS
def test_git_006_fail_when_workflow_changed_without_governance_review(monkeypatch):
    acc_path = ROOT / "review" / "ACCEPTANCE_RESULTS.json"
    acc = _json(acc_path)
    for cr in acc["criterion_results"]:
        if cr["criterion_id"] == "L9-REQ-GIT-006":
            cr["result"] = "PASS"
    _patched_read_text(monkeypatch, {acc_path: acc})
    errors = validate_spec.validate_review_artifacts(ROOT)
    assert any("L9-REQ-GIT-006 must not be PASS by executor prior to independent governance review" in error for error in errors)


# 18. executor tự khai reviewer -> BLOCKED
def test_independent_review_gate_blocked_on_executor_self_claim(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_executor",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "hermes"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "executor_self_claim.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "hermes"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "executor cannot issue independent review attestation" in out or "executor actor" in out


# 19. untrusted actor -> BLOCKED
def test_independent_review_gate_blocked_on_untrusted_actor(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_untrusted",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "untrusted_actor.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "untrusted-attacker"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "not authorized" in out


# 20. reviewer mismatch -> BLOCKED
def test_independent_review_gate_blocked_on_reviewer_mismatch(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_mismatch",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "unknown-authority"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "mismatch.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "bqthai2310"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "not an authorized trusted review authority" in out


# 21. wrong repository -> BLOCKED
def test_independent_review_gate_blocked_on_wrong_repository(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_wrong_repo",
        "repository": "https://github.com/other-org/other-repo",
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "wrong_repo.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "architecture-guardian"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "repository mismatch" in out


# 22. wrong PR -> BLOCKED
def test_independent_review_gate_blocked_on_wrong_pr(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_wrong_pr",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 999,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "wrong_pr.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "architecture-guardian", "--pr-number", "1"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "pr_number mismatch" in out


# 23. stale SHA -> BLOCKED
def test_independent_review_gate_blocked_on_stale_sha(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_stale",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": "0" * 40,
        "review_subject_digest": {"algorithm": "sha256", "encoding": "hex", "value": "0" * 64},
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "stale.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "architecture-guardian"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "reviewed_commit_sha does not match target head SHA" in out


# 24. wrong digest -> BLOCKED
def test_independent_review_gate_blocked_on_wrong_digest(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_wrong_digest",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": {"algorithm": "sha256", "encoding": "hex", "value": "a" * 64},
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "wrong_digest.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "architecture-guardian"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "review_subject_digest does not match current subject digest" in out


# 25. missing GIT-005 -> BLOCKED
def test_independent_review_gate_blocked_on_missing_git_005(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_no_git005",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "no_git005.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "architecture-guardian"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "L9-REQ-GIT-005" in out


# 26. missing GIT-006 -> BLOCKED
def test_independent_review_gate_blocked_on_missing_git_006(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_no_git006",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "no_git006.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "architecture-guardian"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "L9-REQ-GIT-006" in out


# 27. fake evidence ref -> BLOCKED
def test_independent_review_gate_blocked_on_fake_evidence_ref(tmp_path, capsys):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": "reviewatt_fake_ref",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_fake_nonexistent"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "fake_ref.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "architecture-guardian"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "INDEPENDENT_REVIEW_GATE=BLOCKED" in out
    assert "unresolved or fake evidence ref" in out


# 28. trusted reviewer + exact binding + complete evidence -> PASS
def test_independent_review_gate_pass_with_trusted_reviewer_and_complete_evidence(tmp_path):
    import verify_independent_review
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    expected_subject = {
        "schema_version": "2.0.0",
        "subject_id": generate_review_artifacts.SUBJECT_ID,
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "head_commit_sha": head,
        "base_commit_sha": generate_review_artifacts.resolve_base(),
        "files": generate_review_artifacts.file_entries(ROOT),
        "config_digests": [],
        "policy_snapshot_id": "pol_f00_baseline",
        "acceptance_versions": ["2.1.0"],
    }
    digest = generate_review_artifacts.compute_subject_digest(expected_subject)
    att = {
        "schema_version": "2.0.0",
        "attestation_id": f"reviewatt_{head[:12]}",
        "repository": generate_review_artifacts.REPOSITORY_URL,
        "pr_number": 1,
        "reviewed_commit_sha": head,
        "review_subject_digest": digest,
        "reviewer": {"principal_type": "INDEPENDENT_REVIEWER", "id": "architecture-guardian"},
        "verdict": "PASS",
        "criterion_results": [
            {"criterion_id": "L9-REQ-GIT-005", "result": "PASS", "evidence_refs": ["ev_test_output"]},
            {"criterion_id": "L9-REQ-GIT-006", "result": "PASS", "evidence_refs": ["ev_workflow_static"]},
        ],
        "source_ref": "https://github.com/bqthai2310/HYAI/pull/1",
        "issued_at": "2026-10-05T15:00:00Z",
    }
    att_file = tmp_path / "valid_complete_attestation.json"
    att_file.write_text(json.dumps(att), encoding="utf-8")
    rc = verify_independent_review.main(["--head-sha", head, "--attestation-file", str(att_file), "--actor", "architecture-guardian"])
    assert rc == 0

