"""OracleAdapter — generic adapter for any oracle HTTP server.

Domain-agnostic: the adapter is a transport layer between EleguaTask
and a compute kernel via HTTP. Domain-specific action translation is
provided by an injectable ``expr_builder`` callable.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Protocol

from elegua.adapter import Adapter
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus


class OracleLike(Protocol):
    """Minimal protocol for oracle dependency injection."""

    def health(self) -> bool: ...
    def health_or_raise(self) -> None: ...
    def evaluate_with_xact(
        self, expr: str, timeout: int = 60, context_id: str | None = None
    ) -> dict[str, Any]: ...
    def cleanup(self) -> bool: ...
    def check_clean_state(self) -> tuple[bool, list[str]]: ...


ResultMapperFn = Callable[[str, dict[str, Any], dict[str, Any]], ValidationToken]


def _default_expr_builder(action: str, payload: dict[str, Any]) -> str:
    """Default builder: use payload['expression'] or the action name as-is."""
    return str(payload.get("expression", action))


class OracleAdapter(Adapter):
    """Generic adapter for any oracle HTTP server.

    The adapter handles lifecycle (health, cleanup), expression evaluation,
    and result mapping. Domain-specific action→expression translation is
    delegated to the ``expr_builder`` callable.

    Parameters:
        oracle: An OracleClient (or any OracleLike) instance.
        expr_builder: Callable(action, payload) → expression string.
            Defaults to using ``payload["expression"]``.
        timeout: Default per-call timeout in seconds.
    """

    def __init__(
        self,
        oracle: OracleLike | None = None,
        base_url: str = "http://localhost:8765",
        timeout: int = 60,
        expr_builder: Callable[[str, dict[str, Any]], str] | None = None,
        adapter_id: str = "wolfram-oracle",
        result_mapper: ResultMapperFn | None = None,
    ) -> None:
        if oracle is None:
            from elegua.oracle import OracleClient

            oracle = OracleClient(base_url)
        self._oracle = oracle
        self._timeout = timeout
        self._expr_builder = expr_builder or _default_expr_builder
        self._context_id: str | None = None
        self._adapter_id = adapter_id
        self._result_mapper = result_mapper

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    def initialize(self) -> None:
        self._oracle.health_or_raise()
        is_clean, leaked = self._oracle.check_clean_state()
        if not is_clean:
            import warnings

            warnings.warn(
                f"Kernel dirty before test (leaked: {leaked})",
                RuntimeWarning,
                stacklevel=2,
            )
        self._context_id = str(uuid.uuid4())

    def teardown(self) -> None:
        if not self._oracle.cleanup():
            import warnings

            warnings.warn("Oracle cleanup failed", RuntimeWarning, stacklevel=2)
        self._context_id = None

    def execute(self, task: EleguaTask) -> ValidationToken:
        if self._context_id is None:
            msg = (
                "execute() called before initialize() "
                "— call initialize() or use the context manager"
            )
            raise RuntimeError(msg)
        try:
            wolfram_expr = self._expr_builder(task.action, task.payload)
        except KeyError as exc:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.EXECUTION_ERROR,
                metadata={"error": f"Missing required argument: {exc}"},
            )
        except ValueError as exc:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.EXECUTION_ERROR,
                metadata={"error": str(exc)},
            )

        data = self._oracle.evaluate_with_xact(
            wolfram_expr,
            timeout=self._timeout,
            context_id=self._context_id,
        )

        if self._result_mapper is not None:
            return self._result_mapper(task.action, task.payload, data)
        return self._map_result(task.action, task.payload, data)

    def _map_result(
        self,
        action: str,
        payload: dict[str, Any],
        data: dict[str, Any],
    ) -> ValidationToken:
        status_raw = data.get("status", "error")
        oracle_result = data.get("result", "")
        error = data.get("error")

        # Boolean assertion: if the action is "Assert" and the oracle returned
        # a non-True value, treat it as a failure. This is Wolfram-generic
        # (not domain-specific) — any Wolfram boolean check uses this pattern.
        if action == "Assert" and status_raw == "ok":
            if str(oracle_result).strip() != "True":
                msg = payload.get("message") or (
                    f"Assertion failed: {payload.get('condition', '')}"
                )
                return ValidationToken(
                    adapter_id=self.adapter_id,
                    status=TaskStatus.EXECUTION_ERROR,
                    result={"repr": str(oracle_result), "type": "Bool"},
                    metadata={"error": msg},
                )
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.OK,
                result={"repr": "True", "type": "Bool"},
            )

        # Map oracle status to TaskStatus
        if status_raw == "timeout":
            task_status = TaskStatus.TIMEOUT
        elif status_raw == "error":
            task_status = TaskStatus.EXECUTION_ERROR
        else:
            task_status = TaskStatus.OK

        result_dict: dict[str, Any] = {
            "repr": str(oracle_result),
            "type": data.get("type", "Expr"),
            "properties": data.get("properties", {}),
        }

        metadata: dict[str, Any] = {}
        if error:
            metadata["error"] = error
        timing = data.get("timing_ms")
        if timing is not None:
            metadata["execution_time_ms"] = timing

        return ValidationToken(
            adapter_id=self.adapter_id,
            status=task_status,
            result=result_dict,
            metadata=metadata,
        )


def WolframOracleAdapter(*args: Any, **kwargs: Any) -> OracleAdapter:
    """Deprecated: use ``OracleAdapter`` instead."""
    import warnings

    warnings.warn(
        "WolframOracleAdapter is deprecated, use OracleAdapter instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return OracleAdapter(*args, **kwargs)
