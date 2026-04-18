from __future__ import annotations

import json
from pathlib import Path

import pytest

from api import session as session_store
from cases.schema import GeneratedCase

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CASES_FILE = _REPO_ROOT / "test_output.json"


@pytest.fixture(autouse=True)
def clear_session_store() -> None:
    session_store.clear_sessions()
    yield
    session_store.clear_sessions()


@pytest.fixture
def three_cases() -> list[GeneratedCase]:
    if not _CASES_FILE.is_file():
        pytest.skip(f"Missing {_CASES_FILE.name} (generated case bundle).")
    data = json.loads(_CASES_FILE.read_text(encoding="utf-8"))
    raw = data.get("cases", [])
    if len(raw) < 3:
        pytest.skip("Need at least 3 cases in test_output.json for this test.")
    return [GeneratedCase.model_validate(case) for case in raw[:3]]
