#!/usr/bin/env python3
"""Fail-closed verifier for an independent external review attestation."""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from generate_review_artifacts import ROOT, resolve_head

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--head-sha"); parser.add_argument("--attestation-file", type=Path); args=parser.parse_args(argv)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "review/EXTERNAL_REVIEW_ATTESTATION.json"], cwd=ROOT, capture_output=True, text=True)
    if tracked.returncode == 0:
        print("INDEPENDENT_REVIEW_GATE=BLOCKED (independent attestation inside reviewed commit is rejected as self-referential)")
        return 1
    supplied = args.attestation_file or (Path(os.environ["EXTERNAL_ATTESTATION_PATH"]) if os.getenv("EXTERNAL_ATTESTATION_PATH") else None)
    if supplied is None:
        print("INDEPENDENT_REVIEW_GATE=BLOCKED (missing external review attestation)")
        return 1
    path=supplied
    if not path.is_file(): print("INDEPENDENT_REVIEW_GATE=BLOCKED (missing external review attestation)"); return 1
    try:
        doc=json.loads(path.read_text(encoding="utf-8")); schema=json.loads((ROOT/"schemas"/"external_review_attestation.schema.json").read_text(encoding="utf-8"))
        failures=[e.message for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(doc)]
        if doc.get("reviewed_commit_sha") != resolve_head(args.head_sha): failures.append("reviewed_commit_sha does not match target head SHA")
        subject_path = ROOT / "review" / "REVIEW_SUBJECT_MANIFEST.json"
        if not subject_path.is_file(): failures.append("review subject manifest is missing")
        elif doc.get("review_subject_digest") != json.loads(subject_path.read_text(encoding="utf-8")).get("subject_digest"): failures.append("review_subject_digest does not match current subject digest")
        reviewer=doc.get("reviewer",{});
        if reviewer.get("principal_type") not in {"PO","INDEPENDENT_REVIEWER"} or reviewer.get("id") in {"hermes","executor"}: failures.append("reviewer is not independent")
        if doc.get("verdict") != "PASS": failures.append("verdict is not PASS")
        if any(c.get("result")!="PASS" or not c.get("evidence_refs") for c in doc.get("criterion_results",[])): failures.append("criterion results require PASS with evidence_refs")
    except Exception as error: failures=[str(error)]
    if failures: print("INDEPENDENT_REVIEW_GATE=BLOCKED " + "; ".join(failures)); return 1
    print("INDEPENDENT_REVIEW_GATE=PASS"); return 0
if __name__ == "__main__": raise SystemExit(main())
