#!/usr/bin/env python3
"""Collect the live GitHub PR, branch-protection, and check-run state used by F00 review."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def github_get(url: str, token: str | None) -> object:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def get_auth_token() -> str | None:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token
    for command, input_text in (
        (["gh", "auth", "token"], None),
        (["git", "credential", "fill"], "protocol=https\nhost=github.com\n\n"),
    ):
        try:
            result = subprocess.run(
                command,
                input=input_text,
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        if command[0] == "gh":
            token = result.stdout.strip()
        else:
            credentials = dict(
                line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
            )
            token = credentials.get("password", "").strip()
        if token:
            return token
    return None


def targets_main(ruleset: dict[str, object]) -> bool:
    conditions = ruleset.get("conditions")
    if not isinstance(conditions, dict):
        return True
    ref_name = conditions.get("ref_name")
    if not isinstance(ref_name, dict):
        return True
    includes = ref_name.get("include", [])
    return not includes or any(value in {"~DEFAULT_BRANCH", "refs/heads/main", "main"} for value in includes)


def protection(details: dict[str, object]) -> dict[str, object]:
    rules = details.get("rules", [])
    by_type = {rule.get("type"): rule for rule in rules if isinstance(rule, dict)} if isinstance(rules, list) else {}
    pull_request = by_type.get("pull_request", {})
    pr_params = pull_request.get("parameters", {}) if isinstance(pull_request, dict) else {}
    status_checks_rule = by_type.get("required_status_checks", {})
    status_params = status_checks_rule.get("parameters", {}) if isinstance(status_checks_rule, dict) else {}
    checks = status_params.get("required_status_checks", []) if isinstance(status_params, dict) else []
    contexts = [check if isinstance(check, str) else check.get("context") for check in checks if isinstance(check, (str, dict))]
    contexts = sorted(context for context in contexts if isinstance(context, str))
    bypass_actors = details.get("bypass_actors") or []
    return {
        "deletion_protected": "deletion" in by_type,
        "non_fast_forward_protected": "non_fast_forward" in by_type,
        "pull_request_required": "pull_request" in by_type,
        "required_approving_review_count": int(pr_params.get("required_approving_review_count", 0)) if isinstance(pr_params, dict) else 0,
        "required_status_checks": contexts,
        "independent_review_gate_configured": "independent-review-gate" in contexts,
        "bypass_actors": bypass_actors,
        "executor_bypass_prohibited": not bool(bypass_actors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "review" / "LIVE_GITHUB_STATE.json")
    parser.add_argument("--repo", default="bqthai2310/HYAI")
    parser.add_argument("--pr-number", type=int, default=1)
    parser.add_argument("--head-sha")
    args = parser.parse_args(argv)
    document: dict[str, object] = {
        "schema_version": "2.0.0",
        "collected_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "repository": args.repo,
        "pr_number": args.pr_number,
        "head_commit_sha": args.head_sha or "",
        "base_ref": "main",
        "state": "UNKNOWN",
        "api_status": "OFFLINE",
        "rulesets": [],
        "check_runs": [],
    }
    try:
        token = get_auth_token()
        pr = github_get(f"https://api.github.com/repos/{args.repo}/pulls/{args.pr_number}", token)
        if not isinstance(pr, dict):
            raise ValueError("pull request response was not an object")
        head, base = pr.get("head", {}), pr.get("base", {})
        actual_head_sha = args.head_sha or (head.get("sha", "") if isinstance(head, dict) else "")
        document.update({
            "head_commit_sha": actual_head_sha,
            "base_ref": base.get("ref", "main") if isinstance(base, dict) else "main",
            "state": pr.get("state", "UNKNOWN"),
        })
        listing = github_get(f"https://api.github.com/repos/{args.repo}/rulesets", token)
        if not isinstance(listing, list):
            raise ValueError("rulesets response was not a list")
        selected = []
        for item in listing:
            if not isinstance(item, dict) or item.get("enforcement") != "active" or not targets_main(item) or not isinstance(item.get("id"), int):
                continue
            details = github_get(f"https://api.github.com/repos/{args.repo}/rulesets/{item['id']}", token)
            if isinstance(details, dict) and targets_main(details):
                selected.append({"id": item["id"], "name": details.get("name", item.get("name", "")), **protection(details)})
        document["rulesets"] = selected

        if actual_head_sha:
            try:
                check_runs_resp = github_get(f"https://api.github.com/repos/{args.repo}/commits/{actual_head_sha}/check-runs", token)
                if isinstance(check_runs_resp, dict) and isinstance(check_runs_resp.get("check_runs"), list):
                    document["check_runs"] = [
                        {
                            "name": cr.get("name"),
                            "head_sha": cr.get("head_sha"),
                            "status": cr.get("status"),
                            "conclusion": cr.get("conclusion"),
                        }
                        for cr in check_runs_resp["check_runs"]
                        if isinstance(cr, dict)
                    ]
            except Exception:
                pass

        document["api_status"] = "SUCCESS"
    except (HTTPError, URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        document["error"] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"GITHUB_LIVE_STATE={document['api_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
