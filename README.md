# HYAI — Autonomous Digital Company OS

HYAI converts authorized natural-language directives into governed product delivery through typed contracts, durable execution, evidence, and independent assurance.

This is the v2.1 implementation workspace. [ROOT_LAYOUT_MANIFEST.json](ROOT_LAYOUT_MANIFEST.json) protects the root layout; generated products belong in managed product workspaces or external repositories, never at the repository root.

## Development

Use Python 3.11+ and run:

```shell
python scripts/bootstrap.py
python scripts/validate_spec.py
python scripts/root_guard.py
pytest
```

The stable core holds governance, identity, contracts, evidence, and approval semantics. Providers, tools, runtimes, and infrastructure evolve behind versioned ports.
