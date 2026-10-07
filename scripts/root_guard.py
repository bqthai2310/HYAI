#!/usr/bin/env python3
"""Verify that the HYAI repository root matches its protected layout manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

MANIFEST_NAME = "ROOT_LAYOUT_MANIFEST.json"
FROZEN_CANONICAL_MANIFEST_SHA256 = "b4402df1bb54a6e3b52b0c731e8ec11c454e157d53ff4ce9cf7cb7eac50ba081"
IGNORED_ROOT_ENTRIES = frozenset({".git"})
_SNAPSHOT_MANIFEST_DIGESTS: dict[str, str] = {}


def _digest(value: str) -> dict[str, str]:
    return {"algorithm": "sha256", "encoding": "hex", "value": hashlib.sha256(value.encode("utf-8")).hexdigest()}


def _root(root: str | Path | None = None) -> Path:
    return Path.cwd() if root is None else Path(root)


def _read_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing protected manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("executor_may_modify_manifest") is not False:
        raise ValueError("manifest must forbid executor modification")
    return manifest


def _manifest_sha256(root: Path) -> str:
    return hashlib.sha256((root / MANIFEST_NAME).read_bytes()).hexdigest()


def take_snapshot(root: str | Path | None = None) -> dict[str, Any]:
    """Return sorted root entries and their SHA-256 layout digest."""
    repository_root = _root(root)
    _read_manifest(repository_root)
    entries = sorted(entry.name for entry in repository_root.iterdir() if entry.name not in IGNORED_ROOT_ENTRIES)
    digest = _digest("\n".join(entries))
    manifest_sha256 = _manifest_sha256(repository_root)
    _SNAPSHOT_MANIFEST_DIGESTS[digest["value"]] = manifest_sha256
    return {"entries": entries, "digest": digest, "manifest_sha256": manifest_sha256}


def _before_state(before_digest: Mapping[str, Any] | str) -> tuple[dict[str, str], str | None]:
    if isinstance(before_digest, str):
        return _digest(before_digest) if len(before_digest) != 64 else {"algorithm": "sha256", "encoding": "hex", "value": before_digest}, _SNAPSHOT_MANIFEST_DIGESTS.get(before_digest)
    if "digest" in before_digest:
        digest, manifest_sha256 = dict(before_digest["digest"]), before_digest.get("manifest_sha256")
    else:
        digest, manifest_sha256 = dict(before_digest), _SNAPSHOT_MANIFEST_DIGESTS.get(str(before_digest.get("value", "")))
    return digest, manifest_sha256 if isinstance(manifest_sha256, str) else None


def verify_root(before_digest: Mapping[str, Any] | str, task_ref: str, root: str | Path | None = None) -> dict[str, Any]:
    """Verify root layout and return a document matching RootGuardResult."""
    repository_root = _root(root)
    before, expected_manifest_sha256 = _before_state(before_digest)
    unauthorized: list[str] = []
    try:
        manifest = _read_manifest(repository_root)
        allowed = set(manifest["allowed_root_directories"]) | set(manifest["allowed_root_files"])
        entries = {entry.name for entry in repository_root.iterdir()} - IGNORED_ROOT_ENTRIES
        unauthorized.extend(sorted(entries - allowed))
        unauthorized.extend(f"MISSING_DECLARED_ENTRY:{name}" for name in sorted(allowed - entries))
        if _manifest_sha256(repository_root) != FROZEN_CANONICAL_MANIFEST_SHA256:
            unauthorized.append(f"CANONICAL_MANIFEST_DIGEST_MISMATCH:{MANIFEST_NAME}")
        if expected_manifest_sha256 is not None and _manifest_sha256(repository_root) != expected_manifest_sha256:
            unauthorized.append(f"PROTECTED_MANIFEST_MODIFIED:{MANIFEST_NAME}")
    except (FileNotFoundError, ValueError, json.JSONDecodeError, KeyError) as error:
        unauthorized.append(f"MANIFEST_ERROR:{error}")

    after_snapshot = take_snapshot(repository_root) if not any(item.startswith("MANIFEST_ERROR:") for item in unauthorized) else None
    return {
        "schema_version": "2.0.0",
        "guard_result_id": f"rootguard_{uuid4().hex}",
        "task_ref": task_ref,
        "before_digest": before,
        "after_digest": after_snapshot["digest"] if after_snapshot else _digest(""),
        "unauthorized_entries": unauthorized,
        "result": "FAIL_QUARANTINED" if unauthorized else "PASS",
        "issued_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: cwd)")
    parser.add_argument("--task-ref", default="root-layout-gate", help="identifier for this verification")
    parser.add_argument("--json", action="store_true", help="emit the RootGuardResult JSON document")
    parser.add_argument("--output-json", type=Path, help="write the raw RootGuardResult JSON document to this path")
    args = parser.parse_args(argv)
    try:
        snapshot = take_snapshot(args.root)
        result = verify_root(snapshot, args.task_ref, args.root)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"ROOT_GUARD=FAIL_QUARANTINED error={error}")
        return 1
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"ROOT_GUARD={result['result']}")
        for entry in result["unauthorized_entries"]:
            print(f"UNAUTHORIZED_ROOT_ENTRY={entry}")
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
