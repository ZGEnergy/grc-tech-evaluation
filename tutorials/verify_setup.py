from __future__ import annotations

import sys
from pathlib import Path


def check_import(label: str, import_fn: callable) -> bool:
    try:
        import_fn()
        print(f"PASS  {label}")
        return True
    except Exception as exc:
        print(f"FAIL  {label}  ({exc})")
        return False


def check_file(label: str, path: Path) -> bool:
    if path.exists():
        print(f"PASS  {label}")
        return True
    else:
        print(f"FAIL  {label}  (file not found: {path})")
        return False


def main() -> int:
    results: list[bool] = []

    results.append(check_import("import marimo", lambda: __import__("marimo")))
    results.append(check_import("import altair", lambda: __import__("altair")))
    results.append(check_import("import pandas", lambda: __import__("pandas")))
    results.append(
        check_import(
            "from scripts.reconcile_bus_gen import parse_matpower_case",
            lambda: __import__("scripts.reconcile_bus_gen", fromlist=["parse_matpower_case"]),
        )
    )
    results.append(
        check_import(
            "import scripts.tiny_cleanup_classify",
            lambda: __import__("scripts.tiny_cleanup_classify"),
        )
    )

    case39_path = Path(__file__).resolve().parent / ".." / "data" / "networks" / "case39.m"
    results.append(check_file("data/networks/case39.m exists", case39_path))

    if all(results):
        print(f"\nAll {len(results)} checks passed.")
        return 0
    else:
        failed = sum(1 for r in results if not r)
        print(f"\n{failed}/{len(results)} checks FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
