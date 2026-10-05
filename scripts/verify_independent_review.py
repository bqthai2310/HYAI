#!/usr/bin/env python3
"""Fail-closed verifier for an independent external review attestation."""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
from urllib.request import urlopen, Request
from jsonschema import Draft202012Validator, FormatChecker
from generate_review_artifacts import ROOT, resolve_head, resolve_base, compute_subject_digest, file_entries, SUBJECT_ID, REPOSITORY_URL

def load_attestation(args: argparse.Namespace) -> tuple[dict | None, str | None]:
    if args.attestation_json:
        try:
            return json.loads(args.attestation_json), None
        except Exception as e:
            return None, f"invalid attestation json: {e}"
    if os.getenv("EXTERNAL_ATTESTATION_JSON"):
        try:
            return json.loads(os.environ["EXTERNAL_ATTESTATION_JSON"]), None
        except Exception as e:
            return None, f"invalid EXTERNAL_ATTESTATION_JSON: {e}"
    file_path = args.attestation_file or (Path(os.environ["EXTERNAL_ATTESTATION_PATH"]) if os.getenv("EXTERNAL_ATTESTATION_PATH") else None)
    if file_path:
        p = Path(file_path)
        if not p.is_file():
            return None, f"attestation file not found: {p}"
        try:
            return json.loads(p.read_text(encoding="utf-8")), None
        except Exception as e:
            return None, f"failed reading attestation file: {e}"
    url = args.attestation_url or os.getenv("EXTERNAL_ATTESTATION_URL")
    if url:
        try:
            req = Request(url, headers={"User-Agent": "HYAI-Verifier"})
            with urlopen(req, timeout=15) as resp:
                return json.load(resp), None
        except Exception as e:
            return None, f"failed fetching attestation url: {e}"
    return None, None

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head-sha")
    parser.add_argument("--attestation-file", type=Path)
    parser.add_argument("--attestation-json")
    parser.add_argument("--attestation-url")
    args = parser.parse_args(argv)

    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "review/EXTERNAL_REVIEW_ATTESTATION.json"], cwd=ROOT, capture_output=True, text=True)
    if tracked.returncode == 0:
        print("INDEPENDENT_REVIEW_GATE=BLOCKED (independent attestation inside reviewed commit is rejected as self-referential)")
        return 1

    doc, err = load_attestation(args)
    if err:
        print(f"INDEPENDENT_REVIEW_GATE=BLOCKED ({err})")
        return 1
    if doc is None:
        print("INDEPENDENT_REVIEW_GATE=BLOCKED (missing external review attestation)")
        return 1

    failures = []
    try:
        schema = json.loads((ROOT / "schemas" / "external_review_attestation.schema.json").read_text(encoding="utf-8"))
        for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(doc):
            failures.append(e.message)

        target_head = resolve_head(args.head_sha)
        if doc.get("reviewed_commit_sha") != target_head:
            failures.append("reviewed_commit_sha does not match target head SHA")

        expected_subject = {
            "schema_version": "2.0.0",
            "subject_id": SUBJECT_ID,
            "repository": REPOSITORY_URL,
            "head_commit_sha": target_head,
            "base_commit_sha": resolve_base(),
            "files": file_entries(ROOT),
            "config_digests": [],
            "policy_snapshot_id": "pol_f00_baseline",
            "acceptance_versions": ["2.1.0"],
        }
        expected_digest = compute_subject_digest(expected_subject)
        if doc.get("review_subject_digest") != expected_digest:
            failures.append("review_subject_digest does not match current subject digest")

        reviewer = doc.get("reviewer", {})
        if reviewer.get("principal_type") not in {"PO", "INDEPENDENT_REVIEWER"} or reviewer.get("id") in {"hermes", "executor", "IMPLEMENTER"}:
            failures.append("reviewer is not independent")

        if doc.get("verdict") != "PASS":
            failures.append("verdict is not PASS")

        c_results = doc.get("criterion_results", [])
        if not c_results:
            failures.append("criterion_results cannot be empty")
        elif any(c.get("result") != "PASS" or not c.get("evidence_refs") for c in c_results):
            failures.append("criterion results require PASS with evidence_refs")

    except Exception as error:
        failures.append(str(error))

    if failures:
        print("INDEPENDENT_REVIEW_GATE=BLOCKED " + "; ".join(failures))
        return 1

    print("INDEPENDENT_REVIEW_GATE=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
