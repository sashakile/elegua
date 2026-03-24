"""Layer 2 Property Runner — Hypothesis-backed property-based testing.

Loads TOML property specs, maps generator types to Hypothesis strategies,
and validates laws with full shrinking, example database, and composable
strategy support.

PCG64 cross-platform sampling is NOT used here — it lives in
compare_numeric.py for L4 cross-CAS numeric comparison.
"""

from __future__ import annotations

import tomllib
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st
from hypothesis.database import DirectoryBasedExampleDatabase
from pydantic import BaseModel

from elegua.errors import SchemaError


class PropertyValidationError(SchemaError):
    """Raised when a property TOML spec is invalid."""


class GeneratorSpec(BaseModel):
    name: str
    type: str
    params: dict[str, Any] = {}


class PropertySettings(BaseModel):
    max_examples: int = 100
    deadline: int | None = 1000  # ms, None to disable
    database_path: str | None = None


class PropertySpec(BaseModel):
    name: str
    layer: str
    law: str
    generators: list[GeneratorSpec] = []
    setup: list[dict[str, Any]] = []
    settings: PropertySettings = PropertySettings()

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

        spec_settings = PropertySettings(**(data.get("settings", {})))

        return cls(
            name=data["name"],
            layer=data["layer"],
            law=data["law"],
            generators=[GeneratorSpec(**g) for g in data.get("generators", [])],
            setup=[s if isinstance(s, dict) else {"action": s} for s in data.get("setup", [])],
            settings=spec_settings,
        )


class StrategyRegistry:
    """Registry mapping type names to Hypothesis strategies.

    Entries can be:
    - A ``SearchStrategy`` instance (used directly, params ignored)
    - A callable ``(params) -> SearchStrategy`` (called with params from TOML)
    """

    # Strategy entry: either a pre-built strategy or a callable factory
    _StrategyEntry = st.SearchStrategy[Any] | Callable[..., st.SearchStrategy[Any]]

    def __init__(self) -> None:
        self._strategies: dict[str, StrategyRegistry._StrategyEntry] = {}

    def register(
        self,
        type_name: str,
        strategy: st.SearchStrategy[Any] | Callable[..., st.SearchStrategy[Any]],
    ) -> None:
        self._strategies[type_name] = strategy

    def get(
        self,
        type_name: str,
        params: dict[str, Any] | None = None,
    ) -> st.SearchStrategy[Any]:
        if type_name not in self._strategies:
            raise KeyError(f"No strategy registered for type '{type_name}'")
        entry = self._strategies[type_name]
        if isinstance(entry, st.SearchStrategy):
            return entry
        # Callable factory — invoke with params
        try:
            return entry(**(params or {}))
        except TypeError as exc:
            raise RuntimeError(
                f"Strategy factory for type '{type_name}' rejected params {params!r}: {exc}"
            ) from exc


