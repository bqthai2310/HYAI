#!/usr/bin/env python3
"""Validate all schema instances and content-addressed review artifacts."""
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from generate_review_artifacts import ROOT, compute_subject_digest, digest, normalize_bytes
import root_guard

def layout_digest(root: Path = ROOT) -> dict[str, str]:
    return root_guard.take_snapshot(root)["digest"]

def schema_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "schemas").glob("*.schema.json"))

def validate_schemas(root: Path = ROOT) -> list[str]:
    errors = []
    for path in schema_paths(root):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(doc)
        except Exception as e:
            errors.append(f"{path.relative_to(root)}: {e}")
    return errors

def _review_schema(doc: dict) -> str | None:
    schema_uri = doc.get("$schema")
    if isinstance(schema_uri, str) and schema_uri.endswith(".schema.json"):
        return schema_uri.rsplit("/", 1)[-1]
    if "review_subject_id" in doc and "criterion_results" in doc: return "acceptance_results.schema.json"
    if "subject_id" in doc and "head_commit_sha" in doc and "files" in doc: return "review_subject_manifest.schema.json"
    if "review_request_id" in doc and "head_commit_sha" in doc: return "review_request.schema.json"
    if "bundle_id" in doc and "items" in doc: return "evidence_bundle.schema.json"
    if "guard_result_id" in doc or ("root_layout_manifest_digest" in doc and "before_digest" in doc): return "root_guard_result.schema.json"
    if "attestation_id" in doc and "reviewer" in doc: return "external_review_attestation.schema.json"
    return None

def resolve_head(root: Path, target: str | None = None) -> str:
    if target:
        return target
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""

def is_valid_head(artifact_sha: str | None, target_sha: str | None, root: Path) -> bool:
    if not artifact_sha or not target_sha:
        return False
    return artifact_sha.lower() == target_sha.lower()

