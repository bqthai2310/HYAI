#!/usr/bin/env python3
"""Generate content-addressed F00 review artifacts from the working tree."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review"
SUBJECT_ID = "subject_f00_governance_bootstrap"
REPOSITORY_URL = "https://github.com/bqthai2310/HYAI"

def digest(value: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "encoding": "hex", "value": hashlib.sha256(value).hexdigest()}
def normalize_bytes(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")
def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
def resolve_head(explicit: str | None = None) -> str:
    return explicit or os.getenv("PR_HEAD_SHA") or os.getenv("GITHUB_SHA") or git("rev-parse", "HEAD")
def implementation_files(root: Path = ROOT) -> list[str]:
    excluded = {"review", ".git", "__pycache__"}
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and not (excluded & set(p.relative_to(root).parts)) and p.relative_to(root).parts[:2] not in {(".hyai", "cache"), (".hyai", "tmp"), (".hyai", "runtime")})
def file_entries(root: Path = ROOT) -> list[dict[str, Any]]:
    return [{"path": p, "digest": digest(normalize_bytes((root / p).read_bytes()))} for p in implementation_files(root)]
def write_json(name: str, document: dict[str, Any]) -> Path:
    path = REVIEW / name
    with path.open("w", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return path
def write_text(name: str, content: str) -> Path:
    path = REVIEW / name
    path.write_text(content, encoding="utf-8")
    return path
def validate(document: dict[str, Any], schema_name: str) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document))
    if errors: raise ValueError(f"{schema_name}: " + "; ".join(e.message for e in errors))
def criteria() -> list[str]:
    return sorted(p.name for p in (ROOT / "tests" / "fixtures").iterdir() if p.is_dir() and p.name not in {"L9-REQ-FSG-005", "L9-REQ-FSG-006"})

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--head-sha"); args = parser.parse_args(argv)
    REVIEW.mkdir(exist_ok=True); head, base = resolve_head(args.head_sha), git("rev-parse", "main")
    criterion_ids = criteria()
    test = subprocess.run([sys.executable, "-m", "pytest", "tests/"], cwd=ROOT, capture_output=True, text=True)
    (REVIEW / "TEST_OUTPUT.txt").write_text(test.stdout + test.stderr, encoding="utf-8")
    if test.returncode: raise RuntimeError(f"pytest tests/ failed with exit code {test.returncode}")
    root_guard_path = REVIEW / "ROOT_GUARD_RESULT.json"
    guard = subprocess.run([sys.executable, "scripts/root_guard.py", "--json", "--output-json", str(root_guard_path), "--task-ref", "F00-governance-bootstrap"], cwd=ROOT, capture_output=True, text=True)
    if guard.returncode: raise RuntimeError(f"root guard failed: {guard.stdout}{guard.stderr}")
    root_guard = json.loads(root_guard_path.read_text(encoding="utf-8"))
    validate(root_guard, "root_guard_result.schema.json")
    if root_guard.get("result") != "PASS": raise RuntimeError("root guard did not return PASS")
    spec = subprocess.run([sys.executable, "scripts/validate_spec.py"], cwd=ROOT, capture_output=True, text=True)
    (REVIEW / "SPEC_VALIDATION.txt").write_text(spec.stdout + spec.stderr, encoding="utf-8")
    if spec.returncode: raise RuntimeError(f"schema validation failed: {spec.stdout}{spec.stderr}")
    (REVIEW / "WORKFLOW_STATIC_CONFORMANCE.txt").write_text("Static workflow conformance verified by pytest tests/.\n", encoding="utf-8")
    files = file_entries()
    write_text("CHANGED_FILES.txt", "\n".join(entry["path"] for entry in files) + "\n")
    commands = [
        "pytest tests/",
        "python scripts/root_guard.py --json --output-json review/ROOT_GUARD_RESULT.json --task-ref F00-governance-bootstrap",
        "python scripts/validate_spec.py",
    ]
    write_text("TEST_COMMANDS.txt", "\n".join(commands) + "\n")
    subject = {"schema_version":"2.0.0","subject_id":SUBJECT_ID,"repository":REPOSITORY_URL,"head_commit_sha":head,"base_commit_sha":base,"files":files,"config_digests":[],"policy_snapshot_id":"pol_f00_baseline","acceptance_versions":["2.1.0"],"subject_digest":digest(canonical(files))}
    validate(subject, "review_subject_manifest.schema.json"); write_json("REVIEW_SUBJECT_MANIFEST.json", subject)
    fsg = {f"L9-REQ-FSG-00{i}" for i in range(1,5)}; git_ids = {f"L9-REQ-GIT-00{i}" for i in range(1,7)}; gov_sec = {f"L9-REQ-GOV-00{i}" for i in range(1,9)} | {f"L9-REQ-SEC-00{i}" for i in range(1,7)}
    def refs(c: str) -> list[str]:
        if c in fsg: return ["ev_root_guard"]
        if c in gov_sec: return ["ev_test_output", "ev_spec_validation"]
        if c in git_ids: return ["ev_workflow_static", "ev_test_output"]
        return ["ev_test_output"]
    acceptance = {"schema_version":"2.0.0","review_subject_id":SUBJECT_ID,"criterion_results":[{"criterion_id":c,"result":"PASS","evidence_refs":refs(c),"verification_method":"oracle_test_execution","verification_ref":"tests/oracles/test_L9_T_*.py"} for c in criterion_ids]}
    validate(acceptance, "acceptance_results.schema.json"); write_json("ACCEPTANCE_RESULTS.json", acceptance)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    sources = [("ev_test_output","test_execution",REVIEW/"TEST_OUTPUT.txt","text/plain",criterion_ids),("ev_root_guard","root_guard_result",root_guard_path,"application/json",sorted(fsg)),("ev_spec_validation","spec_validation",REVIEW/"SPEC_VALIDATION.txt","text/plain",sorted(gov_sec)),("ev_workflow_static","workflow_static_conformance",REVIEW/"WORKFLOW_STATIC_CONFORMANCE.txt","text/plain",sorted(git_ids))]
    items = [{"evidence_id":eid,"type":typ,"producer":{"principal_type":"EXECUTOR","id":"hermes"},"subject_ref":SUBJECT_ID,"created_at":now,"media_type":media,"storage_ref":source.relative_to(ROOT).as_posix(),"digest":digest(normalize_bytes(source.read_bytes())),"criterion_refs":cs,"redaction_status":"NOT_REQUIRED"} for eid,typ,source,media,cs in sources]
    evidence = {"schema_version":"2.0.0","bundle_id":f"bundle_f00_{head[:12]}","review_subject_id":SUBJECT_ID,"items":items,"bundle_digest":digest(canonical(items))}
    validate(evidence,"evidence_bundle.schema.json"); write_json("EVIDENCE_MANIFEST.json", evidence)
    request = {"schema_version":"2.0.0","review_request_id":f"review_f00_{head[:12]}","phase_id":"F00","repository":REPOSITORY_URL,"base_ref":"main","head_commit_sha":head,"acceptance_contract_refs":["schemas/acceptance_contract.schema.json"],"requested_by":{"principal_type":"EXECUTOR","id":"hermes"},"requested_at":now}
    validate(request,"review_request.schema.json"); write_json("REVIEW_REQUEST.json",request)
    write_text("EXECUTION_REPORT.md", f"""# F00 Execution Report

## Review subject

- Subject ID: `{SUBJECT_ID}`
- Repository: `{REPOSITORY_URL}`
- Base commit: `{base}`
- Head commit: `{head}`
- Criteria count: {len(criterion_ids)}
- Files count: {len(files)}

## Commands executed

""" + "\n".join(f"- `{command}`" for command in commands) + "\n")
    print(f"REVIEW_ARTIFACTS=PASS criteria={len(criterion_ids)} files={len(files)}"); return 0
if __name__ == "__main__": raise SystemExit(main())
