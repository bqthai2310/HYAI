#!/usr/bin/env python3
"""Fail-closed verifier for an independent external review attestation."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from generate_review_artifacts import ROOT, digest, canonical, implementation_files, normalize_bytes, resolve_head

def file_entries() -> list[dict[str, object]]:
    return [{"path": path, "digest": digest(normalize_bytes((ROOT / path).read_bytes()))} for path in implementation_files()]

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--head-sha"); args=parser.parse_args(argv)
    path=ROOT/"review"/"EXTERNAL_REVIEW_ATTESTATION.json"
    if not path.is_file(): print("INDEPENDENT_REVIEW_GATE=BLOCKED (missing external review attestation)"); return 1
    try:
        doc=json.loads(path.read_text(encoding="utf-8")); schema=json.loads((ROOT/"schemas"/"external_review_attestation.schema.json").read_text(encoding="utf-8"))
        failures=[e.message for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(doc)]
        if doc.get("reviewed_commit_sha") != resolve_head(args.head_sha): failures.append("reviewed_commit_sha does not match target head SHA")
        if doc.get("review_subject_digest") != digest(canonical(file_entries())): failures.append("review_subject_digest does not match current subject digest")
        reviewer=doc.get("reviewer",{});
        if reviewer.get("principal_type") not in {"PO","INDEPENDENT_REVIEWER"} or reviewer.get("id") in {"hermes","executor"}: failures.append("reviewer is not independent")
        if doc.get("verdict") != "PASS": failures.append("verdict is not PASS")
        if any(c.get("result")!="PASS" or not c.get("evidence_refs") for c in doc.get("criterion_results",[])): failures.append("criterion results require PASS with evidence_refs")
    except Exception as error: failures=[str(error)]
    if failures: print("INDEPENDENT_REVIEW_GATE=BLOCKED " + "; ".join(failures)); return 1
    print("INDEPENDENT_REVIEW_GATE=PASS"); return 0
if __name__ == "__main__": raise SystemExit(main())
