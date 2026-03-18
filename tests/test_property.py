"""Tests for Layer 2 Property Runner with seed-based reproducibility."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.property import (
    PropertySpec,
    PropertyRunner,
    PropertyResult,
    PropertyValidationError,
    GeneratorRegistry,
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
