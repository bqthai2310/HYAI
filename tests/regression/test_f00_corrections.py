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
