"""Shared fixture loading and evidence assertions for frozen L9 oracle tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]


def fixture(requirement_id: str, name: str) -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / requirement_id / name).read_text(encoding="utf-8"))


def oracle(requirement_id: str, test_id: str, positive: Callable[[], bool], negative: Callable[[], bool]) -> None:
    """Assert a frozen baseline passes and its adversarial mutation cannot pass."""
    good, bad = fixture(requirement_id, "positive.json"), fixture(requirement_id, "negative_001.json")
    assert (good["requirement_id"], good["test_id"], good["expected_result"]) == (requirement_id, test_id, "PASS")
    assert positive(), f"{requirement_id} {test_id}: positive baseline failed"
    assert (bad["requirement_id"], bad["test_id"], bad["expected_result"], bad["forbidden_result"]) == (requirement_id, test_id, "FAIL", "PASS")
    assert not negative(), f"{requirement_id} {test_id}: negative mutation incorrectly passed"
    assert any(requirement_id in item and test_id in item for item in bad["required_assertions"])
