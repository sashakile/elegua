"""SympyAdapter — in-process CAS adapter using SymPy.

Maps EleguaTask actions to SymPy function calls with configurable
timeout and expression parsing.
"""

from __future__ import annotations

import math
import pickle
from collections.abc import Callable
from typing import Any

import sympy

from elegua.adapter import Adapter
from elegua.models import ValidationToken
from elegua.sympy.parsing import parse_expression
from elegua.task import EleguaTask, TaskStatus

ActionHandler = Callable[[sympy.Expr, dict[str, Any]], sympy.Expr]


def _timeout_worker(
    action_name: str,
    expr_bytes: bytes,
    payload: dict[str, Any],
    result_queue: Any,
) -> None:
    """Execute CAS action in a subprocess. Module-level for picklability.

    Receives a serialized expression, looks up the action, executes it,
    and puts the result (or exception) on the queue.
    This function must be at module level to be pickled by multiprocessing.
    """
    try:
        expr = pickle.loads(expr_bytes)
        handler = _ACTIONS[action_name]
        result = handler(expr, payload)
        result_queue.put(result)
    except Exception as exc:
        result_queue.put(exc)


def _var(payload: dict[str, Any]) -> sympy.Symbol:
    """Extract the integration/differentiation variable from payload."""
    return sympy.Symbol(payload["variable"])


def _point(payload: dict[str, Any]) -> sympy.Expr:
    """Extract the limit point from payload."""
    return parse_expression(str(payload["point"]))


_ACTIONS: dict[str, ActionHandler] = {
    "Integrate": lambda expr, p: sympy.integrate(expr, _var(p)),
    "Differentiate": lambda expr, p: sympy.diff(expr, _var(p)),
    "Simplify": lambda expr, p: sympy.simplify(expr),
    "Solve": lambda expr, p: sympy.solve(expr, _var(p)),
    "Series": lambda expr, p: sympy.series(expr, _var(p), n=p.get("n", 6)),
    "Limit": lambda expr, p: sympy.limit(expr, _var(p), _point(p)),
}


class SympyAdapter(Adapter):
    """In-process CAS adapter using SymPy.

    Parameters:
        timeout: Per-operation timeout in seconds.
        parse_mode: Expression parsing mode ('auto', 'mathematica', 'python').
    """

    def __init__(
        self,
        timeout: float = 30.0,
        parse_mode: str = "auto",
        sample_points: list[dict[str, float]] | None = None,
    ) -> None:
        self._timeout = timeout
        self._parse_mode = parse_mode
        self._sample_points = sample_points

    @property
    def adapter_id(self) -> str:
        return "sympy"

    def execute(self, task: EleguaTask) -> ValidationToken:
        handler = _ACTIONS.get(task.action)
        if handler is None:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.EXECUTION_ERROR,
                metadata={"error": f"Unknown action: {task.action}"},
            )

        try:
            expr = parse_expression(
                str(task.payload.get("expression", task.action)),
                parse_mode=self._parse_mode,  # type: ignore[arg-type]
            )
        except (ValueError, KeyError) as exc:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.EXECUTION_ERROR,
                metadata={"error": f"Parse error: {exc}"},
            )

        try:
            result_expr = self._run_with_timeout(task.action, expr, task.payload)
        except TimeoutError:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.TIMEOUT,
                metadata={"error": f"Timeout after {self._timeout}s"},
            )
        except (KeyError, ValueError, TypeError) as exc:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.EXECUTION_ERROR,
                metadata={"error": str(exc)},
            )

        metadata: dict[str, Any] = {}
        if isinstance(result_expr, sympy.Basic) and result_expr.has(sympy.Integral):
            metadata["unevaluated"] = True

        result_dict: dict[str, Any] = {
            "repr": str(result_expr),
            "type": type(result_expr).__name__,
            "properties": {},
        }

        if self._sample_points and isinstance(result_expr, sympy.Basic):
            result_dict["numeric_samples"] = self._generate_samples(result_expr)

        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result=result_dict,
            metadata=metadata,
        )

    def _generate_samples(
        self,
        result_expr: sympy.Basic,
    ) -> list[dict[str, Any]]:
        """Evaluate result_expr at sample_points via lambdify."""
        variables = sorted(result_expr.free_symbols, key=lambda s: str(s))
        if not variables:
            return []
        fn = sympy.lambdify(variables, result_expr, modules="numpy")
        samples: list[dict[str, Any]] = []
        for point in self._sample_points:  # type: ignore[union-attr]
            try:
                args = [point[str(v)] for v in variables]
                val = complex(fn(*args))
                if val.imag != 0:
                    continue
                fval = float(val.real)
                if not math.isfinite(fval):
                    samples.append({"vars": point, "value": None, "non_finite": True})
                else:
                    samples.append({"vars": point, "value": fval})
            except Exception:
                pass
        return samples

    def _run_with_timeout(
        self,
        action_name: str,
        expr: sympy.Expr,
        payload: dict[str, Any],
    ) -> sympy.Expr:
        """Run handler with timeout using a subprocess.

        Uses ``multiprocessing.Process`` so the runaway computation can be
        terminated (killed) on timeout, preventing leaked threads.
        """
        import multiprocessing as mp

        expr_bytes = pickle.dumps(expr)
        result_queue = mp.Queue()

        proc = mp.Process(
            target=_timeout_worker,
            args=(action_name, expr_bytes, payload, result_queue),
        )
        proc.start()
        proc.join(timeout=self._timeout)

        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=2.0)
            if proc.is_alive():
                proc.kill()
                proc.join()
            raise TimeoutError

        result = result_queue.get_nowait()
        if isinstance(result, Exception):
            raise result
        return result
