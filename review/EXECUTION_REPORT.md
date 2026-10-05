# F00 Execution Report

## Outcome

F00 completed successfully. All 29 acceptance criteria passed.

## Review subject

- Subject: `subject_f00_governance_bootstrap`
- Repository: `https://github.com/bqthai2310/HYAI`
- Base commit: `a7fa5f3e5429660adb87f5b548fa95eaf0406fd4`
- Head commit: `a7fa5f3e5429660adb87f5b548fa95eaf0406fd4`
- Reviewed files: 229

## Commands executed

- `pytest tests/` — exit code 0
- `python scripts/root_guard.py` — root layout verified
- `python scripts/bootstrap.py` — bootstrap verified
- `python scripts/validate_spec.py` — schemas verified

## Evidence and conformance

- `TEST_OUTPUT.txt` contains the complete pytest stdout and stderr stream.
- `ROOT_GUARD_RESULT.json` records the frozen before digest and the current root-layout digest.
- Acceptance, subject, evidence, and request artifacts conform to their frozen JSON schemas.
- Evidence digests are SHA-256 hex digests of their stored files; bundle and subject digests use canonical JSON serialization.
