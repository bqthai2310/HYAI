#!/usr/bin/env python3
"""Fail-closed verifier for an independent external review attestation."""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request
from jsonschema import Draft202012Validator, FormatChecker
from generate_review_artifacts import ROOT, resolve_head, resolve_base, compute_subject_digest, file_entries, SUBJECT_ID, REPOSITORY_URL

# Trusted Review Authorities registry for HYAI F00 governance
TRUSTED_REVIEW_AUTHORITIES: dict[str, dict[str, Any]] = {
    "architecture-guardian": {
        "principal_type": "INDEPENDENT_REVIEWER",
        "allowed_actors": {"architecture-guardian", "bqthai2310", "guardian-bot", "independent-reviewer"},
    },
    "independent-reviewer": {
        "principal_type": "INDEPENDENT_REVIEWER",
        "allowed_actors": {"independent-reviewer", "bqthai2310"},
    },
    "po-guardian": {
        "principal_type": "PO",
        "allowed_actors": {"bqthai2310", "po-guardian"},
    },
}

EXECUTOR_IDENTITIES = frozenset({
    "hermes", "executor", "implementer", "c2-coder", "coder", "runtime-worker", "github-actions[bot]",
})

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

def resolve_actor(args: argparse.Namespace) -> str | None:
    if args.actor:
        return args.actor.strip()
    for env_var in ("ATTESTATION_ACTOR", "REVIEWER_ACTOR", "GITHUB_ACTOR"):
        val = os.getenv(env_var)
        if val and val.strip():
            return val.strip()
    return None

def get_known_evidence_ids() -> set[str]:
    evidence_manifest_path = ROOT / "review" / "EVIDENCE_MANIFEST.json"
    if evidence_manifest_path.is_file():
        try:
            doc = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))
            return {item.get("evidence_id") for item in doc.get("items", []) if isinstance(item, dict) and item.get("evidence_id")}
        except Exception:
            pass
    return {
        "ev_test_output",
        "ev_root_guard",
        "ev_spec_validation",
        "ev_workflow_static",
        "ev_github_live_state",
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head-sha")
    parser.add_argument("--attestation-file", type=Path)
    parser.add_argument("--attestation-json")
    parser.add_argument("--attestation-url")
    parser.add_argument("--actor", help="Authenticated reviewer provenance actor")
    parser.add_argument("--pr-number", type=int, default=1)
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

        # 1. Repository binding
        if doc.get("repository") != REPOSITORY_URL:
            failures.append(f"repository mismatch: expected {REPOSITORY_URL}, got {doc.get('repository')}")

        # 2. PR number binding
        if doc.get("pr_number") != args.pr_number:
            failures.append(f"pr_number mismatch: expected {args.pr_number}, got {doc.get('pr_number')}")

        # 3. Exact head commit SHA binding
        target_head = resolve_head(args.head_sha)
        if doc.get("reviewed_commit_sha") != target_head:
            failures.append("reviewed_commit_sha does not match target head SHA")

        # 4. Exact review subject digest binding
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

        # 5. Reviewer authority & authentication boundary
        reviewer = doc.get("reviewer", {})
        principal_type = reviewer.get("principal_type")
        reviewer_id = reviewer.get("id", "")

        if principal_type == "EXECUTOR" or reviewer_id.lower() in EXECUTOR_IDENTITIES:
            failures.append("executor cannot issue independent review attestation")
        elif reviewer_id not in TRUSTED_REVIEW_AUTHORITIES:
            failures.append(f"reviewer identity '{reviewer_id}' is not an authorized trusted review authority")
        else:
            auth_spec = TRUSTED_REVIEW_AUTHORITIES[reviewer_id]
            if principal_type != auth_spec["principal_type"]:
                failures.append(f"reviewer principal_type mismatch: expected {auth_spec['principal_type']}, got {principal_type}")

            actor = resolve_actor(args)
            if not actor:
                failures.append("missing reviewer authentication provenance (no authenticated actor)")
            elif actor.lower() in EXECUTOR_IDENTITIES:
                failures.append(f"executor actor '{actor}' cannot self-proclaim or dispatch review attestation")
            elif actor not in auth_spec["allowed_actors"]:
                failures.append(f"actor '{actor}' is not authorized for trusted reviewer '{reviewer_id}'")

            gh_actor = os.getenv("GITHUB_ACTOR")
            if gh_actor and gh_actor.lower() in EXECUTOR_IDENTITIES:
                failures.append(f"workflow_dispatch actor '{gh_actor}' is an executor and cannot dispatch review gate")
            elif gh_actor and gh_actor not in auth_spec["allowed_actors"]:
                failures.append(f"workflow_dispatch actor '{gh_actor}' is not authorized for reviewer '{reviewer_id}'")

        # 6. Verdict validation
        if doc.get("verdict") != "PASS":
            failures.append("verdict is not PASS")

        # 7. Criterion coverage gate (must cover L9-REQ-GIT-005 and L9-REQ-GIT-006)
        c_results = doc.get("criterion_results", [])
        if not c_results:
            failures.append("criterion_results cannot be empty")
        else:
            c_map = {c.get("criterion_id"): c for c in c_results if isinstance(c, dict)}
            if "L9-REQ-GIT-005" not in c_map or c_map["L9-REQ-GIT-005"].get("result") != "PASS":
                failures.append("attestation missing required passing result for L9-REQ-GIT-005")
            if "L9-REQ-GIT-006" not in c_map or c_map["L9-REQ-GIT-006"].get("result") != "PASS":
                failures.append("attestation missing required passing result for L9-REQ-GIT-006")

            # 8. Evidence ref validation (must resolve against known evidence items)
            known_evidence = get_known_evidence_ids()
            for c in c_results:
                if c.get("result") != "PASS":
                    failures.append(f"criterion {c.get('criterion_id')} is not PASS")
                refs = c.get("evidence_refs", [])
                if not refs:
                    failures.append(f"criterion {c.get('criterion_id')} missing evidence_refs")
                for ref in refs:
                    if not isinstance(ref, str) or not ref.startswith("ev_") or ref not in known_evidence:
                        failures.append(f"unresolved or fake evidence ref: '{ref}' in criterion {c.get('criterion_id')}")

    except Exception as error:
        failures.append(str(error))

    if failures:
        print("INDEPENDENT_REVIEW_GATE=BLOCKED " + "; ".join(failures))
        return 1

    print("INDEPENDENT_REVIEW_GATE=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
