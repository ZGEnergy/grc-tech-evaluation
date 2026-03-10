"""Data augmentation pipeline runner.

Orchestrates the data augmentation scripts in dependency order.
Runs the full TINY (case39) pipeline end-to-end, or individual stages.

Usage:
    python -m scripts.run_pipeline              # run full TINY pipeline
    python -m scripts.run_pipeline --stage tiny  # same as above
    python -m scripts.run_pipeline --stage reference  # reference table only
    python -m scripts.run_pipeline --list        # list available stages
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StageResult:
    """Result of running a pipeline stage."""

    name: str
    success: bool
    elapsed_s: float
    error: str | None = None


def _run_stage(name: str, func: object, *args: object, **kwargs: object) -> StageResult:
    """Run a single pipeline stage with timing and error handling."""
    print(f"\n{'=' * 60}")
    print(f"  Stage: {name}")
    print(f"{'=' * 60}")
    t0 = time.monotonic()
    try:
        func(*args, **kwargs)
        elapsed = time.monotonic() - t0
        print(f"  OK ({elapsed:.1f}s)")
        return StageResult(name=name, success=True, elapsed_s=elapsed)
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print(f"  FAILED ({elapsed:.1f}s): {exc}", file=sys.stderr)
        return StageResult(name=name, success=False, elapsed_s=elapsed, error=str(exc))


def run_reference() -> list[StageResult]:
    """Build the RTS-GMLC reference table."""
    from scripts.build_rts_gmlc_reference import main as build_ref

    return [_run_stage("build_rts_gmlc_reference", build_ref)]


def run_tiny() -> list[StageResult]:
    """Run the full TINY (case39) pipeline."""
    results: list[StageResult] = []

    # Stage 0: Reference table (needed by later stages)
    from scripts.build_rts_gmlc_reference import main as build_ref

    results.append(_run_stage("build_rts_gmlc_reference", build_ref))
    if not results[-1].success:
        return results

    # Stage 1: Cleanup + classify
    from scripts.tiny_cleanup_classify import main as cleanup_classify

    results.append(_run_stage("tiny_cleanup_classify", cleanup_classify))
    if not results[-1].success:
        return results

    # Stage 2: Temporal parameters
    from scripts.tiny_gen_temporal_params import main as gen_temporal

    results.append(_run_stage("tiny_gen_temporal_params", gen_temporal))

    # Stage 3: Renewable profiles (independent of stages 1-2)
    from scripts.renewable_profiles import main as renewable

    results.append(_run_stage("renewable_profiles", renewable))

    # Stage 4: Load profile (depends on stage 1)
    from scripts.tiny_load_profile import main as load_profile

    results.append(_run_stage("tiny_load_profile", load_profile))

    # Stage 5: Reserve definitions (depends on stages 1-2)
    from scripts.tiny_reserve_definitions import main as reserves

    results.append(_run_stage("tiny_reserve_definitions", reserves))

    # Stage 6: Stochastic scenarios (depends on stage 3)
    from scripts.tiny_stochastic_scenarios import main as scenarios

    results.append(_run_stage("tiny_stochastic_scenarios", scenarios))

    # Stage 7: Flowgates (depends on stages 1, 4)
    from scripts.tiny_flowgates import main as flowgates

    results.append(_run_stage("tiny_flowgates", flowgates))

    # Stage 8: BESS + DR
    from scripts.tiny_bess_dr import main as bess_dr

    results.append(_run_stage("tiny_bess_dr", bess_dr))

    return results


STAGES = {
    "reference": ("Build RTS-GMLC reference table", run_reference),
    "tiny": ("Run full TINY (case39) pipeline", run_tiny),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Data augmentation pipeline runner")
    parser.add_argument(
        "--stage",
        choices=list(STAGES.keys()),
        default="tiny",
        help="Pipeline stage to run (default: tiny)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available stages and exit",
    )
    args = parser.parse_args()

    if args.list:
        print("Available stages:")
        for name, (desc, _) in STAGES.items():
            print(f"  {name:15s}  {desc}")
        return

    desc, runner = STAGES[args.stage]
    print(f"Running: {desc}")
    print(f"Working directory: {Path.cwd()}")

    results = runner()

    # Summary
    print(f"\n{'=' * 60}")
    print("  Pipeline Summary")
    print(f"{'=' * 60}")
    total_time = sum(r.elapsed_s for r in results)
    for r in results:
        status = "OK" if r.success else "FAILED"
        print(f"  [{status:6s}] {r.name} ({r.elapsed_s:.1f}s)")
    print(f"\n  Total: {total_time:.1f}s")

    failed = [r for r in results if not r.success]
    if failed:
        print(f"\n  {len(failed)} stage(s) failed.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n  All {len(results)} stages passed.")


if __name__ == "__main__":
    main()
