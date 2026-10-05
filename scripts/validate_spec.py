#!/usr/bin/env python3
"""Validate frozen schemas and fail closed on stale review artifacts."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REVIEW_SCHEMA_KEYS = {"review_request_id":"review_request.schema.json","verdict_id":"review_verdict.schema.json","attestation_id":"external_review_attestation.schema.json","subject_id":"review_subject_manifest.schema.json","criterion_results":"acceptance_results.schema.json","bundle_id":"evidence_bundle.schema.json","guard_result_id":"root_guard_result.schema.json"}
def digest(data: bytes) -> dict[str,str]: return {"algorithm":"sha256","encoding":"hex","value":hashlib.sha256(data).hexdigest()}
def normalize_bytes(data: bytes) -> bytes: return data.replace(b"\r\n", b"\n")
def canonical(v: Any) -> bytes: return json.dumps(v,sort_keys=True,separators=(",",":")).encode()
def compute_subject_digest(manifest: dict[str, Any]) -> dict[str, str]:
    material = {
        "acceptance_versions": sorted(manifest.get("acceptance_versions", [])),
        "base_commit_sha": manifest.get("base_commit_sha", ""),
        "config_digests": sorted(manifest.get("config_digests", []), key=canonical),
        "files": sorted(manifest.get("files", []), key=lambda x: x.get("path", "")),
        "head_commit_sha": manifest.get("head_commit_sha", ""),
        "policy_snapshot_id": manifest.get("policy_snapshot_id", ""),
        "repository": manifest.get("repository", ""),
    }
    return digest(canonical(material))
def schema_paths(root: Path=ROOT)->list[Path]: return sorted((root/"schemas").rglob("*.json"))
def validate_schemas(root: Path=ROOT)->list[str]:
    errors=[]
    for p in schema_paths(root):
        try: Draft202012Validator.check_schema(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e: errors.append(f"{p.relative_to(root)}: {e}")
    return errors
def _review_schema(doc: dict[str,Any])->str|None:
    found=[s for k,s in REVIEW_SCHEMA_KEYS.items() if k in doc]
    return found[0] if len(found)==1 else None
def resolve_head(root: Path, explicit: str|None=None)->str|None:
    if explicit or os.getenv("PR_HEAD_SHA") or os.getenv("GITHUB_SHA"): return explicit or os.getenv("PR_HEAD_SHA") or os.getenv("GITHUB_SHA")
    try: return subprocess.run(["git","rev-parse","HEAD"],cwd=root,check=True,capture_output=True,text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError): return None
def subject_files(root: Path)->list[dict[str,Any]]:
    excluded={"review", ".git", "__pycache__"}
    files=sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and not (excluded & set(p.relative_to(root).parts)) and p.relative_to(root).parts[:2] not in {(".hyai", "cache"), (".hyai", "tmp"), (".hyai", "runtime")})
    return [{"path":p,"digest":digest(normalize_bytes((root/p).read_bytes()))} for p in files]
def layout_digest(root: Path)->dict[str,str]:
    entries=sorted(p.name for p in root.iterdir() if p.name!=".git")
    return digest("\n".join(entries).encode())
def validate_review_artifacts(root: Path=ROOT, target_head_sha: str|None=None)->list[str]:
    errors=[]; review=root/"review"; docs: dict[str,dict[str,Any]]={}
    def is_valid_head(artifact_sha: str | None, target_sha: str | None, root: Path) -> bool:
        if not artifact_sha or not target_sha:
            return False
        return artifact_sha.lower() == target_sha.lower()
    if not review.exists(): return ["review directory is missing"]
    for artifact in sorted(review.rglob("*.json")):
        # This is API-collected evidence rather than a governed review artifact.
        if artifact.name == "LIVE_GITHUB_STATE.json":
            continue
        try:
            doc=json.loads(artifact.read_text(encoding="utf-8")); docs[artifact.name]=doc
            if not isinstance(doc,dict): raise ValueError("artifact must be a JSON object")
            name=_review_schema(doc)
            if name is None: raise ValueError("cannot identify a review artifact schema")
            schema=json.loads((root/"schemas"/name).read_text(encoding="utf-8"))
            errors.extend(f"{artifact.relative_to(root)}: {e.message}" for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(doc))
        except (OSError,ValueError,json.JSONDecodeError) as e: errors.append(f"{artifact.relative_to(root)}: {e}")
    head=resolve_head(root,target_head_sha); request=docs.get("REVIEW_REQUEST.json",{}); subject=docs.get("REVIEW_SUBJECT_MANIFEST.json",{})
    if not is_valid_head(request.get("head_commit_sha"), head, root): errors.append("REVIEW_REQUEST.head_commit_sha does not match current head commit SHA")
    if not is_valid_head(subject.get("head_commit_sha"), head, root): errors.append("REVIEW_SUBJECT_MANIFEST.head_commit_sha does not match current head commit SHA")
    if subject:
        base = None
        for ref in ("main", "origin/main"):
            try:
                base=subprocess.run(["git","rev-parse",ref],cwd=root,check=True,capture_output=True,text=True).stdout.strip()
                break
            except (OSError,subprocess.CalledProcessError):
                pass
        if base is not None:
            if subject.get("base_commit_sha")!=base: errors.append("REVIEW_SUBJECT_MANIFEST.base_commit_sha does not match base branch")
        elif not isinstance(subject.get("base_commit_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", subject["base_commit_sha"]):
            errors.append("REVIEW_SUBJECT_MANIFEST.base_commit_sha is not a valid SHA")
        for entry in subject.get("files",[]):
            path=root/entry.get("path","")
            if not path.is_file() or entry.get("digest")!=digest(normalize_bytes(path.read_bytes()) if path.is_file() else b""): errors.append(f"Review subject file digest mismatch: {entry.get('path')}")
        if subject.get("subject_digest") != compute_subject_digest(subject): errors.append("Review subject digest mismatch")
    guard=docs.get("ROOT_GUARD_RESULT.json",{})
    if guard:
        if guard.get("result")!="PASS": errors.append("Root guard result is not PASS")
        actual=layout_digest(root)
        if guard.get("before_digest")!=actual: errors.append("Root guard before_digest mismatch")
        if guard.get("after_digest")!=actual: errors.append("Root guard after_digest mismatch")
    evidence=docs.get("EVIDENCE_MANIFEST.json",{})
    if evidence:
        if evidence.get("review_subject_id")!=subject.get("subject_id"): errors.append("Evidence manifest review_subject_id mismatch")
        for item in evidence.get("items",[]):
            path=root/item.get("storage_ref","")
            if not path.is_file() or item.get("digest")!=digest(normalize_bytes(path.read_bytes()) if path.is_file() else b""): errors.append(f"Evidence digest mismatch: {item.get('storage_ref')}")
        live_items = [item for item in evidence.get("items", []) if item.get("evidence_id") == "ev_github_live_state"]
        if live_items:
            live_path = root / "review" / "LIVE_GITHUB_STATE.json"
            if not live_path.is_file(): errors.append("Live GitHub state evidence is missing")
            elif any(item.get("digest") != digest(normalize_bytes(live_path.read_bytes())) for item in live_items): errors.append("Evidence digest mismatch: review/LIVE_GITHUB_STATE.json")
    acceptance = docs.get("ACCEPTANCE_RESULTS.json", {})
    if acceptance:
        live_exists = bool(evidence and any(item.get("evidence_id") == "ev_github_live_state" for item in evidence.get("items", [])) and (root / "review" / "LIVE_GITHUB_STATE.json").is_file())
        for criterion in acceptance.get("criterion_results", []):
            criterion_id, result, refs = criterion.get("criterion_id", ""), criterion.get("result"), criterion.get("evidence_refs", [])
            if criterion_id in {"L9-REQ-GIT-001", "L9-REQ-GIT-002", "L9-REQ-GIT-003", "L9-REQ-GIT-004"} and result == "PASS" and ("ev_github_live_state" not in refs or not live_exists):
                errors.append(f"Git criterion PASS requires live GitHub state evidence: {criterion_id}")
            if criterion_id == "L9-REQ-GIT-005" and result == "PASS": errors.append("L9-REQ-GIT-005 must not be PASS by executor")
    return errors
def main(argv: list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--root",type=Path,default=ROOT); p.add_argument("--review-artifacts",action="store_true"); p.add_argument("--head-sha"); a=p.parse_args(argv)
    errors=validate_schemas(a.root)
    if a.review_artifacts: errors.extend(validate_review_artifacts(a.root,a.head_sha))
    if errors: print("SPEC_VALIDATION=FAIL"); print("\n".join(errors)); return 1
    print(f"SPEC_VALIDATION=PASS schemas={len(schema_paths(a.root))}" + (" review_artifacts=validated" if a.review_artifacts else "")); return 0
if __name__=="__main__": raise SystemExit(main())