class GeneratorRegistry:
    """Deprecated: use StrategyRegistry instead.

    Wraps legacy ``Callable[[Generator], Any]`` callables into Hypothesis
    strategies for backward compatibility.
    """

    def __init__(self) -> None:
        warnings.warn(
            "GeneratorRegistry is deprecated, use StrategyRegistry instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self._registry = StrategyRegistry()

    def register(self, type_name: str, fn: Callable[..., Any]) -> None:
        # Wrap the legacy callable into a Hypothesis strategy via builds
        self._registry.register(type_name, st.builds(fn))

    def get(self, type_name: str) -> Callable[..., Any]:
        # Return the strategy (not callable) — for backward compat in tests
        return self._registry.get(type_name)  # type: ignore[return-value]

    @property
    def strategy_registry(self) -> StrategyRegistry:
        """Access the underlying StrategyRegistry."""
        return self._registry


@dataclass(frozen=True)
class Failure:
    sample_index: int
    bindings: dict[str, Any]
    shrunk_bindings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PropertyResult:
    passed: bool
    samples_run: int
    failures: list[Failure] = field(default_factory=list)


# Type alias for evaluator functions
Evaluator = Callable[[str, dict[str, Any]], bool]


_UNSET: Any = object()


class PropertyRunner:
    """Hypothesis-backed property runner.

    Translates TOML property specs into ``@given``-decorated test functions
    with full shrinking, example database, and health check support.
    """

    def __init__(self, registry: StrategyRegistry | GeneratorRegistry) -> None:
        if isinstance(registry, GeneratorRegistry):
            self._registry = registry.strategy_registry
        else:
            self._registry = registry

    def run(
        self,
        spec: PropertySpec,
        evaluator: Evaluator,
        max_examples: int | None = None,
        deadline: int | None | Any = _UNSET,
    ) -> PropertyResult:
        """Run the property check via Hypothesis.

        Parameters:
            spec: The property specification.
            evaluator: Callable ``(law, bindings) -> bool``.
            max_examples: Override max examples (default: from spec settings).
            deadline: Override deadline in ms (default: from spec settings).
                Pass None to disable deadline.
        """
        effective_max = max_examples if max_examples is not None else spec.settings.max_examples
        effective_deadline = deadline if deadline is not _UNSET else spec.settings.deadline

        if effective_max == 0:
            return PropertyResult(passed=True, samples_run=0)

        # Build strategies for each generator
        strategies: dict[str, st.SearchStrategy[Any]] = {}
        for gen in spec.generators:
            try:
                strategies[gen.name] = self._registry.get(
                    gen.type, gen.params if gen.params else None
                )
            except KeyError:
                raise RuntimeError(
                    f"No strategy registered for generator '{gen.name}' (type={gen.type!r})"
                ) from None

        # Configure Hypothesis example database
        db_path = spec.settings.database_path
        defaults = settings.default
        default_db = defaults.database if defaults is not None else None
        database = DirectoryBasedExampleDatabase(db_path) if db_path else default_db

        # Configure Hypothesis settings
        hyp_settings = settings(
            max_examples=effective_max,
            deadline=effective_deadline,
            database=database,
            suppress_health_check=[HealthCheck.too_slow],
            phases=[Phase.explicit, Phase.generate, Phase.shrink],
        )

        # Track results via closure
        samples_run = 0
        original_failure: dict[str, Any] | None = None
        shrunk_failure: dict[str, Any] | None = None

        if not strategies:
            # No generators — run evaluator once with empty bindings
            try:
                result = evaluator(spec.law, {})
            except Exception as exc:
                raise RuntimeError(
                    f"Evaluator failed for law={spec.law!r} with bindings={{}}: {exc}"
                ) from exc
            if not result:
                return PropertyResult(
                    passed=False,
                    samples_run=1,
                    failures=[Failure(sample_index=0, bindings={}, shrunk_bindings={})],
                )
            return PropertyResult(passed=True, samples_run=1)

        # Build the @given test function
        @hyp_settings
        @given(**strategies)
        def check(**kwargs: Any) -> None:
            nonlocal samples_run, original_failure, shrunk_failure
            samples_run += 1
            try:
                result = evaluator(spec.law, kwargs)
            except Exception as exc:
                raise RuntimeError(
                    f"Evaluator failed for law={spec.law!r} with bindings={kwargs!r}: {exc}"
                ) from exc
            if not result:
                if original_failure is None:
                    original_failure = dict(kwargs)
                shrunk_failure = dict(kwargs)
                raise AssertionError(f"Property {spec.law!r} falsified with {kwargs}")

        # Execute
        try:
            check()
        except AssertionError:
            # Hypothesis shrunk and re-raised — shrunk_failure has the minimal input
            return PropertyResult(
                passed=False,
                samples_run=samples_run,
                failures=[
                    Failure(
                        sample_index=samples_run - 1,
                        bindings=original_failure or {},
                        shrunk_bindings=shrunk_failure or {},
                    )
                ],
            )

        return PropertyResult(passed=True, samples_run=samples_run)
