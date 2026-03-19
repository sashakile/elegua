"""WolframOracleAdapter — real adapter using the oracle HTTP server.

Translates EleguaTask (action + payload) into Wolfram expressions,
sends them to the oracle via HTTP, and maps results back to
ValidationTokens.
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from elegua.adapter import Adapter
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus


class OracleLike(Protocol):
    """Minimal protocol for oracle dependency injection."""

    def health(self) -> bool: ...
    def evaluate_with_xact(
        self, expr: str, timeout: int = 60, context_id: str | None = None
    ) -> dict[str, Any]: ...
    def cleanup(self) -> bool: ...
    def check_clean_state(self) -> tuple[bool, list[str]]: ...


class WolframOracleAdapter(Adapter):
    """Adapter for the Wolfram/xAct backend via oracle HTTP server.

    Parameters:
        oracle: An OracleClient (or any OracleLike) instance.
        timeout: Default per-call timeout in seconds.
    """

    def __init__(
        self,
        oracle: OracleLike | None = None,
        base_url: str = "http://localhost:8765",
        timeout: int = 60,
    ) -> None:
        if oracle is None:
            from elegua.oracle import OracleClient

            oracle = OracleClient(base_url)
        self._oracle = oracle
        self._timeout = timeout
        self._context_id: str | None = None

    @property
    def adapter_id(self) -> str:
        return "wolfram-oracle"

    def initialize(self) -> None:
        if not self._oracle.health():
            raise RuntimeError("Wolfram oracle unavailable — is the server running?")
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
        self._oracle.cleanup()
        self._context_id = None

    def execute(self, task: EleguaTask) -> ValidationToken:
        try:
            wolfram_expr = build_expr(task.action, task.payload)
        except KeyError as exc:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.EXECUTION_ERROR,
                metadata={"error": f"Missing required argument: {exc}"},
            )

        data = self._oracle.evaluate_with_xact(
            wolfram_expr,
            timeout=self._timeout,
            context_id=self._context_id,
        )

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

        # Assert special case: non-True is a failure
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


def build_expr(action: str, args: dict[str, Any]) -> str:
    """Translate action + args to a Wolfram expression string.

    Raises:
        KeyError: if a required arg is absent.
        ValueError: if the action is unknown.
    """
    if action == "DefManifold":
        idx_str = ", ".join(args["indices"])
        return f"DefManifold[{args['name']}, {args['dimension']}, {{{idx_str}}}]"

    if action == "DefMetric":
        return f"DefMetric[{args['signdet']}, {args['metric']}, {args['covd']}]"

    if action == "DefTensor":
        idx_str = ",".join(args["indices"])
        tensor_slot = f"{args['name']}[{idx_str}]"
        manifold = args.get("manifold") or ""
        symmetry = args.get("symmetry") or ""
        parts = [p for p in (tensor_slot, manifold, symmetry) if p]
        return f"DefTensor[{', '.join(parts)}]"

    if action == "Evaluate":
        return str(args["expression"])

    if action == "ToCanonical":
        return f"ToCanonical[{args['expression']}]"

    if action == "Simplify":
        expr = args["expression"]
        assumptions = args.get("assumptions") or ""
        if assumptions:
            return f"Simplify[{expr}, {assumptions}]"
        return f"Simplify[{expr}]"

    if action == "Contract":
        return f"ContractMetric[{args['expression']}]"

    if action == "Assert":
        return str(args["condition"])

    if action == "CommuteCovDs":
        idx = ", ".join(args["indices"])
        return f"CommuteCovDs[{args['expression']}, {args['covd']}, {{{idx}}}]"

    if action == "SortCovDs":
        return f"SortCovDs[{args['expression']}, {args['covd']}]"

    if action == "IntegrateByParts":
        return f"IBP[{args['expression']}, {args['covd']}]"

    if action == "TotalDerivativeQ":
        return f"TotalDerivativeQ[{args['expression']}, {args['covd']}]"

    if action == "VarD":
        return f"VarD[{args['field']}, {args['covd']}][{args['expression']}]"

    if action == "DefPerturbation":
        return f"DefPerturbation[{args['tensor']}, {args['background']}, {args['order']}]"

    if action == "Perturb":
        return f"Perturb[{args['expr']}, {args['order']}]"

    if action == "PerturbCurvature":
        key = args.get("key")
        if key:
            return f"{key}[{args['covd']}]"
        return f"PerturbCurvature[{args['covd']}, {args['perturbation']}]"

    if action == "PerturbationOrder":
        return f"PerturbationOrder[{args['tensor']}]"

    if action == "PerturbationAtOrder":
        return f"PerturbationAtOrder[{args['background']}, {args['order']}]"

    if action == "CheckMetricConsistency":
        return f"CheckMetricConsistency[{args['metric']}]"

    if action == "Christoffel":
        return f"Christoffel[{args['metric']}, {args['basis']}]"

    if action == "SetBasisChange":
        return f"SetBasisChange[{args['from_basis']}, {args['to_basis']}, {args['matrix']}]"

    if action == "ChangeBasis":
        return (
            f"ChangeBasis[{args['expr']}, {args['slot']}, {args['from_basis']}, {args['to_basis']}]"
        )

    if action == "GetJacobian":
        return f"Jacobian[{args['basis1']}, {args['basis2']}]"

    if action == "BasisChangeQ":
        return f"BasisChangeQ[{args['from_basis']}, {args['to_basis']}]"

    if action == "SetComponents":
        return f"SetComponents[{args['tensor']}, {args['array']}, {args['bases']}]"

    if action == "GetComponents":
        return f"GetComponents[{args['tensor']}, {args['bases']}]"

    if action == "ComponentValue":
        idx = ", ".join(str(i) for i in args["indices"])
        return f"ComponentValue[{args['tensor']}, {{{idx}}}, {args['bases']}]"

    if action == "CTensorQ":
        return f"CTensorQ[{args['tensor']}, {args['bases']}]"

    if action == "ToBasis":
        return f"ToBasis[{args['basis']}][{args['expression']}]"

    if action == "FromBasis":
        return f"FromBasis[{args['tensor']}, {args['bases']}]"

    if action == "TraceBasisDummy":
        return f"TraceBasisDummy[{args['tensor']}, {args['bases']}]"

    if action == "CollectTensors":
        return f"CollectTensors[{args['expression']}]"

    if action == "AllContractions":
        return f"AllContractions[{args['expression']}, {args['metric']}]"

    if action == "SymmetryOf":
        return f"SymmetryOf[{args['expression']}]"

    if action == "MakeTraceFree":
        return f"MakeTraceFree[{args['expression']}, {args['metric']}]"

    raise ValueError(f"Unknown action: {action!r}")
