"""Layer 2 Property Runner — declarative property-based testing with PCG64 seeds.

Loads TOML property specs, generates reproducible samples via PCG64,
and validates laws against an evaluator function.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from numpy.random import PCG64, Generator
from pydantic import BaseModel

from elegua.errors import SchemaError


class PropertyValidationError(SchemaError):
    """Raised when a property TOML spec is invalid."""


class GeneratorSpec(BaseModel):
    name: str
    type: str


class PropertySpec(BaseModel):
    name: str
    layer: str
    law: str
    generators: list[GeneratorSpec] = []
    setup: list[dict[str, Any]] = []

    @classmethod
    def from_toml(cls, path: Path) -> PropertySpec:
        with open(path, "rb") as f:
            try:
                data = tomllib.load(f)
            except tomllib.TOMLDecodeError as exc:
                raise SchemaError(f"{path}: invalid TOML: {exc}") from exc

        for required in ("name", "law"):
            if required not in data:
                raise PropertyValidationError(f"{path}: missing required field '{required}'")

        if data.get("layer") != "property":
            raise PropertyValidationError(
                f"{path}: 'layer' must be 'property', got {data.get('layer')!r}"
            )

        return cls(
            name=data["name"],
            layer=data["layer"],
            law=data["law"],
            generators=[GeneratorSpec(**g) for g in data.get("generators", [])],
            setup=[s if isinstance(s, dict) else {"action": s} for s in data.get("setup", [])],
        )


class GeneratorRegistry:
    """Registry of domain-specific sample generators."""

    def __init__(self) -> None:
        self._generators: dict[str, Callable[[Generator], Any]] = {}

    def register(self, type_name: str, fn: Callable[[Generator], Any]) -> None:
        self._generators[type_name] = fn

    def get(self, type_name: str) -> Callable[[Generator], Any]:
        if type_name not in self._generators:
            raise KeyError(f"No generator registered for type '{type_name}'")
        return self._generators[type_name]


@dataclass(frozen=True)
class Failure:
    sample_index: int
    bindings: dict[str, Any]


@dataclass(frozen=True)
class PropertyResult:
    passed: bool
    samples_run: int
    failures: list[Failure] = field(default_factory=list)


# Type alias for evaluator functions
Evaluator = Callable[[str, dict[str, Any]], bool]


class PropertyRunner:
    def __init__(self, registry: GeneratorRegistry) -> None:
        self._registry = registry

    def generate_samples(
        self,
        spec: PropertySpec,
        seed: int,
        count: int,
    ) -> list[dict[str, Any]]:
        """Generate `count` sample bindings using PCG64 with the given seed."""
        if count == 0:
            return []

        rng = Generator(PCG64(seed))
        samples = []
        for sample_idx in range(count):
            bindings: dict[str, Any] = {}
            for gen in spec.generators:
                fn = self._registry.get(gen.type)
                try:
                    bindings[gen.name] = fn(rng)
                except Exception as exc:
                    raise RuntimeError(
                        f"Generator '{gen.name}' (type={gen.type!r}) "
                        f"failed at sample {sample_idx}: {exc}"
                    ) from exc
            samples.append(bindings)
        return samples

    def run(
        self,
        spec: PropertySpec,
        evaluator: Evaluator,
        seed: int = 0,
        samples: int = 100,
    ) -> PropertyResult:
        """Run the property check and return results."""
        sample_list = self.generate_samples(spec, seed=seed, count=samples)
        failures: list[Failure] = []

        for i, bindings in enumerate(sample_list):
            try:
                result = evaluator(spec.law, bindings)
            except Exception as exc:
                raise RuntimeError(
                    f"Evaluator failed at sample {i} for law={spec.law!r} "
                    f"with bindings={bindings!r}: {exc}"
                ) from exc
            if not result:
                failures.append(Failure(sample_index=i, bindings=bindings))

        return PropertyResult(
            passed=len(failures) == 0,
            samples_run=len(sample_list),
            failures=failures,
        )
