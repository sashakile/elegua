# vale off

"""elegua command-line tool.

Commands:

    coverage <fixtures-dir> [--axis <a,b>] [--output-dir <dir>]
        Generate fixture coverage matrix report (CSV + Markdown).

    run <fixture> [--oracle NAME] [--iut NAME]
        Load a fixture and compare oracle vs IUT adapter results.
        Prints a pass-fail summary per test. Exits 0 if all pass.

        Supports both the bridge format (meta/setup/tests) and the legacy
        tasks format.
"""
# vale on

from __future__ import annotations

import argparse
import csv
import itertools
import sys
import tomllib
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from elegua.bridge import Operation, TestFile, TestFileMeta, load_test_file
from elegua.comparison import ComparisonPipeline
from elegua.multitier import MultiTierRunner
from elegua.task import TaskStatus

# ---------------------------------------------------------------------------
# Adapter resolution
# ---------------------------------------------------------------------------


def _resolve_adapter(name: str):
    """Return an Adapter instance by short name.

    Known names: echo, wolfram, sympy, oracle, oracle-client.
    """
    lowered = name.lower()
    if lowered in ("echo", "wolfram"):
        from elegua.adapter import WolframAdapter

        return WolframAdapter()
    if lowered == "sympy":
        from elegua.sympy.adapter import SympyAdapter

        return SympyAdapter()
    if lowered in ("oracle", "oracle-client"):
        from elegua.wolfram.adapter import OracleAdapter

        return OracleAdapter(base_url="http://127.0.0.1:8733")
    msg = f"Unknown adapter {name!r}. Known: echo, wolfram, sympy, oracle"
    raise SystemExit(msg)


# ---------------------------------------------------------------------------
# Legacy tasks -> TestFile conversion
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _TaskStub:
    action: str
    payload: dict[str, Any] = field(default_factory=dict)