def validate_review_artifacts(root: Path = ROOT, target_head_sha: str | None = None) -> list[str]:
    errors = []
    review = root / "review"
    docs: dict[str, dict] = {}
    if not review.exists(): return ["review directory is missing"]
    for artifact in sorted(review.rglob("*.json")):
        if artifact.name == "LIVE_GITHUB_STATE.json":
            continue
        try:
            doc = json.loads(artifact.read_text(encoding="utf-8")); docs[artifact.name] = doc
            if not isinstance(doc, dict): raise ValueError("artifact must be a JSON object")
            name = _review_schema(doc)
            if name is None: raise ValueError("cannot identify a review artifact schema")
            schema = json.loads((root / "schemas" / name).read_text(encoding="utf-8"))
            errors.extend(f"{artifact.relative_to(root)}: {e.message}" for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(doc))
        except (OSError, ValueError, json.JSONDecodeError) as e: errors.append(f"{artifact.relative_to(root)}: {e}")
    head = resolve_head(root, target_head_sha); request = docs.get("REVIEW_REQUEST.json", {}); subject = docs.get("REVIEW_SUBJECT_MANIFEST.json", {})
    if not is_valid_head(request.get("head_commit_sha"), head, root): errors.append("REVIEW_REQUEST.head_commit_sha does not match current head commit SHA")
    if not is_valid_head(subject.get("head_commit_sha"), head, root): errors.append("REVIEW_SUBJECT_MANIFEST.head_commit_sha does not match current head commit SHA")
    if subject:
        base = None
        for ref in ("main", "origin/main"):
            try:
                base = subprocess.run(["git", "rev-parse", ref], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
                break
            except (OSError, subprocess.CalledProcessError):
                pass
        if base is not None:
            if subject.get("base_commit_sha") != base: errors.append("REVIEW_SUBJECT_MANIFEST.base_commit_sha does not match base branch")
        elif not isinstance(subject.get("base_commit_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", subject["base_commit_sha"]):
            errors.append("REVIEW_SUBJECT_MANIFEST.base_commit_sha is not a valid SHA")
        for entry in subject.get("files", []):
            path = root / entry.get("path", "")
            if not path.is_file() or entry.get("digest") != digest(normalize_bytes(path.read_bytes()) if path.is_file() else b""): errors.append(f"Review subject file digest mismatch: {entry.get('path')}")
        if subject.get("subject_digest") != compute_subject_digest(subject): errors.append("Review subject digest mismatch")
    guard = docs.get("ROOT_GUARD_RESULT.json", {})
    if guard:
        if guard.get("result") != "PASS": errors.append("Root guard result is not PASS")
        actual = layout_digest(root)
        if guard.get("before_digest") != actual: errors.append("Root guard before_digest mismatch")
        if guard.get("after_digest") != actual: errors.append("Root guard after_digest mismatch")
    evidence = docs.get("EVIDENCE_MANIFEST.json", {})
    if evidence:
        if evidence.get("review_subject_id") != subject.get("subject_id"): errors.append("Evidence manifest review_subject_id mismatch")
        for item in evidence.get("items", []):
            path = root / item.get("storage_ref", "")
            if not path.is_file() or item.get("digest") != digest(normalize_bytes(path.read_bytes()) if path.is_file() else b""): errors.append(f"Evidence digest mismatch: {item.get('storage_ref')}")
        live_items = [item for item in evidence.get("items", []) if item.get("evidence_id") == "ev_github_live_state"]
        if live_items:
            live_path = root / "review" / "LIVE_GITHUB_STATE.json"
            if not live_path.is_file(): errors.append("Live GitHub state evidence is missing")
            elif any(item.get("digest") != digest(normalize_bytes(live_path.read_bytes())) for item in live_items): errors.append("Evidence digest mismatch: review/LIVE_GITHUB_STATE.json")
    acceptance = docs.get("ACCEPTANCE_RESULTS.json", {})
    if acceptance:
        live_file = root / "review" / "LIVE_GITHUB_STATE.json"
        try: live_doc = json.loads(live_file.read_text(encoding="utf-8")) if live_file.is_file() else {}
        except Exception: live_doc = {}
        live_exists = bool(evidence and any(item.get("evidence_id") == "ev_github_live_state" for item in evidence.get("items", [])) and live_file.is_file())
        for criterion in acceptance.get("criterion_results", []):
            criterion_id, result, refs = criterion.get("criterion_id", ""), criterion.get("result"), criterion.get("evidence_refs", [])
            if criterion_id in {"L9-REQ-GIT-001", "L9-REQ-GIT-002", "L9-REQ-GIT-003", "L9-REQ-GIT-004"} and result == "PASS":
                if "ev_github_live_state" not in refs or not live_exists:
                    errors.append(f"Git criterion PASS requires live GitHub state evidence: {criterion_id}")
            if criterion_id == "L9-REQ-GIT-001" and result == "PASS":
                rulesets = live_doc.get("rulesets", [])
                ok = any(
                    r.get("deletion_protected") is True
                    and r.get("non_fast_forward_protected") is True
                    and r.get("pull_request_required") is True
                    and r.get("executor_bypass_prohibited") is True
                    for r in rulesets if isinstance(r, dict)
                ) if isinstance(rulesets, list) else False
                if not ok:
                    errors.append("Git criterion L9-REQ-GIT-001 predicate failed: main branch protection or executor bypass prohibition not verified in live state")
            if criterion_id == "L9-REQ-GIT-002" and result == "PASS":
                pr_num = live_doc.get("pr_number")
                pr_state = live_doc.get("state")
                pr_base = live_doc.get("base_ref")
                pr_head = live_doc.get("head_commit_sha")
                if not (isinstance(pr_num, int) and pr_num > 0 and pr_state == "open" and pr_base == "main" and is_valid_head(pr_head, head, root)):
                    errors.append("Git criterion L9-REQ-GIT-002 predicate failed: PR evidence missing or invalid")
            if criterion_id == "L9-REQ-GIT-003" and result == "PASS":
                check_runs = live_doc.get("check_runs", [])
                if not check_runs or any(cr.get("head_sha") != head for cr in check_runs):
                    errors.append("Git criterion L9-REQ-GIT-003 predicate failed: required status checks from stale SHA or missing")
            if criterion_id == "L9-REQ-GIT-004" and result == "PASS":
                if not (is_valid_head(request.get("head_commit_sha"), head, root) and is_valid_head(subject.get("head_commit_sha"), head, root)):
                    errors.append("Git criterion L9-REQ-GIT-004 predicate failed: review artifacts do not bind exact target head")
            if criterion_id == "L9-REQ-GIT-005" and result == "PASS":
                errors.append("L9-REQ-GIT-005 must not be PASS by executor")
            if criterion_id == "L9-REQ-GIT-006" and result == "PASS":
                has_wf_changes = any(f.get("path", "").startswith(".github/workflows/") for f in subject.get("files", []))
                if has_wf_changes:
                    errors.append("L9-REQ-GIT-006 must not be PASS by executor prior to independent governance review")
    return errors

def main(argv: list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--root",type=Path,default=ROOT); p.add_argument("--review-artifacts",action="store_true"); p.add_argument("--head-sha"); a=p.parse_args(argv)
    errors=validate_schemas(a.root)
    if a.review_artifacts: errors.extend(validate_review_artifacts(a.root,a.head_sha))
    if errors: print("SPEC_VALIDATION=FAIL"); print("\n".join(errors)); return 1
    print(f"SPEC_VALIDATION=PASS schemas={len(schema_paths(a.root))}" + (" review_artifacts=validated" if a.review_artifacts else "")); return 0
if __name__=="__main__": raise SystemExit(main())
