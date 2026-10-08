# HYAI-Hermes-Codex Task Bundle Contract (Model A — External Wiring)

## 1. Overview & Context

This contract governs the external operational handoff between:
- **HYAI (The Sovereign Brain):** Owns sovereign intent, natural language goal ingress, high-level planning, constitutional authority, and delivery bundle sealing.
- **Hermes Agent (The Coordinator / Orchestrator):** Receives the structured `TaskBundle`, performs operational decomposition into bounded engineering subtasks, orchestrates execution, delegates coding to Codex CLI, enforces verification gates, and returns a sealed `ResultBundle`.
- **Codex CLI (The Coder):** An isolated, non-interactive coding agent process (`codex exec`) that reads task prompts, inspects the codebase, writes/refactors source files, and implements unit tests.

Under **Model A (Pragmatic External Wiring)**, HYAI and Hermes communicate via strongly typed, schema-validated JSON documents over a filesystem or IPC interface.

---

## 2. Component Architecture & Flow

```
+-------------------------------------------------------------+
|                      HYAI (Brain)                           |
|  - Ingests directive & compiles GoalSpecification          |
|  - Compiles execution plan steps                            |
|  - Emits TaskBundle (JSON) with hard acceptance criteria    |
+------------------------------+------------------------------+
                               |
                               | (1) TaskBundle.json
                               v
+-------------------------------------------------------------+
|                 Hermes Agent (Coordinator)                  |
|  - Validates TaskBundle schema                              |
|  - Decomposes into actionable engineering subtasks          |
|  - Dispatches subtask prompt to Codex CLI                   |
+------------------------------+------------------------------+
                               |
                               | (2) codex exec (subprocess)
                               v
+-------------------------------------------------------------+
|                  Codex CLI (Coder Agent)                    |
|  - Reads instructions, workspace files                      |
|  - Authors code, modules, test suites                       |
|  - Emits changes to disk & reports terminal logs            |
+------------------------------+------------------------------+
                               |
                               | (3) Code changes & session log
                               v
+-------------------------------------------------------------+
|                 Hermes Agent (Verifier)                     |
|  - Runs test suites, syntax checks, schema validations      |
|  - Verifies 100% of acceptance criteria (lossless check)    |
|  - Assembles & seals ResultBundle.json                      |
+------------------------------+------------------------------+
                               |
                               | (4) ResultBundle.json
                               v
+-------------------------------------------------------------+
|                      HYAI (Brain)                           |
|  - Validates ResultBundle against expected format           |
|  - Incorporates results into durable state & delivery bundle|
+-------------------------------------------------------------+
```

---

## 3. Task Bundle Schema (`task_bundle.schema.json`)

