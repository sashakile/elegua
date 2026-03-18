"""Tests for ActionPayload and ValidationToken models."""

from __future__ import annotations

import pytest

from elegua.models import ActionPayload, ValidationToken
from elegua.task import TaskStatus


class TestActionPayload:
    def test_minimal(self):
        ap = ActionPayload(action="DefTensor", payload={"name": "T"})
        assert ap.action == "DefTensor"
        assert ap.payload == {"name": "T"}
        assert ap.domain is None
        assert ap.manifest is None

    def test_full(self):
        ap = ActionPayload(
            action="DefTensor",
            domain="tensor_calculus",
            manifest="manifest.toml",
            payload={"expression": {"fn": "Operator", "args": []}},
        )
        assert ap.domain == "tensor_calculus"
        assert ap.manifest == "manifest.toml"

    def test_action_required(self):
        with pytest.raises(Exception):
            ActionPayload(payload={"name": "T"})  # type: ignore[call-arg]


class TestValidationToken:
    def test_ok_token(self):
        token = ValidationToken(
            adapter_id="wolfram",
            status=TaskStatus.OK,
            result={"fn": "Tensor", "args": ["a", "b"]},
        )
        assert token.adapter_id == "wolfram"
        assert token.status == TaskStatus.OK
        assert token.result is not None
        assert token.metadata == {}

    def test_error_token_no_result(self):
        token = ValidationToken(
            adapter_id="wolfram",
            status=TaskStatus.EXECUTION_ERROR,
        )
        assert token.result is None

    def test_metadata(self):
        token = ValidationToken(
            adapter_id="wolfram",
            status=TaskStatus.OK,
            result={"value": 42},
            metadata={"duration_ms": 120},
        )
        assert token.metadata["duration_ms"] == 120

    def test_adapter_id_required(self):
        with pytest.raises(Exception):
            ValidationToken(status=TaskStatus.OK)  # type: ignore[call-arg]