def _load_legacy_tasks(path: Path) -> list[_TaskStub]:
    """Load a legacy [[tasks]]-format TOML file."""
    with open(path, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            print(f"error: {path}: invalid TOML: {exc}", file=sys.stderr)
            sys.exit(1)

    raw_tasks = data.get("tasks", [])
    if not raw_tasks:
        print(f"error: {path}: no tasks found", file=sys.stderr)
        sys.exit(1)

    return [
        _TaskStub(
            action=t.get("action", ""),
            payload=t.get("payload", {}),
        )
        for t in raw_tasks
    ]


def _legacy_to_test_file(path: Path, stubs: list[_TaskStub]) -> TestFile:
    """Wrap legacy task stubs into a bridge-format TestFile."""
    meta = TestFileMeta(
        id=f"legacy/{path.stem}",
        description=f"Legacy tasks format: {path.name}",
    )
    operations = [Operation(action=s.action, args=s.payload) for s in stubs]
    # type ignore used to construct bridge TestCase from legacy tasks
    # Can't use dataclass directly because TestCase is frozen; construct manually
    from elegua.bridge import TestCase as BridgeTestCase

    return TestFile(
        meta=meta,
        setup=[],
        tests=[
            BridgeTestCase(
                id=path.stem,
                description=f"Legacy task sequence from {path.name}",
                operations=operations,
            )
        ],
    )


def _load_fixture(path: Path) -> TestFile:
    """Load a fixture file, supporting both bridge and legacy formats."""
    try:
        return load_test_file(path)
    except Exception:
        stubs = _load_legacy_tasks(path)
        return _legacy_to_test_file(path, stubs)


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


def _print_summary(
    name: str,
    total: int,
    passed: int,
    failed: int,
    skipped: int,
    errors: int,
) -> None:
    print(f"\n  {name}: {total} test(s)")
    if passed:
        print(f"    ✓ {passed} passed")
    if failed:
        print(f"    ✗ {failed} failed")
    if errors:
        print(f"    ! {errors} errored")
    if skipped:
        print(f"    - {skipped} skipped")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _coverage(args: argparse.Namespace) -> int:
    fixtures_dir = Path(args.fixtures_dir)
    output_dir = Path(args.output_dir)
    axes = [a.strip() for a in args.axis.split(",")]

    if not fixtures_dir.is_dir():
        print(f"error: {fixtures_dir} is not a directory", file=sys.stderr)
        return 1

    fixtures = _load_fixture_data(fixtures_dir)

    # Collect matrix domain values and test counts
    domain: dict[str, list[str]] = {ax: [] for ax in axes}
    counts: dict[tuple[str, ...], int] = {}

    for fixture in fixtures:
        matrix = fixture.get("matrix", {})
        for ax in axes:
            for val in matrix.get(ax, []):
                val_str = str(val)
                if val_str not in domain[ax]:
                    domain[ax].append(val_str)

        for test in fixture.get("tests", []):
            key = tuple(str(test.get(ax, "")) for ax in axes)
            if all(k for k in key):
                counts[key] = counts.get(key, 0) + 1

    # Build full cartesian product from domain
    all_combos = list(itertools.product(*[domain[ax] for ax in axes]))
    rows = [(combo, counts.get(combo, 0)) for combo in all_combos]

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write CSV
    csv_path = output_dir / "coverage.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([*axes, "count"])
        for combo, count in rows:
            writer.writerow([*combo, count])

    # Write Markdown table
    md_path = output_dir / "coverage.md"
    header = [*axes, "count"]
    sep = ["---"] * len(header)
    md_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for combo, count in rows:
        flag = " ⚠" if count == 0 else ""
        md_lines.append("| " + " | ".join([*combo, str(count) + flag]) + " |")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return 0


def _load_fixture_data(fixtures_dir: Path) -> list[dict]:
    """Return raw TOML dicts for every TOML file in fixtures_dir."""
    result = []
    for path in sorted(fixtures_dir.glob("**/*.toml")):
        with open(path, "rb") as f:
            try:
                result.append(tomllib.load(f))
            except tomllib.TOMLDecodeError:
                continue
    return result


def _run(args: argparse.Namespace) -> int:
    fixture_path = Path(args.fixture)
    if not fixture_path.is_file():
        print(f"error: {fixture_path} is not a file", file=sys.stderr)
        return 1

    test_file = _load_fixture(fixture_path)
    oracle = _resolve_adapter(args.oracle)
    iut = _resolve_adapter(args.iut)

    pipeline = ComparisonPipeline()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with MultiTierRunner(oracle, iut, pipeline=pipeline) as runner:
            results = runner.verify(test_file)

    total = len(results)
    passed = 0
    failed = 0
    skipped = 0
    errors = 0

    print(f"\n{'=' * 48}")
    print(f"  Eleguá — {fixture_path.name}")
    print(f"  Oracle: {args.oracle}   IUT: {args.iut}")
    print(f"{'=' * 48}")

    for vr in results:
        if vr.skipped:
            skipped += 1
            print(f"  - {vr.test_id}: SKIPPED ({vr.skip_reason})")
            continue
        if vr.comparison.status == TaskStatus.OK:
            passed += 1
            print(f"  ✓ {vr.test_id}: PASS")
        elif vr.oracle_error or vr.iut_error:
            errors += 1
            src = "oracle" if vr.oracle_error else "iut"
            err = vr.oracle_error or vr.iut_error
            print(f"  ! {vr.test_id}: ERROR ({src}: {err})")
        else:
            failed += 1
            detail = vr.comparison.diagnostics.get("detail", "")
            suffix = f" — {detail}" if detail else ""
            print(f"  ✗ {vr.test_id}: FAIL (tier={vr.comparison.layer}){suffix}")

    _print_summary(fixture_path.name, total, passed, failed, skipped, errors)

    return 0 if (passed + skipped == total and errors == 0) else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(prog="elegua")
    sub = parser.add_subparsers(dest="command")

    cov = sub.add_parser("coverage", help="Generate fixture coverage report")
    cov.add_argument("fixtures_dir", help="Directory containing .toml fixture files")
    cov.add_argument("--axis", default="adapter,action", help="Comma-separated axis names")
    cov.add_argument("--output-dir", required=True, help="Directory to write outputs")

    run_cmd = sub.add_parser("run", help="Run fixture through oracle and IUT adapters")
    run_cmd.add_argument("fixture", help="Path to .toml fixture file")
    run_cmd.add_argument(
        "--oracle", default="wolfram", help="Oracle adapter name (default: wolfram)"
    )
    run_cmd.add_argument("--iut", default="wolfram", help="IUT adapter name (default: wolfram)")

    args = parser.parse_args()
    if args.command == "coverage":
        sys.exit(_coverage(args))
    elif args.command == "run":
        sys.exit(_run(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
