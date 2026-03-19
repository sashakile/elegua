"""Tests for Layer 2 Property Runner with seed-based reproducibility."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.errors import SchemaError
from elegua.property import (
    GeneratorRegistry,
    GeneratorSpec,
    PropertyResult,
    PropertyRunner,
    PropertySpec,
    PropertyValidationError,
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


class TestGeneratorRegistry:
    def test_register_and_generate(self):
        registry = GeneratorRegistry()
        registry.register("integer", lambda rng: rng.integers(-1000, 1000))
        gen = registry.get("integer")
        assert gen is not None

    def test_unknown_generator_raises(self):
        registry = GeneratorRegistry()
        with pytest.raises(KeyError, match="unknown_type"):
            registry.get("unknown_type")


class TestPropertyRunner:
    def test_reproducible_with_seed(self):
        """Same seed produces identical sample sequences."""
        registry = GeneratorRegistry()
        registry.register("integer", lambda rng: int(rng.integers(-1000, 1000)))

        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        runner = PropertyRunner(registry=registry)

        samples_a = runner.generate_samples(spec, seed=42, count=10)
        samples_b = runner.generate_samples(spec, seed=42, count=10)
        assert samples_a == samples_b

    def test_different_seeds_differ(self):
        registry = GeneratorRegistry()
        registry.register("integer", lambda rng: int(rng.integers(-1000, 1000)))

        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        runner = PropertyRunner(registry=registry)

        samples_a = runner.generate_samples(spec, seed=42, count=10)
        samples_b = runner.generate_samples(spec, seed=99, count=10)
        assert samples_a != samples_b

    def test_zero_samples_returns_empty(self):
        registry = GeneratorRegistry()
        registry.register("integer", lambda rng: int(rng.integers(-1000, 1000)))

        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        runner = PropertyRunner(registry=registry)

        samples = runner.generate_samples(spec, seed=1, count=0)
        assert samples == []

    def test_run_property_single_adapter(self):
        """Self-validation: adapter satisfies the law internally."""
        registry = GeneratorRegistry()
        registry.register("integer", lambda rng: int(rng.integers(-1000, 1000)))

        def negate_evaluator(law: str, bindings: dict) -> bool:
            """Stub: negate is an involution (f(f(x)) == x)."""
            return True

        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=negate_evaluator, seed=42, samples=10)

        assert isinstance(result, PropertyResult)
        assert result.passed
        assert result.samples_run == 10
        assert result.failures == []

    def test_run_property_detects_failure(self):
        """Evaluator that fails on negative inputs."""
        registry = GeneratorRegistry()
        registry.register("integer", lambda rng: int(rng.integers(-1000, 1000)))

        def broken_evaluator(law: str, bindings: dict) -> bool:
            return bindings["$x"] >= 0  # fails for negatives

        spec = PropertySpec.from_toml(FIXTURES / "involution.toml")
        runner = PropertyRunner(registry=registry)
        result = runner.run(spec, evaluator=broken_evaluator, seed=42, samples=50)

        assert not result.passed
        assert len(result.failures) > 0
        assert result.failures[0].bindings["$x"] < 0


def test_generator_crash_includes_context():
    """Generator exception should include generator name, type, and sample index."""
    registry = GeneratorRegistry()
    registry.register("crasher", lambda rng: 1 / 0)

    spec = PropertySpec(
        name="test_prop",
        layer="property",
        law="True",
        generators=[GeneratorSpec(name="x", type="crasher")],
    )
    runner = PropertyRunner(registry)
    with pytest.raises(RuntimeError, match=r"Generator 'x'.*type='crasher'.*sample 0"):
        runner.generate_samples(spec, seed=0, count=1)


def test_evaluator_crash_includes_context():
    """Evaluator exception should include sample index, law, and bindings."""
    registry = GeneratorRegistry()
    registry.register("int", lambda rng: rng.integers(0, 100))

    spec = PropertySpec(
        name="test_prop",
        layer="property",
        law="some_law",
        generators=[GeneratorSpec(name="x", type="int")],
    )

    def bad_evaluator(law, bindings):
        raise TypeError("unsupported operand")

    runner = PropertyRunner(registry)
    with pytest.raises(RuntimeError, match=r"Evaluator failed.*sample 0.*law='some_law'"):
        runner.run(spec, evaluator=bad_evaluator, seed=42, samples=1)


def test_from_toml_malformed(tmp_path):
    f = tmp_path / "bad.toml"
    f.write_text("this is not valid [[[ toml")
    with pytest.raises(SchemaError, match="invalid TOML"):
        PropertySpec.from_toml(f)
