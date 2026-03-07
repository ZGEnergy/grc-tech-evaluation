"""Runner for SMALL tests that outputs full JSON to files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

TESTS = {
    "a10": ("expressiveness", "test_a10_lossy_dcopf_lmp_small"),
    "a11": ("expressiveness", "test_a11_distributed_slack_opf_small"),
    "a9": ("expressiveness", "test_a9_scopf_small"),
    "b8": ("extensibility", "test_b8_reference_bus_config_small"),
    "a5": ("expressiveness", "test_a5_scuc_small"),
    "a6": ("expressiveness", "test_a6_sced_small"),
    "b4": ("extensibility", "test_b4_stochastic_wrapping_small"),
}


def main():
    test_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not test_id or test_id not in TESTS:
        print(f"Usage: python _run_small.py <{'|'.join(TESTS.keys())}>")
        sys.exit(1)

    dim, mod_name = TESTS[test_id]
    sys.path.insert(0, str(Path(__file__).parent / dim))

    mod = __import__(mod_name)
    result = mod.run()

    # Write full JSON to file
    out_path = Path(__file__).parent / f"_result_{test_id}_small.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Written to {out_path}")

    # Print summary
    print(f"status: {result['status']}")
    print(f"wall_clock_seconds: {result['wall_clock_seconds']}")
    print(f"errors: {result['errors']}")
    if result.get("details"):
        for k in [
            "objective",
            "converged",
            "solver_status",
            "lossless_dcopf",
            "lossy_dcopf",
            "lmp_comparison",
            "n_scenarios_solved",
        ]:
            if k in result["details"]:
                print(f"  {k}: {result['details'][k]}")


if __name__ == "__main__":
    main()
