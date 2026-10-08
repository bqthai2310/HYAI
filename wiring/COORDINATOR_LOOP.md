# Hermes Coordinator Loop Specification (Model A — External Wiring)

## 1. Principles & Separation of Roles

In the TAIOP/HYAI multi-agent operating model:
- **HYAI (The Sovereign Brain):** Owns sovereign intent, constitutional authority, strategic planning, and delivery sealing.
- **Hermes Agent (The Coordinator / Verifier):** Owns operational coordination, task decomposition, subagent delegation, quality gate enforcement, and result verification. **Hermes strictly does not write or modify code directly** when acting as coordinator.
- **Codex CLI (The Coder Agent):** An autonomous execution tool invoked via CLI (`codex exec`) that reads repository state, creates/edits source files, and writes test suites.

```
       [ HYAI Brain ]
             │  (TaskBundle JSON)
             ▼
    ┌─────────────────┐
    │  Hermes Agent   │◄──────────────┐
    │  (Coordinator)  │               │
    └────────┬────────┘               │
             │ (Decompose & Delegate) │ (Verify code changes)
             ▼                        │
    ┌─────────────────┐               │
    │    Codex CLI    │───────────────┘
    │     (Coder)     │
    └─────────────────┘
```

---

## 2. The 5-Stage Coordinator Loop

The coordinator loop executes across 5 sequential, deterministic stages:

### Stage 1: Ingress & Bundle Validation
1. **Receive `TaskBundle`:** Ingest JSON payload from HYAI.
2. **Schema Validation:** Validate against `wiring/schemas/task_bundle.schema.json`. If schema validation fails, immediately reject with `REJECTED_INVALID_BUNDLE`.
3. **Constraint Enforcement:** Check workspace boundaries, budget ceilings, and execution timeout parameters.

### Stage 2: Operational Decomposition
1. **Analyze Plan Steps & Acceptance Criteria:** Map each criterion $C_i$ to its corresponding implementation requirement.
2. **Author Bounded Coder Prompt:** Construct an explicit, unambiguous engineering specification for Codex CLI including:
   - Objective & Target File Paths.
   - Exact functional requirements & error handling behaviors.
   - Unit test requirements (minimum test cases, test framework).
   - Workspace boundary constraints (no modifications outside designated subpaths).
3. **Log Decomposition Artifact:** Record decomposition in `decomposition_log.json` for full audit traceability.

### Stage 3: Delegation to Codex CLI
1. **Command Invocation:** Execute non-interactive Codex CLI via subprocess with pseudo-terminal:
   ```bash
   codex exec --sandbox danger-full-access "<Detailed Coding Instructions>"
   ```
2. **Session Monitoring:** Capture stdout/stderr streams, exit code, and token usage into `codex_session_output.txt`.
3. **Change Detection:** Inspect git status and filesystem diffs to verify which files were created/modified by Codex.

### Stage 4: Independent Verification Gate
1. **Syntax & Compilation Check:** Execute `python -m py_compile <files>` to ensure zero syntax errors.
2. **Automated Test Execution:** Run the test suite using `pytest` without mock shortcuts:
   ```bash
   pytest <test_file> -v
   ```
3. **Lossless Criteria Verification:** For every `criterion_id` in `task_bundle.acceptance_criteria`:
   - Inspect specific assertion / test outcome.
   - Record `status`: `PASS` or `FAIL`.
   - Record `verification_output`: test runner stdout, execution timing, and evidence excerpt.
4. **Remediation Loop (if needed):**
   - If any criterion fails, Hermes does NOT fix the code.
   - Hermes feeds the error traceback and failing criterion back to Codex CLI for a targeted repair attempt (bounded to max 3 rounds).
   - If still failing, evaluate bundle status as `FAILED_VERIFICATION`.

### Stage 5: Assembly & Sealing of Result Bundle
1. **Artifact Hashing:** Compute SHA-256 checksums and file sizes for all generated files.
2. **1-to-1 Lossless Mapping Check:** Ensure `count(verified_criteria) == count(task_bundle.acceptance_criteria)` with zero omitted criteria.
3. **Cryptographic Sealing:**
   - Assemble the `ResultBundle` payload.
   - Compute SHA-256 digest over the canonical JSON representation:
     ```python
     canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
     digest = hashlib.sha256(canonical_bytes).hexdigest()
     ```
   - Stamp `content_digest: { "algorithm": "sha256", "encoding": "hex", "value": digest }`.
4. **Return to HYAI:** Save `result_bundle.json` and transmit back to HYAI.

---

## 3. Operational Guarantees

| Requirement | Guarantee Mechanism |
|---|---|
| **Role Separation** | Hermes orchestrates and verifies; Codex CLI writes code. |
| **Audit Continuity** | Every phase generates an immutable record (`task_bundle.json`, `decomposition_log.json`, `codex_session_output.txt`, `verification_record.json`, `result_bundle.json`). |
| **Lossless Round-Trip** | Strict 1-to-1 bijection between input acceptance criteria and verified criteria in the output bundle. |
| **Fail-Closed Gate** | Any failed test, missing file, or schema error halts the bundle with `FAILED_VERIFICATION`. |
