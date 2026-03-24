"""Tests for Layer 2 Property Runner with Hypothesis integration."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import strategies as st

from elegua.errors import SchemaError
from elegua.property import (
    Failure,
    GeneratorRegistry,
    GeneratorSpec,
    PropertyResult,
    PropertyRunner,
    PropertySpec,
    PropertyValidationError,
    StrategyRegistry,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestPropertySpec:
    def test_load_valid_spec(self):
        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        assert spec.name == "negate_involution"
        assert spec.layer == "property"
        assert spec.law == "f(f($x)) == $x"
        assert len(spec.generators) == 1
        assert spec.generators[0].name == "$x"
        assert spec.generators[0].type == "integer"

    def test_missing_law_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.toml"
        bad.write_text('name = "test"\nlayer = "property"\n')
        with pytest.raises(PropertyValidationError, match="law"):
            PropertySpec.from_toml(bad)

    def test_missing_name_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.toml"
        bad.write_text('layer = "property"\nlaw = "x == x"\n')
        with pytest.raises(PropertyValidationError, match="name"):
            PropertySpec.from_toml(bad)

    def test_wrong_layer_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.toml"
        bad.write_text('name = "test"\nlayer = "unit"\nlaw = "x == x"\n')
        with pytest.raises(PropertyValidationError, match="layer"):
            PropertySpec.from_toml(bad)

    def test_missing_layer_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.toml"
        bad.write_text('name = "test"\nlaw = "x == x"\n')
        with pytest.raises(PropertyValidationError, match="layer"):
            PropertySpec.from_toml(bad)

    def test_no_generators_defaults_to_empty(self, tmp_path: Path):
        spec_file = tmp_path / "no_gen.toml"
        spec_file.write_text('name = "trivial"\nlayer = "property"\nlaw = "true"\n')
        spec = PropertySpec.from_toml(spec_file)
        assert spec.generators == []

    def test_params_parsed(self, tmp_path: Path):
        spec_file = tmp_path / "params.toml"
        spec_file.write_text(
            'name = "bounded"\nlayer = "property"\nlaw = "x >= 0"\n'
            "[[generators]]\n"
            'name = "$x"\ntype = "integer"\n'
            "[generators.params]\n"
            "min_value = 0\nmax_value = 100\n"
        )
        spec = PropertySpec.from_toml(spec_file)
        assert spec.generators[0].params == {"min_value": 0, "max_value": 100}

    def test_settings_parsed(self, tmp_path: Path):
        spec_file = tmp_path / "settings.toml"
        spec_file.write_text(
            'name = "configured"\nlayer = "property"\nlaw = "true"\n'
            "[settings]\n"
            "max_examples = 200\ndeadline = 5000\n"
        )
        spec = PropertySpec.from_toml(spec_file)
        assert spec.settings.max_examples == 200
        assert spec.settings.deadline == 5000

    def test_settings_defaults(self):
        spec = PropertySpec(name="t", layer="property", law="true")
        assert spec.settings.max_examples == 100
        assert spec.settings.deadline == 1000


class TestStrategyRegistry:
    def test_register_and_get_strategy(self):
        registry = StrategyRegistry()
        registry.register("integer", st.integers(-1000, 1000))
        strategy = registry.get("integer")
        assert isinstance(strategy, st.SearchStrategy)

    def test_register_callable_factory(self):
        def factory(min_value=0, max_value=100):
            return st.integers(min_value, max_value)

        registry = StrategyRegistry()
        registry.register("integer", factory)
        strategy = registry.get("integer", params={"min_value": -50, "max_value": 50})
        assert isinstance(strategy, st.SearchStrategy)

    def test_unknown_type_raises(self):
        registry = StrategyRegistry()
        with pytest.raises(KeyError, match="unknown_type"):
            registry.get("unknown_type")

    def test_prebuilt_strategy_ignores_params(self):
        registry = StrategyRegistry()
        registry.register("fixed", st.just(42))
        # params silently ignored for pre-built strategies
        strategy = registry.get("fixed")
        assert isinstance(strategy, st.SearchStrategy)

    def test_factory_bad_params_raises_runtime_error(self):
        def factory(min_value=0, max_value=10):
            return st.integers(min_value, max_value)

        registry = StrategyRegistry()
        registry.register("int", factory)
        with pytest.raises(RuntimeError, match=r"Strategy factory.*rejected params"):
            registry.get("int", params={"bad_key": 99})


class TestGeneratorRegistryDeprecated:
    def test_deprecation_warning(self):
        with pytest.warns(DeprecationWarning, match="StrategyRegistry"):
            GeneratorRegistry()

    def test_register_and_run(self):
        with pytest.warns(DeprecationWarning):
            registry = GeneratorRegistry()
        registry.register("integer", lambda: 42)
        runner = PropertyRunner(registry=registry)
        spec = PropertySpec(
            name="compat",
            layer="property",
            law="true",
            generators=[GeneratorSpec(name="$x", type="integer")],
        )
        result = runner.run(spec, evaluator=lambda law, bindings: True, max_examples=5)
        assert result.passed


class TestPropertyRunner:
    def test_passing_property(self):
        registry = StrategyRegistry()
        registry.register("integer", st.integers(-1000, 1000))

        def always_true(law: str, bindings: dict) -> bool:
            return True

        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=always_true, max_examples=10)

        assert isinstance(result, PropertyResult)
        assert result.passed
        assert result.samples_run >= 1
        assert result.failures == []

    def test_failing_property_with_shrinking(self):
        registry = StrategyRegistry()
        registry.register("integer", st.integers(-1000, 1000))

        def fails_on_negative(law: str, bindings: dict) -> bool:
            return bindings["$x"] >= 0

        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=fails_on_negative, max_examples=50)

        assert not result.passed
        assert len(result.failures) == 1
        failure = result.failures[0]
        # Hypothesis should shrink to the simplest negative: -1
        assert failure.shrunk_bindings["$x"] == -1
        # Original failure should be a different (larger) negative
        assert failure.bindings["$x"] < 0
        assert failure.bindings["$x"] <= failure.shrunk_bindings["$x"]

    def test_zero_max_examples(self):
        registry = StrategyRegistry()
        spec = PropertySpec(name="trivial", layer="property", law="true")
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=lambda law, b: True, max_examples=0)
        assert result.passed
        assert result.samples_run == 0

    def test_no_generators_runs_once(self):
        registry = StrategyRegistry()
        spec = PropertySpec(name="trivial", layer="property", law="true")
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=lambda law, b: True)
        assert result.passed
        assert result.samples_run == 1

    def test_no_generators_failure(self):
        registry = StrategyRegistry()
        spec = PropertySpec(name="trivial", layer="property", law="false")
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=lambda law, b: False)
        assert not result.passed
        assert result.samples_run == 1

    def test_strategy_params_passthrough(self):
        """Strategy factory receives params from TOML."""
        registry = StrategyRegistry()
        registry.register(
            "bounded_int",
            lambda min_value=0, max_value=10: st.integers(min_value, max_value),
        )

        spec = PropertySpec(
            name="bounded",
            layer="property",
            law="x >= 5",
            generators=[
                GeneratorSpec(
                    name="$x", type="bounded_int", params={"min_value": 5, "max_value": 100}
                )
            ],
        )
        runner = PropertyRunner(registry=registry)

        def check_ge_5(law: str, bindings: dict) -> bool:
            return bindings["$x"] >= 5

        result = runner.run(spec, evaluator=check_ge_5, max_examples=50)
        assert result.passed

    def test_settings_from_spec(self):
        """max_examples from spec settings is respected."""
        registry = StrategyRegistry()
        registry.register("integer", st.integers(-10, 10))

        spec = PropertySpec(
            name="few",
            layer="property",
            law="true",
            generators=[GeneratorSpec(name="$x", type="integer")],
            settings={"max_examples": 5},
        )
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=lambda law, b: True)
        assert result.passed
        # Hypothesis may run a few more than max_examples due to explicit phase,
        # but should be in the right ballpark
        assert result.samples_run <= 20

    def test_missing_strategy_raises(self):
        registry = StrategyRegistry()
        spec = PropertySpec(
            name="missing",
            layer="property",
            law="true",
            generators=[GeneratorSpec(name="$x", type="nonexistent")],
        )
        runner = PropertyRunner(registry=registry)
        with pytest.raises(RuntimeError, match=r"No strategy.*nonexistent"):
            runner.run(spec, evaluator=lambda law, b: True)

    def test_evaluator_crash_includes_context(self):
        registry = StrategyRegistry()
        registry.register("int", st.integers(0, 100))

        spec = PropertySpec(
            name="test_prop",
            layer="property",
            law="some_law",
            generators=[GeneratorSpec(name="x", type="int")],
        )

        def bad_evaluator(law: str, bindings: dict) -> bool:
            raise TypeError("unsupported operand")

        runner = PropertyRunner(registry=registry)
        with pytest.raises(RuntimeError, match=r"Evaluator failed.*law='some_law'"):
            runner.run(spec, evaluator=bad_evaluator, max_examples=1)

    def test_failure_has_shrunk_bindings(self):
        registry = StrategyRegistry()
        registry.register("integer", st.integers(0, 1000))

        spec = PropertySpec(
            name="shrink_test",
            layer="property",
            law="x < 10",
            generators=[GeneratorSpec(name="$x", type="integer")],
        )
        runner = PropertyRunner(registry=registry)
        result = runner.run(
            spec,
            evaluator=lambda law, b: b["$x"] < 10,
            max_examples=200,
        )
        assert not result.passed
        failure = result.failures[0]
        # Hypothesis should shrink to exactly 10 (smallest failing value)
        assert failure.shrunk_bindings["$x"] == 10
        assert isinstance(failure, Failure)

    def test_existing_involution_fixture_works(self):
        """Backward compat: involution TOML fixture works unchanged."""
        registry = StrategyRegistry()
        registry.register("integer", st.integers(-1000, 1000))

        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=lambda law, b: True, max_examples=10)
        assert result.passed

    def test_example_database_persists(self, tmp_path: Path):
        """Example database stores failures for replay."""
        registry = StrategyRegistry()
        registry.register("integer", st.integers(0, 1000))

        db_dir = str(tmp_path / "hyp_db")
        spec = PropertySpec(
            name="db_test",
            layer="property",
            law="x < 10",
            generators=[GeneratorSpec(name="$x", type="integer")],
            settings={"database_path": db_dir},
        )
        runner = PropertyRunner(registry=registry)

        # First run — find and store failure
        r1 = runner.run(spec, evaluator=lambda law, b: b["$x"] < 10, max_examples=200)
        assert not r1.passed

        # Database directory should have been created
        assert Path(db_dir).exists()

    def test_original_vs_shrunk_bindings_differ(self):
        """bindings holds the original failure, shrunk_bindings the minimal one."""
        registry = StrategyRegistry()
        # Use a wide range so the original failure is likely far from the boundary
        registry.register("integer", st.integers(0, 10000))

        spec = PropertySpec(
            name="wide_shrink",
            layer="property",
            law="x < 100",
            generators=[GeneratorSpec(name="$x", type="integer")],
        )
        runner = PropertyRunner(registry=registry)
        result = runner.run(
            spec,
            evaluator=lambda law, b: b["$x"] < 100,
            max_examples=200,
        )
        assert not result.passed
        failure = result.failures[0]
        # Shrunk should be exactly 100 (boundary)
        assert failure.shrunk_bindings["$x"] == 100
        # Original should be >= 100 (the first random failure found)
        assert failure.bindings["$x"] >= 100


def test_from_toml_malformed(tmp_path):
    f = tmp_path / "bad.toml"
    f.write_text("this is not valid [[[ toml")
    with pytest.raises(SchemaError, match="invalid TOML"):
        PropertySpec.from_toml(f)
