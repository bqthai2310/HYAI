"""Regression coverage for the F00 review hardening corrections."""
from __future__ import annotations
import hashlib, json, shutil, subprocess, sys
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import root_guard
import validate_spec

def _json(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, value): path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
def _root_copy(tmp_path: Path) -> Path:
    manifest = _json(ROOT / "ROOT_LAYOUT_MANIFEST.json")
    (tmp_path / "ROOT_LAYOUT_MANIFEST.json").write_bytes((ROOT / "ROOT_LAYOUT_MANIFEST.json").read_bytes())
    for name in manifest["allowed_root_directories"]: (tmp_path / name).mkdir()
    for name in manifest["allowed_root_files"]:
        if name != "ROOT_LAYOUT_MANIFEST.json": (tmp_path / name).write_text("", encoding="utf-8")
    return tmp_path

def test_stale_head_sha_rejected():
    assert "REVIEW_REQUEST.head_commit_sha does not match current head commit SHA" in validate_spec.validate_review_artifacts(ROOT, "0" * 40)
def test_stale_review_subject_digest_rejected(monkeypatch):
    path=ROOT/"review/REVIEW_SUBJECT_MANIFEST.json"; doc=_json(path); doc["subject_digest"]["value"]="0"*64
    original=Path.read_text; monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: json.dumps(doc) if self == path else original(self, *a, **k))
    assert "Review subject digest mismatch" in validate_spec.validate_review_artifacts(ROOT)
def test_stale_evidence_bundle_rejected(monkeypatch):
    path=ROOT/"review/EVIDENCE_MANIFEST.json"; doc=_json(path); doc["items"][0]["digest"]["value"]="0"*64
    original=Path.read_text; monkeypatch.setattr(Path,"read_text",lambda self,*a,**k: json.dumps(doc) if self==path else original(self,*a,**k))
    assert any(e.startswith("Evidence digest mismatch:") for e in validate_spec.validate_review_artifacts(ROOT))
def test_unauthorized_root_entry_rejected(tmp_path):
    root=_root_copy(tmp_path); snap=root_guard.take_snapshot(root); (root/"rogue").mkdir()
    assert root_guard.verify_root(snap,"test",root)["result"] == "FAIL_QUARANTINED"
def test_modified_frozen_root_manifest_rejected(tmp_path):
    root=_root_copy(tmp_path); (root/"ROOT_LAYOUT_MANIFEST.json").write_text("{}",encoding="utf-8")
    assert root_guard.verify_root(root_guard._digest("before"),"test",root)["result"] == "FAIL_QUARANTINED"
def test_executor_cannot_self_approve():
    schema=_json(ROOT/"schemas/external_review_attestation.schema.json")
    doc={"schema_version":"2","attestation_id":"reviewatt_x","repository":"r","pr_number":1,"reviewed_commit_sha":"0"*40,"review_subject_digest":{"algorithm":"sha256","encoding":"hex","value":"0"*64},"reviewer":{"principal_type":"EXECUTOR","id":"hermes"},"verdict":"PASS","criterion_results":[{"criterion_id":"x","result":"PASS","evidence_refs":["e"]}],"source_ref":"x","issued_at":"2026-01-01T00:00:00Z"}
    assert list(Draft202012Validator(schema).iter_errors(doc))
def test_criterion_pass_without_matching_evidence_rejected():
    schema=_json(ROOT/"schemas/acceptance_results.schema.json")
    doc={"schema_version":"2","review_subject_id":"s","criterion_results":[{"criterion_id":"x","result":"PASS","evidence_refs":[]}]}
    assert list(Draft202012Validator(schema).iter_errors(doc))
def test_static_yaml_presence_does_not_prove_live_platform_state():
    workflow=(ROOT/".github/workflows/review-artifact-gate.yml").read_text(encoding="utf-8")
    evidence=_json(ROOT/"review/EVIDENCE_MANIFEST.json")
    assert "pull_request" in workflow
    assert "ev_github_live_state" not in {item["evidence_id"] for item in evidence["items"]}
def test_missing_external_independent_pass_blocks_gate():
    path=ROOT/"review/EXTERNAL_REVIEW_ATTESTATION.json"
    if path.exists(): pytest.skip("repository contains an external attestation")
    run=subprocess.run([sys.executable,"scripts/verify_independent_review.py"],cwd=ROOT,capture_output=True,text=True)
    assert run.returncode == 1 and "INDEPENDENT_REVIEW_GATE=BLOCKED" in run.stdout