A `TaskBundle` is an immutable, machine-readable JSON document produced by HYAI.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "HYAITaskBundle",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "bundle_id",
    "goal_ref",
    "plan_steps",
    "acceptance_criteria",
    "constraints",
    "expected_deliverable_format"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["1.0.0"]
    },
    "bundle_id": {
      "type": "string",
      "pattern": "^taskbundle_[a-f0-9]{8,32}$"
    },
    "goal_ref": {
      "type": "string",
      "pattern": "^goal_[a-f0-9]{8,32}$"
    },
    "plan_steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["step_id", "title", "description", "assigned_role"],
        "properties": {
          "step_id": { "type": "string" },
          "title": { "type": "string" },
          "description": { "type": "string" },
          "assigned_role": { "type": "string", "enum": ["COORDINATOR", "CODER", "VERIFIER"] }
        }
      }
    },
    "acceptance_criteria": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["criterion_id", "description", "verification_type", "target_ref"],
        "properties": {
          "criterion_id": { "type": "string" },
          "description": { "type": "string" },
          "verification_type": { "type": "string", "enum": ["UNIT_TEST", "SYNTAX_CHECK", "SCHEMA_VALIDATION", "FILE_EXISTENCE"] },
          "target_ref": { "type": "string" }
        }
      }
    },
    "constraints": {
      "type": "object",
      "additionalProperties": false,
      "required": ["workspace_root", "sandbox_mode", "network_egress", "max_duration_seconds"],
      "properties": {
        "workspace_root": { "type": "string" },
        "sandbox_mode": { "type": "string", "enum": ["STRICT_SANDBOX", "WORKSPACE_WRITE", "DANGER_FULL_ACCESS"] },
        "network_egress": { "type": "string", "enum": ["BLOCKED", "LOCALHOST_ONLY", "TELEGRAM_ONLY"] },
        "max_duration_seconds": { "type": "integer", "minimum": 1 }
      }
    },
    "expected_deliverable_format": {
      "type": "object",
      "additionalProperties": false,
      "required": ["deliverable_type", "required_files", "result_bundle_schema_ref"],
      "properties": {
        "deliverable_type": { "type": "string" },
        "required_files": {
          "type": "array",
          "items": { "type": "string" }
        },
        "result_bundle_schema_ref": { "type": "string" }
      }
    }
  }
}
```

---

## 4. Result Bundle Schema (`result_bundle.schema.json`)

A `ResultBundle` is an immutable, machine-readable JSON document returned by Hermes to HYAI.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "HYAIResultBundle",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "result_bundle_id",
    "task_bundle_ref",
    "goal_ref",
    "status",
    "verified_criteria",
    "artifacts",
    "execution_metadata",
    "content_digest"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["1.0.0"]
    },
    "result_bundle_id": {
      "type": "string",
      "pattern": "^resultbundle_[a-f0-9]{8,32}$"
    },
    "task_bundle_ref": {
      "type": "string",
      "pattern": "^taskbundle_[a-f0-9]{8,32}$"
    },
    "goal_ref": {
      "type": "string",
      "pattern": "^goal_[a-f0-9]{8,32}$"
    },
    "status": {
      "type": "string",
      "enum": ["COMPLETED_SUCCESS", "FAILED_VERIFICATION", "ABORTED"]
    },
    "verified_criteria": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["criterion_id", "status", "verification_output", "verified_at"],
        "properties": {
          "criterion_id": { "type": "string" },
          "status": { "type": "string", "enum": ["PASS", "FAIL"] },
          "verification_output": { "type": "string" },
          "verified_at": { "type": "string", "format": "date-time" }
        }
      }
    },
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["file_path", "sha256", "size_bytes"],
        "properties": {
          "file_path": { "type": "string" },
          "sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
          "size_bytes": { "type": "integer", "minimum": 0 }
        }
      }
    },
    "execution_metadata": {
      "type": "object",
      "additionalProperties": false,
      "required": ["coordinator", "coder", "duration_seconds", "timestamp_start", "timestamp_end"],
      "properties": {
        "coordinator": { "type": "string" },
        "coder": { "type": "string" },
        "duration_seconds": { "type": "number" },
        "timestamp_start": { "type": "string", "format": "date-time" },
        "timestamp_end": { "type": "string", "format": "date-time" }
      }
    },
    "content_digest": {
      "type": "object",
      "additionalProperties": false,
      "required": ["algorithm", "encoding", "value"],
      "properties": {
        "algorithm": { "type": "string", "enum": ["sha256"] },
        "encoding": { "type": "string", "enum": ["hex"] },
        "value": { "type": "string", "pattern": "^[a-f0-9]{64}$" }
      }
    }
  }
}
```

---

## 5. Lossless Round-Trip Guarantee (W-AC-004)

1. **Criterion Invariance:** Every `criterion_id` present in `task_bundle.acceptance_criteria` MUST appear exactly once in `result_bundle.verified_criteria`.
2. **Fail-Closed Evaluation:** If any criterion evaluates to `status != "PASS"`, the entire `result_bundle.status` MUST evaluate to `FAILED_VERIFICATION`.
3. **Artifact Digest Integrity:** Every artifact declared in `artifacts` must be verified on disk, match the expected path, and be sealed with its exact SHA-256 digest.
4. **Bundle Sealing:** The `content_digest.value` is computed over the deterministic, key-sorted JSON representation of the entire `ResultBundle` payload (excluding the digest field itself).
