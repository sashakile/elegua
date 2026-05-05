"""Red-phase tests for automatic provenance fields on tokens and verdicts.

All tests in this file MUST FAIL until elegua.provenance is implemented.
See: elegua-du0, elegua-mmr.
"""

from __future__ import annotations

import datetime

import pytest

pytest.importorskip(
    "elegua.provenance",
    reason="elegua.provenance not yet implemented (elegua-mmr)",
)

from elegua.models import ValidationToken
from elegua.provenance import ProvenanceRecord, attach_provenance
from elegua.task import TaskStatus


def _base_token() -> ValidationToken:
    return ValidationToken(adapter_id="test_adapter", status=TaskStatus.OK, result={"value": 1.0})


def _base_provenance(**overrides) -> ProvenanceRecord:
    defaults = dict(
        fixture_id="fixture-abc",
        fixture_content_hash="deadbeef" * 8,
        adapter_id="test_adapter",
        adapter_version="0.1.0",
        elegua_version="0.3.0",
        timestamp=datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC),
        environment_hash="cafebabe" * 8,
        duration=0.123,
        host="ci-runner-01",
    )
    defaults.update(overrides)
    return ProvenanceRecord(**defaults)


# --- Required fields ---


def test_token_has_fixture_id_after_attach():
    token = attach_provenance(_base_token(), _base_provenance())
    assert token.metadata["provenance"]["fixture_id"] == "fixture-abc"


def test_token_has_fixture_content_hash():
    token = attach_provenance(_base_token(), _base_provenance())
    assert "fixture_content_hash" in token.metadata["provenance"]
    assert isinstance(token.metadata["provenance"]["fixture_content_hash"], str)


def test_token_has_adapter_id():
    token = attach_provenance(_base_token(), _base_provenance())
    assert token.metadata["provenance"]["adapter_id"] == "test_adapter"


def test_token_has_adapter_version():
    token = attach_provenance(_base_token(), _base_provenance(adapter_version="1.2.3"))
    assert token.metadata["provenance"]["adapter_version"] == "1.2.3"


def test_token_has_elegua_version():
    token = attach_provenance(_base_token(), _base_provenance(elegua_version="0.3.0"))
    assert token.metadata["provenance"]["elegua_version"] == "0.3.0"


def test_token_has_timestamp():
    ts = datetime.datetime(2026, 5, 1, 0, 0, 0, tzinfo=datetime.UTC)
    token = attach_provenance(_base_token(), _base_provenance(timestamp=ts))
    assert token.metadata["provenance"]["timestamp"] == ts.isoformat()


def test_token_has_environment_hash():
    token = attach_provenance(_base_token(), _base_provenance())
    assert "environment_hash" in token.metadata["provenance"]


def test_token_has_duration():
    token = attach_provenance(_base_token(), _base_provenance(duration=1.5))
    assert token.metadata["provenance"]["duration"] == pytest.approx(1.5)


def test_token_has_host():
    token = attach_provenance(_base_token(), _base_provenance(host="worker-42"))
    assert token.metadata["provenance"]["host"] == "worker-42"


# --- Optional fields ---


def test_token_git_sha_optional_present():
    token = attach_provenance(_base_token(), _base_provenance(git_sha="abc123def456"))
    assert token.metadata["provenance"]["git_sha"] == "abc123def456"


def test_token_git_sha_optional_absent_is_none():
    token = attach_provenance(_base_token(), _base_provenance(git_sha=None))
    assert token.metadata["provenance"].get("git_sha") is None


def test_token_seed_optional_present():
    token = attach_provenance(_base_token(), _base_provenance(seed=42))
    assert token.metadata["provenance"]["seed"] == 42


def test_token_seed_optional_absent_is_none():
    token = attach_provenance(_base_token(), _base_provenance(seed=None))
    assert token.metadata["provenance"].get("seed") is None


# --- ProvenanceRecord structure ---


def test_provenance_record_required_fields():
    record = _base_provenance()
    assert record.fixture_id == "fixture-abc"
    assert record.adapter_id == "test_adapter"
    assert record.duration > 0


def test_provenance_record_optional_fields_default_none():
    record = _base_provenance()
    assert record.git_sha is None
    assert record.seed is None


def test_provenance_record_invalid_missing_required_raises():
    with pytest.raises((TypeError, ValueError)):
        ProvenanceRecord(fixture_id="x")  # missing many required fields


# --- attach_provenance does not mutate original token ---


def test_attach_provenance_returns_new_token():
    original = _base_token()
    updated = attach_provenance(original, _base_provenance())
    assert original is not updated
    assert "provenance" not in original.metadata


def test_attach_provenance_preserves_existing_metadata():
    token = _base_token().model_copy(update={"metadata": {"custom_key": "custom_value"}})
    updated = attach_provenance(token, _base_provenance())
    assert updated.metadata["custom_key"] == "custom_value"
    assert "provenance" in updated.metadata
