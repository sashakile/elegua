"""Tests for the domain exception hierarchy."""

from __future__ import annotations

import pytest


class TestExceptionHierarchy:
    """Verify the EleguaError hierarchy and backward compatibility."""

    def test_elegua_error_is_exception(self):
        from elegua.errors import EleguaError

        assert issubclass(EleguaError, Exception)

    def test_schema_error_is_elegua_error(self):
        from elegua.errors import EleguaError, SchemaError

        assert issubclass(SchemaError, EleguaError)

    def test_schema_error_is_value_error(self):
        """SchemaError must also be a ValueError for backward compat."""
        from elegua.errors import SchemaError

        assert issubclass(SchemaError, ValueError)

    def test_adapter_error_is_elegua_error(self):
        from elegua.errors import AdapterError, EleguaError

        assert issubclass(AdapterError, EleguaError)

    def test_oracle_error_is_adapter_error(self):
        from elegua.errors import AdapterError, OracleError

        assert issubclass(OracleError, AdapterError)

    def test_property_validation_error_is_schema_error(self):
        from elegua.errors import SchemaError
        from elegua.property import PropertyValidationError

        assert issubclass(PropertyValidationError, SchemaError)

    def test_property_validation_error_is_elegua_error(self):
        from elegua.errors import EleguaError
        from elegua.property import PropertyValidationError

        assert issubclass(PropertyValidationError, EleguaError)

    def test_property_validation_error_is_value_error(self):
        """PropertyValidationError must still be caught by except ValueError."""
        from elegua.property import PropertyValidationError

        assert issubclass(PropertyValidationError, ValueError)

    def test_invalid_transition_is_elegua_error(self):
        from elegua.errors import EleguaError
        from elegua.task import InvalidTransition

        assert issubclass(InvalidTransition, EleguaError)

    @pytest.mark.parametrize(
        "exc_name",
        ["EleguaError", "SchemaError", "AdapterError", "OracleError"],
    )
    def test_all_instantiable_with_message(self, exc_name):
        import elegua.errors as mod

        cls = getattr(mod, exc_name)
        err = cls("test message")
        assert str(err) == "test message"

    def test_all_importable_from_elegua_errors(self):
        from elegua.errors import AdapterError, EleguaError, OracleError, SchemaError

        assert EleguaError is not None
        assert SchemaError is not None
        assert AdapterError is not None
        assert OracleError is not None

    def test_all_importable_from_elegua_package(self):
        from elegua import AdapterError, EleguaError, OracleError, SchemaError

        assert EleguaError is not None
        assert SchemaError is not None
        assert AdapterError is not None
        assert OracleError is not None


class TestBackwardCompat:
    """Verify that existing except ValueError handlers still catch new exceptions."""

    def test_schema_error_caught_by_except_value_error(self):
        from elegua.errors import SchemaError

        with pytest.raises(ValueError):
            raise SchemaError("backward compat")

    def test_property_validation_error_caught_by_except_value_error(self):
        from elegua.property import PropertyValidationError

        with pytest.raises(ValueError):
            raise PropertyValidationError("backward compat")


class TestExceptionChaining:
    """Verify raise X from Y preserves __cause__ in all except blocks (M4)."""

    def test_bridge_toml_parse_chains_cause(self, tmp_path):
        from elegua.bridge import load_test_file
        from elegua.errors import SchemaError

        bad = tmp_path / "bad.toml"
        bad.write_text("not = [valid toml")
        with pytest.raises(SchemaError) as exc_info:
            load_test_file(bad)
        assert exc_info.value.__cause__ is not None

    def test_runner_toml_parse_chains_cause(self, tmp_path):
        from elegua.errors import SchemaError
        from elegua.runner import load_toml_tasks

        bad = tmp_path / "bad.toml"
        bad.write_text("not = [valid toml")
        with pytest.raises(SchemaError) as exc_info:
            load_toml_tasks(bad)
        assert exc_info.value.__cause__ is not None

    def test_snapshot_json_parse_chains_cause(self, tmp_path):
        from elegua.errors import SchemaError
        from elegua.snapshot import SnapshotStore

        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        with pytest.raises(SchemaError) as exc_info:
            SnapshotStore.read(bad)
        assert exc_info.value.__cause__ is not None

    def test_blobstore_json_parse_chains_cause(self, tmp_path):
        from elegua.blobstore import BlobStore
        from elegua.errors import SchemaError

        store = BlobStore(tmp_path / "blobs")
        # Put valid data first to get a real sha
        ref = store.put({"key": "value"})
        # Corrupt the blob file
        sha = ref["blob"]
        blob_path = tmp_path / "blobs" / sha[:2] / sha[2:]
        blob_path.write_text("{corrupt json")
        with pytest.raises(SchemaError) as exc_info:
            store.get(sha)
        assert exc_info.value.__cause__ is not None

    def test_property_toml_parse_chains_cause(self, tmp_path):
        from elegua.errors import SchemaError
        from elegua.property import PropertySpec

        bad = tmp_path / "bad.toml"
        bad.write_text("not = [valid toml")
        with pytest.raises(SchemaError) as exc_info:
            PropertySpec.from_toml(bad)
        assert exc_info.value.__cause__ is not None

    def test_comparison_layer_exception_chains_cause(self):
        from elegua.comparison import ComparisonPipeline
        from elegua.models import ValidationToken
        from elegua.task import TaskStatus

        def exploding_layer(a, b):
            raise ValueError("kaboom")

        pipeline = ComparisonPipeline(default_layers=False)
        pipeline.register(1, "boom", exploding_layer)

        ta = ValidationToken(adapter_id="a", status=TaskStatus.OK, result={"x": 1})
        tb = ValidationToken(adapter_id="b", status=TaskStatus.OK, result={"x": 2})
        with pytest.raises(RuntimeError) as exc_info:
            pipeline.compare(ta, tb)
        assert exc_info.value.__cause__ is not None

    def test_isolation_setup_reraise_chains_cause(self):
        """IsolatedRunner._run_setup re-raises with from exc."""
        from elegua.adapter import Adapter
        from elegua.bridge import Operation
        from elegua.isolation import IsolatedRunner
        from elegua.models import ValidationToken
        from elegua.task import EleguaTask

        class SetupBoomAdapter(Adapter):
            @property
            def adapter_id(self):
                return "boom"

            def execute(self, task: EleguaTask) -> ValidationToken:
                raise RuntimeError("setup exploded")

        runner = IsolatedRunner(SetupBoomAdapter())
        with runner:
            with pytest.raises(RuntimeError) as exc_info:
                runner._run_setup([Operation(action="Boom")])
            assert exc_info.value.__cause__ is not None
