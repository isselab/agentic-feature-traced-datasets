#!/usr/bin/env python3
"""Render the README dataset table from .gitmodules."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from catalog import read_datasets

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
START = "<!-- DATASETS:START -->"
END = "<!-- DATASETS:END -->"


def render() -> str:
    datasets = read_datasets(ROOT)
    if not datasets:
        return "_No datasets are registered yet._"
    lines = ["| Dataset | Repository | Local path |", "|---|---|---|"]
    for item in datasets:
        lines.append(
            f"| `{item.name}` | [{item.url.removesuffix('.git')}]"
            f"({item.url.removesuffix('.git')}) | `{item.path}` |"
        )
    return "\n".join(lines)


def expected_readme(current: str) -> str:
    if START not in current or END not in current:
        raise ValueError("README is missing dataset table markers")
    before, remainder = current.split(START, 1)
    _, after = remainder.split(END, 1)
    return f"{before}{START}\n{render()}\n{END}{after}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = README.read_text(encoding="utf-8")
    expected = expected_readme(current)
    if args.check:
        if current != expected:
            print("README dataset table is stale; run scripts/render_catalog.py", file=sys.stderr)
            raise SystemExit(1)
        print("README dataset table is current")
    else:
        README.write_text(expected, encoding="utf-8")
        print("Updated README dataset table")


if __name__ == "__main__":
    main()
