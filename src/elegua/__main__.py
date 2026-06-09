"""elegua command-line tool entry point.

Usage:
    python -m elegua coverage <fixtures-dir> --axis <a,b> --output-dir <dir>
"""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
import tomllib
from pathlib import Path


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="elegua")
    sub = parser.add_subparsers(dest="command")

    cov = sub.add_parser("coverage", help="Generate fixture coverage report")
    cov.add_argument("fixtures_dir", help="Directory containing .toml fixture files")
    cov.add_argument("--axis", default="adapter,action", help="Comma-separated axis names")
    cov.add_argument("--output-dir", required=True, help="Directory to write outputs")

    args = parser.parse_args()
    if args.command == "coverage":
        sys.exit(_coverage(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
