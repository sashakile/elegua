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
