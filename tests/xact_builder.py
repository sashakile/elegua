"""xAct expression builder — test fixture (canonical version in sxAct).

Translates xAct-specific actions (DefManifold, DefTensor, ToCanonical, etc.)
into Wolfram expression strings. This is a local copy kept for elegua's own
tests. The canonical version is maintained in the sxAct project.

Usage::

    from elegua.wolfram.adapter import OracleAdapter
    from xact_builder import build_xact_expr

    adapter = OracleAdapter(expr_builder=build_xact_expr)
"""

from __future__ import annotations

from typing import Any


def build_xact_expr(action: str, payload: dict[str, Any]) -> str:
    """Translate an xAct action + payload to a Wolfram expression string.

    Raises:
        KeyError: if a required payload field is absent.
        ValueError: if the action is not in the xAct vocabulary.
    """
    if action == "DefManifold":
        idx_str = ", ".join(payload["indices"])
        return f"DefManifold[{payload['name']}, {payload['dimension']}, {{{idx_str}}}]"

    if action == "DefMetric":
        return f"DefMetric[{payload['signdet']}, {payload['metric']}, {payload['covd']}]"

    if action == "DefTensor":
        idx_str = ",".join(payload["indices"])
        tensor_slot = f"{payload['name']}[{idx_str}]"
        manifold = payload.get("manifold") or ""
        symmetry = payload.get("symmetry") or ""
        parts = [p for p in (tensor_slot, manifold, symmetry) if p]
        return f"DefTensor[{', '.join(parts)}]"

    if action == "Evaluate":
        return str(payload["expression"])

    if action == "ToCanonical":
        return f"ToCanonical[{payload['expression']}]"

    if action == "Simplify":
        expr = payload["expression"]
        assumptions = payload.get("assumptions") or ""
        if assumptions:
            return f"Simplify[{expr}, {assumptions}]"
        return f"Simplify[{expr}]"

    if action == "Contract":
        return f"ContractMetric[{payload['expression']}]"

    if action == "Assert":
        return str(payload["condition"])

    if action == "CommuteCovDs":
        idx = ", ".join(payload["indices"])
        return f"CommuteCovDs[{payload['expression']}, {payload['covd']}, {{{idx}}}]"

    if action == "SortCovDs":
        return f"SortCovDs[{payload['expression']}, {payload['covd']}]"

    if action == "IntegrateByParts":
        return f"IBP[{payload['expression']}, {payload['covd']}]"

    if action == "TotalDerivativeQ":
        return f"TotalDerivativeQ[{payload['expression']}, {payload['covd']}]"

    if action == "VarD":
        return f"VarD[{payload['field']}, {payload['covd']}][{payload['expression']}]"

    if action == "DefPerturbation":
        return f"DefPerturbation[{payload['tensor']}, {payload['background']}, {payload['order']}]"

    if action == "Perturb":
        return f"Perturb[{payload['expr']}, {payload['order']}]"

    if action == "PerturbCurvature":
        key = payload.get("key")
        if key:
            return f"{key}[{payload['covd']}]"
        return f"PerturbCurvature[{payload['covd']}, {payload['perturbation']}]"

    if action == "PerturbationOrder":
        return f"PerturbationOrder[{payload['tensor']}]"

    if action == "PerturbationAtOrder":
        return f"PerturbationAtOrder[{payload['background']}, {payload['order']}]"

    if action == "CheckMetricConsistency":
        return f"CheckMetricConsistency[{payload['metric']}]"

    if action == "Christoffel":
        return f"Christoffel[{payload['metric']}, {payload['basis']}]"

    if action == "SetBasisChange":
        return (
            f"SetBasisChange[{payload['from_basis']}, {payload['to_basis']}, {payload['matrix']}]"
        )

    if action == "ChangeBasis":
        return (
            f"ChangeBasis[{payload['expr']}, {payload['slot']}, "
            f"{payload['from_basis']}, {payload['to_basis']}]"
        )

    if action == "GetJacobian":
        return f"Jacobian[{payload['basis1']}, {payload['basis2']}]"

    if action == "BasisChangeQ":
        return f"BasisChangeQ[{payload['from_basis']}, {payload['to_basis']}]"

    if action == "SetComponents":
        return f"SetComponents[{payload['tensor']}, {payload['array']}, {payload['bases']}]"

    if action == "GetComponents":
        return f"GetComponents[{payload['tensor']}, {payload['bases']}]"

    if action == "ComponentValue":
        idx = ", ".join(str(i) for i in payload["indices"])
        return f"ComponentValue[{payload['tensor']}, {{{idx}}}, {payload['bases']}]"

    if action == "CTensorQ":
        return f"CTensorQ[{payload['tensor']}, {payload['bases']}]"

    if action == "ToBasis":
        return f"ToBasis[{payload['basis']}][{payload['expression']}]"

    if action == "FromBasis":
        return f"FromBasis[{payload['tensor']}, {payload['bases']}]"

    if action == "TraceBasisDummy":
        return f"TraceBasisDummy[{payload['tensor']}, {payload['bases']}]"

    if action == "CollectTensors":
        return f"CollectTensors[{payload['expression']}]"

    if action == "AllContractions":
        return f"AllContractions[{payload['expression']}, {payload['metric']}]"

    if action == "SymmetryOf":
        return f"SymmetryOf[{payload['expression']}]"

    if action == "MakeTraceFree":
        return f"MakeTraceFree[{payload['expression']}, {payload['metric']}]"

    raise ValueError(f"Unknown xAct action: {action!r}")
