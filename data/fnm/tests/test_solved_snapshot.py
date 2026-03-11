"""Tests for solved-snapshot confirmation (PRD 08).

Tests T01-T06 are synthetic unit tests requiring no FNM data.
Tests T07-T08 are integration tests using synthetic CSV fixtures.
Tests T09-T10 are FNM integration tests requiring FNM_PATH.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from fnm.scripts.solved_snapshot import (
    DistributionStats,
    IndicatorResult,
    IndicatorSignal,
    SnapshotClassification,
    build_confirmation,
    classify_overall,
    classify_va,
    classify_vm,
    main,
)

# ---------------------------------------------------------------------------
# T01: test_classify_vm_solved
# ---------------------------------------------------------------------------


def test_classify_vm_solved() -> None:
    """VM with mean=1.01, std=0.03, 10% exact 1.0 -> SOLVED_SIGNAL."""
    stats = DistributionStats(
        count=100,
        mean=1.01,
        std=0.03,
        min=0.95,
        max=1.06,
        pct_exact_reference=10.0,
    )
    result = classify_vm(stats)
    assert result.signal == IndicatorSignal.SOLVED_SIGNAL
    assert result.name == "VM"


# ---------------------------------------------------------------------------
# T02: test_classify_vm_flat
# ---------------------------------------------------------------------------


def test_classify_vm_flat() -> None:
    """VM all exactly 1.0 -> FLAT_SIGNAL."""
    stats = DistributionStats(
        count=100,
        mean=1.0,
        std=0.0,
        min=1.0,
        max=1.0,
        pct_exact_reference=100.0,
    )
    result = classify_vm(stats)
    assert result.signal == IndicatorSignal.FLAT_SIGNAL
    assert result.name == "VM"


# ---------------------------------------------------------------------------
# T03: test_classify_va_solved
# ---------------------------------------------------------------------------


def test_classify_va_solved() -> None:
    """VA with mean=-5.2, std=8.3, 2% exactly 0.0 -> SOLVED_SIGNAL."""
    stats = DistributionStats(
        count=100,
        mean=-5.2,
        std=8.3,
        min=-30.0,
        max=15.0,
        pct_exact_reference=2.0,
    )
    result = classify_va(stats)
    assert result.signal == IndicatorSignal.SOLVED_SIGNAL
    assert result.name == "VA"


# ---------------------------------------------------------------------------
# T04: test_classify_overall_solved
# ---------------------------------------------------------------------------


def test_classify_overall_solved() -> None:
    """All three SOLVED_SIGNAL -> SOLVED."""
    vm = IndicatorResult("VM", IndicatorSignal.SOLVED_SIGNAL, "solved")
    va = IndicatorResult("VA", IndicatorSignal.SOLVED_SIGNAL, "solved")
    qg = IndicatorResult("Qg", IndicatorSignal.SOLVED_SIGNAL, "solved")
    assert classify_overall(vm, va, qg) == SnapshotClassification.SOLVED


# ---------------------------------------------------------------------------
# T05: test_classify_overall_flat_start
# ---------------------------------------------------------------------------


def test_classify_overall_flat_start() -> None:
    """All three FLAT_SIGNAL -> FLAT_START."""
    vm = IndicatorResult("VM", IndicatorSignal.FLAT_SIGNAL, "flat")
    va = IndicatorResult("VA", IndicatorSignal.FLAT_SIGNAL, "flat")
    qg = IndicatorResult("Qg", IndicatorSignal.FLAT_SIGNAL, "flat")
    assert classify_overall(vm, va, qg) == SnapshotClassification.FLAT_START


# ---------------------------------------------------------------------------
# T06: test_classify_overall_indeterminate_mixed
# ---------------------------------------------------------------------------


def test_classify_overall_indeterminate_mixed() -> None:
    """VM SOLVED, VA FLAT, Qg AMBIGUOUS -> INDETERMINATE."""
    vm = IndicatorResult("VM", IndicatorSignal.SOLVED_SIGNAL, "solved")
    va = IndicatorResult("VA", IndicatorSignal.FLAT_SIGNAL, "flat")
    qg = IndicatorResult("Qg", IndicatorSignal.AMBIGUOUS, "ambiguous")
    assert classify_overall(vm, va, qg) == SnapshotClassification.INDETERMINATE


# ---------------------------------------------------------------------------
# Synthetic CSV helpers
# ---------------------------------------------------------------------------


def _write_bus_csv_with_header(
    path: Path,
    rows: list[dict[str, str | float]],
) -> None:
    """Write a bus CSV with header row."""
    fieldnames = [
        "bus_i",
        "type",
        "Pd",
        "Qd",
        "Gs",
        "Bs",
        "area",
        "vm",
        "va",
        "base_kv",
        "zone",
        "Vmax",
        "Vmin",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_gen_csv_with_header(
    path: Path,
    rows: list[dict[str, str | float]],
) -> None:
    """Write a generator CSV with header row."""
    fieldnames = ["bus", "pg", "qg", "qmax", "qmin", "vs", "mbase", "status", "Pmax", "Pmin"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# T07: test_build_confirmation_solved_synthetic
# ---------------------------------------------------------------------------


def test_build_confirmation_solved_synthetic(tmp_path: Path) -> None:
    """Synthetic CSV with solved values -> SOLVED, isolated bus excluded."""
    import random

    random.seed(42)

    bus_rows: list[dict[str, str | float]] = []
    # 50 non-isolated buses with varied VM (0.95-1.05) and VA (-20 to +15)
    for i in range(1, 51):
        vm = 0.95 + random.random() * 0.10  # 0.95 to 1.05
        va = -20.0 + random.random() * 35.0  # -20 to +15
        bus_rows.append(
            {
                "bus_i": i,
                "type": 1,
                "Pd": 100.0,
                "Qd": 50.0,
                "Gs": 0.0,
                "Bs": 0.0,
                "area": 1,
                "vm": f"{vm:.6f}",
                "va": f"{va:.6f}",
                "base_kv": 230.0,
                "zone": 1,
                "Vmax": 1.1,
                "Vmin": 0.9,
            }
        )

    # 1 isolated bus (type=4) — should be excluded
    bus_rows.append(
        {
            "bus_i": 99,
            "type": 4,
            "Pd": 0.0,
            "Qd": 0.0,
            "Gs": 0.0,
            "Bs": 0.0,
            "area": 1,
            "vm": "1.000000",
            "va": "0.000000",
            "base_kv": 230.0,
            "zone": 1,
            "Vmax": 1.1,
            "Vmin": 0.9,
        }
    )

    bus_csv = tmp_path / "bus.csv"
    _write_bus_csv_with_header(bus_csv, bus_rows)

    # 20 generators with non-zero Qg
    gen_rows: list[dict[str, str | float]] = []
    for i in range(1, 21):
        qg = -50.0 + random.random() * 100.0  # -50 to +50 MVAr
        gen_rows.append(
            {
                "bus": i,
                "pg": 200.0,
                "qg": f"{qg:.4f}",
                "qmax": 100.0,
                "qmin": -100.0,
                "vs": 1.0,
                "mbase": 100.0,
                "status": 1,
                "Pmax": 500.0,
                "Pmin": 0.0,
            }
        )

    gen_csv = tmp_path / "gen.csv"
    _write_gen_csv_with_header(gen_csv, gen_rows)

    confirmation = build_confirmation(bus_csv, gen_csv, canonical_parser="TEST")

    assert confirmation.classification == SnapshotClassification.SOLVED
    assert confirmation.buses_excluded_isolated == 1
    assert confirmation.buses_analyzed == 50
    assert confirmation.vm_stats.std > 0.01
    assert confirmation.vm_indicator.signal == IndicatorSignal.SOLVED_SIGNAL
    assert confirmation.va_indicator.signal == IndicatorSignal.SOLVED_SIGNAL
    assert confirmation.qg_indicator.signal == IndicatorSignal.SOLVED_SIGNAL


# ---------------------------------------------------------------------------
# T08: test_build_confirmation_flat_start_synthetic
# ---------------------------------------------------------------------------


def test_build_confirmation_flat_start_synthetic(tmp_path: Path) -> None:
    """Flat-start synthetic CSVs -> FLAT_START."""
    bus_rows: list[dict[str, str | float]] = []
    for i in range(1, 101):
        bus_rows.append(
            {
                "bus_i": i,
                "type": 1,
                "Pd": 50.0,
                "Qd": 20.0,
                "Gs": 0.0,
                "Bs": 0.0,
                "area": 1,
                "vm": "1.000000",
                "va": "0.000000",
                "base_kv": 345.0,
                "zone": 1,
                "Vmax": 1.1,
                "Vmin": 0.9,
            }
        )

    bus_csv = tmp_path / "bus.csv"
    _write_bus_csv_with_header(bus_csv, bus_rows)

    gen_rows: list[dict[str, str | float]] = []
    for i in range(1, 31):
        gen_rows.append(
            {
                "bus": i,
                "pg": 100.0,
                "qg": "0.0000",
                "qmax": 50.0,
                "qmin": -50.0,
                "vs": 1.0,
                "mbase": 100.0,
                "status": 1,
                "Pmax": 300.0,
                "Pmin": 0.0,
            }
        )

    gen_csv = tmp_path / "gen.csv"
    _write_gen_csv_with_header(gen_csv, gen_rows)

    confirmation = build_confirmation(bus_csv, gen_csv, canonical_parser="TEST")

    assert confirmation.classification == SnapshotClassification.FLAT_START
    assert confirmation.buses_analyzed == 100
    assert confirmation.buses_excluded_isolated == 0
    assert confirmation.vm_indicator.signal == IndicatorSignal.FLAT_SIGNAL
    assert confirmation.va_indicator.signal == IndicatorSignal.FLAT_SIGNAL
    assert confirmation.qg_indicator.signal == IndicatorSignal.FLAT_SIGNAL


# ---------------------------------------------------------------------------
# T09: test_fnm_snapshot_produces_classification (FNM required)
# ---------------------------------------------------------------------------


@pytest.mark.fnm
def test_fnm_snapshot_produces_classification(require_fnm) -> None:
    """Run with actual parser output -> valid SnapshotClassification."""
    fnm_path = require_fnm.fnm_path
    assert fnm_path is not None

    # Locate canonical parser CSV outputs in intermediate directory
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    intermediate = repo_root / "data" / "fnm" / "intermediate"

    # Try MATPOWER first, then GridCal
    bus_csv = None
    gen_csv = None
    parser_name = ""

    mpc_bus = intermediate / "matpower" / "mpc_bus.csv"
    mpc_gen = intermediate / "matpower" / "mpc_gen.csv"
    gc_bus = intermediate / "gridcal" / "gridcal_buses.csv"
    gc_gen = intermediate / "gridcal" / "gridcal_generators.csv"

    if mpc_bus.exists() and mpc_gen.exists():
        bus_csv = mpc_bus
        gen_csv = mpc_gen
        parser_name = "MATPOWER"
    elif gc_bus.exists() and gc_gen.exists():
        bus_csv = gc_bus
        gen_csv = gc_gen
        parser_name = "GRIDCAL"
    else:
        pytest.skip(
            "No canonical parser CSV outputs found in intermediate/. Run parser pipeline first."
        )

    confirmation = build_confirmation(bus_csv, gen_csv, canonical_parser=parser_name)

    assert confirmation.classification in (
        SnapshotClassification.SOLVED,
        SnapshotClassification.FLAT_START,
        SnapshotClassification.INDETERMINATE,
    )
    assert confirmation.buses_analyzed > 0
    assert confirmation.qg_stats.total_generators > 0


# ---------------------------------------------------------------------------
# T10: test_fnm_snapshot_report_files_written (FNM required)
# ---------------------------------------------------------------------------


@pytest.mark.fnm
def test_fnm_snapshot_report_files_written(require_fnm, tmp_path: Path) -> None:
    """Run main() with actual CSVs -> verify JSON and markdown files exist."""
    fnm_path = require_fnm.fnm_path
    assert fnm_path is not None

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    intermediate = repo_root / "data" / "fnm" / "intermediate"

    mpc_bus = intermediate / "matpower" / "mpc_bus.csv"
    mpc_gen = intermediate / "matpower" / "mpc_gen.csv"
    gc_bus = intermediate / "gridcal" / "gridcal_buses.csv"
    gc_gen = intermediate / "gridcal" / "gridcal_generators.csv"

    if mpc_bus.exists() and mpc_gen.exists():
        bus_csv = mpc_bus
        gen_csv = mpc_gen
        parser_name = "MATPOWER"
    elif gc_bus.exists() and gc_gen.exists():
        bus_csv = gc_bus
        gen_csv = gc_gen
        parser_name = "GRIDCAL"
    else:
        pytest.skip(
            "No canonical parser CSV outputs found in intermediate/. Run parser pipeline first."
        )

    main(
        [
            "--bus-csv",
            str(bus_csv),
            "--gen-csv",
            str(gen_csv),
            "--parser",
            parser_name,
            "--output-dir",
            str(tmp_path),
        ]
    )

    json_path = tmp_path / "solved_snapshot_report.json"
    md_path = tmp_path / "solved_snapshot_report.md"

    assert json_path.exists(), "JSON report was not created"
    assert md_path.exists(), "Markdown report was not created"

    # Validate JSON structure
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert "classification" in report
    assert report["classification"] in ("solved", "flat_start", "indeterminate")
    assert "vm_stats" in report
    assert "va_stats" in report
    assert "qg_stats" in report
    assert "vm_indicator" in report
    assert "va_indicator" in report
    assert "qg_indicator" in report
    assert "phase3_implications" in report

    # Validate markdown has key sections
    md_text = md_path.read_text(encoding="utf-8")
    assert "# Solved-Snapshot Confirmation Report" in md_text
    assert "## Phase 3 Implications" in md_text
