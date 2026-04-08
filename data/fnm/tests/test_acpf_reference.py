"""Tests for ACPF Reference Solution Extraction (PRD 03/02).

Tests T01-T14 are synthetic (no FNM data required).
Tests T15-T16 require FNM_PATH and D6/D8 outputs.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pytest

from fnm.scripts.acpf_reference import (
    ConvergenceInfo,
    SolutionSource,
    SolverSettings,
    SystemSummary,
    build_acpf_reference,
    compute_system_summary,
    determine_solution_source,
    extract_bus_results,
    write_branches_csv,
    write_buses_csv,
    write_generators_csv,
    write_summary_json,
)

# ---------------------------------------------------------------------------
# Helpers for synthetic CSV generation
# ---------------------------------------------------------------------------


def _write_bus_csv(
    path: Path,
    *,
    n_buses: int = 50,
    n_isolated: int = 3,
    n_deenergized: int = 1,
    with_header: bool = True,
    vm_base: float = 1.0,
    vm_spread: float = 0.05,
    va_spread: float = 15.0,
    seed: int = 42,
) -> list[dict]:
    """Create a synthetic bus CSV and return the expected non-excluded rows."""
    rng = random.Random(seed)
    rows = []
    expected = []

    for i in range(1, n_buses + 1):
        bus_num = i * 10
        if i <= n_isolated:
            bus_type = 4  # isolated
        elif i == n_isolated + 1:
            bus_type = 3  # slack
        else:
            bus_type = 1  # PQ

        if i == n_buses and n_deenergized > 0:
            vm = 0.0
            va = 0.0
        else:
            vm = vm_base + rng.uniform(-vm_spread, vm_spread)
            va = rng.uniform(-va_spread, va_spread)

        pd = rng.uniform(0, 50)
        qd = rng.uniform(-10, 20)

        if with_header:
            rows.append(
                {
                    "bus_i": str(bus_num),
                    "type": str(bus_type),
                    "Pd": f"{pd:.4f}",
                    "Qd": f"{qd:.4f}",
                    "Gs": "0",
                    "Bs": "0",
                    "area": "1",
                    "Vm": f"{vm:.8f}",
                    "Va": f"{va:.6f}",
                    "baseKV": "138",
                    "zone": "1",
                    "Vmax": "1.1",
                    "Vmin": "0.9",
                }
            )
        else:
            rows.append(
                [
                    str(bus_num),
                    str(bus_type),
                    f"{pd:.4f}",
                    f"{qd:.4f}",
                    "0",
                    "0",
                    "1",
                    f"{vm:.8f}",
                    f"{va:.6f}",
                    "138",
                    "1",
                    "1.1",
                    "0.9",
                ]
            )

        if bus_type != 4 and vm != 0.0:
            expected.append({"bus": bus_num, "VM": vm, "VA": va})

    with open(path, "w", newline="", encoding="utf-8") as f:
        if with_header:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(f)
            writer.writerows(rows)

    expected.sort(key=lambda r: r["bus"])
    return expected


def _write_branch_csv(
    path: Path,
    *,
    n_branches: int = 30,
    with_header: bool = True,
    seed: int = 42,
) -> list[dict]:
    """Create a synthetic branch CSV with P/Q flow values and return expected rows."""
    rng = random.Random(seed)
    rows = []
    expected = []

    for i in range(1, n_branches + 1):
        from_bus = i * 10
        to_bus = (i + 1) * 10
        ckt = "1"
        status = 1
        # Realistic flow: P_from positive, P_to negative, losses = P_from + P_to > 0
        p_from = rng.uniform(10, 200)
        losses = rng.uniform(0.1, 5.0)
        p_to = -(p_from - losses)
        q_from = rng.uniform(-50, 50)
        q_to = rng.uniform(-50, 50)

        if with_header:
            rows.append(
                {
                    "fbus": str(from_bus),
                    "tbus": str(to_bus),
                    "ckt": ckt,
                    "r": "0.01",
                    "x": "0.1",
                    "b": "0.02",
                    "rateA": "100",
                    "rateB": "100",
                    "rateC": "100",
                    "ratio": "0",
                    "status": str(status),
                    "angmin": "-360",
                    "angmax": "360",
                    "Pf": f"{p_from:.4f}",
                    "Qf": f"{q_from:.4f}",
                    "Pt": f"{p_to:.4f}",
                    "Qt": f"{q_to:.4f}",
                }
            )
        else:
            rows.append(
                [
                    str(from_bus),
                    str(to_bus),
                    "0.01",
                    "0.1",
                    "0.02",
                    "100",
                    "100",
                    "100",
                    "0",
                    "0",
                    str(status),
                    "-360",
                    "360",
                    f"{p_from:.4f}",
                    f"{q_from:.4f}",
                    f"{p_to:.4f}",
                    f"{q_to:.4f}",
                ]
            )

        expected.append(
            {
                "from_bus": from_bus,
                "to_bus": to_bus,
                "ckt": ckt if with_header else "1",
                "P_from": p_from,
                "Q_from": q_from,
                "P_to": p_to,
                "Q_to": q_to,
            }
        )

    with open(path, "w", newline="", encoding="utf-8") as f:
        if with_header:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(f)
            writer.writerows(rows)

    expected.sort(key=lambda r: (r["from_bus"], r["to_bus"], r["ckt"]))
    return expected


def _write_gen_csv(
    path: Path,
    *,
    n_generators: int = 15,
    with_header: bool = True,
    seed: int = 42,
) -> list[dict]:
    """Create a synthetic generator CSV and return expected rows."""
    rng = random.Random(seed)
    rows = []
    expected = []

    for i in range(1, n_generators + 1):
        bus_num = (i + 3) * 10  # start after isolated buses
        machine_id = str(i % 3 + 1)
        pg = rng.uniform(10, 500)
        qg = rng.uniform(-100, 200)
        status = 1

        if with_header:
            rows.append(
                {
                    "bus": str(bus_num),
                    "machine_id": machine_id,
                    "Pg": f"{pg:.4f}",
                    "Qg": f"{qg:.4f}",
                    "Qmax": "999",
                    "Qmin": "-999",
                    "Vg": "1.0",
                    "status": str(status),
                    "Pmax": "999",
                    "Pmin": "0",
                }
            )
        else:
            rows.append(
                [
                    str(bus_num),
                    f"{pg:.4f}",
                    f"{qg:.4f}",
                    "999",
                    "-999",
                    "1.0",
                    "100",
                    str(status),
                    "999",
                    "0",
                ]
            )

        expected.append(
            {
                "bus": bus_num,
                "machine_id": machine_id if with_header else str(1),
                "P": pg,
                "Q": qg,
            }
        )

    with open(path, "w", newline="", encoding="utf-8") as f:
        if with_header:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(f)
            writer.writerows(rows)

    expected.sort(key=lambda r: (r["bus"], r["machine_id"]))
    return expected


def _write_snapshot_json(path: Path, classification: str = "solved") -> None:
    """Write a minimal D8 snapshot confirmation JSON."""
    data = {"classification": classification}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===========================================================================
# T01-T03: Path selection
# ===========================================================================


def test_determine_source_solved() -> None:
    """T01: determine_solution_source('solved') returns EXTRACTED."""
    result = determine_solution_source("solved")
    assert result == SolutionSource.EXTRACTED


def test_determine_source_flat_start() -> None:
    """T02: determine_solution_source('flat_start') returns COMPUTED."""
    result = determine_solution_source("flat_start")
    assert result == SolutionSource.COMPUTED


def test_determine_source_indeterminate_raises() -> None:
    """T03: determine_solution_source('indeterminate') raises ValueError."""
    with pytest.raises(ValueError, match="indeterminate"):
        determine_solution_source("indeterminate")


# ===========================================================================
# T04-T05: Bus extraction
# ===========================================================================


def test_extract_bus_results_excludes_isolated(tmp_path: Path) -> None:
    """T04: extract_bus_results excludes type=4 and VM=0 buses."""
    bus_csv = tmp_path / "bus.csv"
    expected = _write_bus_csv(bus_csv, n_buses=50, n_isolated=3, n_deenergized=1, with_header=True)

    result = extract_bus_results(bus_csv)

    # Should have 50 - 3 (isolated) - 1 (VM=0) = 46 buses
    assert len(result) == 46
    assert len(result) == len(expected)

    # No isolated or deenergized buses in output
    result_bus_nums = {r["bus"] for r in result}
    # buses 10, 20, 30 are type=4 (isolated), bus 500 has VM=0
    assert 10 not in result_bus_nums
    assert 20 not in result_bus_nums
    assert 30 not in result_bus_nums
    assert 500 not in result_bus_nums

    # Sorted ascending
    bus_nums = [r["bus"] for r in result]
    assert bus_nums == sorted(bus_nums)


def test_extract_bus_results_precision(tmp_path: Path) -> None:
    """T05: VM values preserve at least 6 decimal places."""
    bus_csv = tmp_path / "bus.csv"
    # Create a CSV with precise VM values
    with open(bus_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "bus_i",
                "type",
                "Pd",
                "Qd",
                "Gs",
                "Bs",
                "area",
                "Vm",
                "Va",
                "baseKV",
                "zone",
                "Vmax",
                "Vmin",
            ]
        )
        writer.writerow(
            [
                "1",
                "1",
                "10",
                "5",
                "0",
                "0",
                "1",
                "1.01234567",
                "-3.456789",
                "138",
                "1",
                "1.1",
                "0.9",
            ]
        )
        writer.writerow(
            [
                "2",
                "3",
                "20",
                "10",
                "0",
                "0",
                "1",
                "0.98765432",
                "2.123456",
                "138",
                "1",
                "1.1",
                "0.9",
            ]
        )

    result = extract_bus_results(bus_csv)
    assert len(result) == 2

    # Check that VM precision is maintained to at least 6 decimal places
    for r in result:
        if r["bus"] == 1:
            assert abs(r["VM"] - 1.01234567) < 1e-6
        elif r["bus"] == 2:
            assert abs(r["VM"] - 0.98765432) < 1e-6


# ===========================================================================
# T06-T07: Data structures
# ===========================================================================


def test_solver_settings_defaults() -> None:
    """T06: SolverSettings fields set correctly, enforce_area_interchange defaults to None."""
    settings = SolverSettings(
        name="runpf",
        tolerance=1e-8,
        max_iterations=100,
        q_limits_enforced=True,
        q_limit_strategy="two_stage_relaxed_then_enforced",
    )
    assert settings.name == "runpf"
    assert settings.tolerance == 1e-8
    assert settings.max_iterations == 100
    assert settings.q_limits_enforced is True
    assert settings.q_limit_strategy == "two_stage_relaxed_then_enforced"
    assert settings.enforce_area_interchange is None


def test_convergence_info_null_for_extracted() -> None:
    """T07: ConvergenceInfo() with no args has all None fields."""
    info = ConvergenceInfo()
    assert info.converged is None
    assert info.iterations is None
    assert info.final_mismatch_mw is None
    assert info.final_mismatch_mvar is None


# ===========================================================================
# T08-T10: Output CSV format
# ===========================================================================


def test_write_buses_csv_schema(tmp_path: Path) -> None:
    """T08: buses_acpf.csv has correct schema and precision."""
    rng = random.Random(42)
    bus_results = [
        {"bus": i, "VM": 0.95 + rng.uniform(0, 0.1), "VA": rng.uniform(-15, 10)}
        for i in range(1, 21)
    ]

    output = tmp_path / "buses_acpf.csv"
    write_buses_csv(bus_results, output)

    # Read back and verify
    with open(output, encoding="utf-8") as f:
        raw_text = f.read()

    lines = raw_text.strip().split("\n")
    assert lines[0] == "bus,VM,VA"
    assert len(lines) == 21  # header + 20 data rows

    # Verify bus column is integer
    with open(output, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 20
    for row in rows:
        int(row["bus"])  # should not raise

    # Check VM has at least 6 decimal places in raw text
    for line in lines[1:]:
        vm_str = line.split(",")[1]
        decimal_part = vm_str.split(".")[1]
        assert len(decimal_part) >= 6, f"VM '{vm_str}' has fewer than 6 decimal places"


def test_write_branches_csv_schema(tmp_path: Path) -> None:
    """T09: branches_acpf.csv has correct schema and positive losses."""
    rng = random.Random(42)
    branch_results = []
    for i in range(1, 31):
        p_from = rng.uniform(10, 200)
        losses = rng.uniform(0.1, 5.0)
        p_to = -(p_from - losses)
        branch_results.append(
            {
                "from_bus": i * 10,
                "to_bus": (i + 1) * 10,
                "ckt": "1",
                "P_from": p_from,
                "Q_from": rng.uniform(-50, 50),
                "P_to": p_to,
                "Q_to": rng.uniform(-50, 50),
            }
        )

    output = tmp_path / "branches_acpf.csv"
    write_branches_csv(branch_results, output)

    with open(output, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 30

    # Verify header
    with open(output, encoding="utf-8") as f:
        header = f.readline().strip()
    assert header == "from_bus,to_bus,ckt,P_from,Q_from,P_to,Q_to"

    # Verify positive losses (P_from + P_to > 0) for all branches
    for row in rows:
        p_from = float(row["P_from"])
        p_to = float(row["P_to"])
        assert p_from + p_to > 0, f"Negative losses: P_from={p_from}, P_to={p_to}"


def test_write_generators_csv_schema(tmp_path: Path) -> None:
    """T10: generators_acpf.csv has correct schema."""
    rng = random.Random(42)
    gen_results = [
        {
            "bus": (i + 3) * 10,
            "machine_id": str(i % 3 + 1),
            "P": rng.uniform(10, 500),
            "Q": rng.uniform(-100, 200),
        }
        for i in range(1, 16)
    ]

    output = tmp_path / "generators_acpf.csv"
    write_generators_csv(gen_results, output)

    with open(output, encoding="utf-8") as f:
        header = f.readline().strip()
    assert header == "bus,machine_id,P,Q"

    with open(output, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 15


# ===========================================================================
# T11-T12: Summary JSON
# ===========================================================================


def test_write_summary_json_extracted_path(tmp_path: Path) -> None:
    """T11: summary_acpf.json for extracted path has correct structure."""
    summary = SystemSummary(
        total_gen_mw=50000.0,
        total_gen_mvar=12000.0,
        total_load_mw=48000.0,
        total_load_mvar=11000.0,
        total_loss_mw=2000.0,
        total_loss_mvar=1000.0,
        slack_bus=100,
        power_balance_residual_mw=0.0,
    )
    counts = {
        "buses_total": 30000,
        "buses_excluded_isolated": 50,
        "buses_excluded_deenergized": 10,
        "buses_in_output": 29940,
        "branches_in_output": 35000,
        "generators_in_output": 2000,
    }

    output = tmp_path / "summary_acpf.json"
    write_summary_json(
        source=SolutionSource.EXTRACTED,
        classification="solved",
        canonical_parser="matpower",
        settings=SolverSettings(),
        convergence=None,
        summary=summary,
        counts=counts,
        warnings=[],
        output_path=output,
    )

    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["solution_source"] == "extracted"
    assert data["solver"]["name"] is None
    assert data["solver"]["convergence"]["converged"] is None
    assert isinstance(data["system_summary"]["total_gen_mw"], float)
    assert isinstance(data["system_summary"]["total_gen_mvar"], float)
    assert isinstance(data["system_summary"]["total_load_mw"], float)
    assert isinstance(data["system_summary"]["total_load_mvar"], float)
    assert isinstance(data["system_summary"]["total_loss_mw"], float)
    assert isinstance(data["system_summary"]["total_loss_mvar"], float)
    assert isinstance(data["system_summary"]["slack_bus"], int)
    assert isinstance(data["system_summary"]["power_balance_residual_mw"], float)

    # Verify timestamp is a valid ISO 8601 string
    from datetime import datetime

    datetime.fromisoformat(data["timestamp"])


def test_write_summary_json_computed_path(tmp_path: Path) -> None:
    """T12: summary_acpf.json for computed path has solver fields populated."""
    summary = SystemSummary(
        total_gen_mw=50000.0,
        total_gen_mvar=12000.0,
        total_load_mw=48000.0,
        total_load_mvar=11000.0,
        total_loss_mw=2000.0,
        total_loss_mvar=1000.0,
        slack_bus=100,
        power_balance_residual_mw=0.0,
    )
    counts = {
        "buses_total": 30000,
        "buses_excluded_isolated": 50,
        "buses_excluded_deenergized": 10,
        "buses_in_output": 29940,
        "branches_in_output": 35000,
        "generators_in_output": 2000,
    }
    settings = SolverSettings(
        name="runpf",
        version="8.0",
        tolerance=1e-8,
        max_iterations=100,
        q_limits_enforced=True,
        q_limit_strategy="two_stage_relaxed_then_enforced",
        enforce_area_interchange=False,
    )
    convergence = ConvergenceInfo(
        converged=True,
        iterations=12,
        final_mismatch_mw=0.0001,
        final_mismatch_mvar=0.0002,
    )

    output = tmp_path / "summary_acpf.json"
    write_summary_json(
        source=SolutionSource.COMPUTED,
        classification="flat_start",
        canonical_parser="matpower",
        settings=settings,
        convergence=convergence,
        summary=summary,
        counts=counts,
        warnings=[],
        output_path=output,
    )

    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["solution_source"] == "computed"
    assert data["solver"]["name"] == "runpf"
    assert data["solver"]["settings"]["tolerance"] == 1e-8
    assert data["solver"]["convergence"]["converged"] is True
    assert data["solver"]["convergence"]["iterations"] == 12
    assert isinstance(data["solver"]["convergence"]["iterations"], int)
    assert data["solver"]["convergence"]["iterations"] > 0


# ===========================================================================
# T13-T14: System summary
# ===========================================================================


def _create_balanced_test_data(
    tmp_path: Path,
    total_gen_mw: float = 1000.0,
    total_load_mw: float = 950.0,
    total_loss_mw: float = 50.0,
    n_branches: int = 10,
    n_generators: int = 5,
) -> tuple[list[dict], list[dict], list[dict], Path]:
    """Create test data with specific power balance."""
    # Bus CSV with load and a slack bus
    bus_csv = tmp_path / "bus.csv"
    with open(bus_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "bus_i",
                "type",
                "Pd",
                "Qd",
                "Gs",
                "Bs",
                "area",
                "Vm",
                "Va",
                "baseKV",
                "zone",
                "Vmax",
                "Vmin",
            ]
        )
        load_per_bus = total_load_mw / 10
        for i in range(1, 11):
            bus_type = 3 if i == 1 else 1
            writer.writerow(
                [
                    str(i),
                    str(bus_type),
                    f"{load_per_bus:.4f}",
                    "10.0",
                    "0",
                    "0",
                    "1",
                    "1.0",
                    "0.0",
                    "138",
                    "1",
                    "1.1",
                    "0.9",
                ]
            )

    # Bus results
    bus_results = [{"bus": i, "VM": 1.0, "VA": 0.0} for i in range(1, 11)]

    # Generator results
    gen_per = total_gen_mw / n_generators
    gen_results = [
        {"bus": 1, "machine_id": str(i), "P": gen_per, "Q": 50.0}
        for i in range(1, n_generators + 1)
    ]

    # Branch results with specified total losses
    loss_per_branch = total_loss_mw / n_branches
    branch_results = []
    for i in range(1, n_branches + 1):
        p_from = 100.0
        p_to = -(100.0 - loss_per_branch)
        branch_results.append(
            {
                "from_bus": i,
                "to_bus": i + 1 if i < 10 else 1,
                "ckt": "1",
                "P_from": p_from,
                "Q_from": 10.0,
                "P_to": p_to,
                "Q_to": -8.0,
            }
        )

    return bus_results, branch_results, gen_results, bus_csv


def test_compute_system_summary_balanced(tmp_path: Path) -> None:
    """T13: System summary with balanced power."""
    bus_results, branch_results, gen_results, bus_csv = _create_balanced_test_data(
        tmp_path,
        total_gen_mw=1000.0,
        total_load_mw=950.0,
        total_loss_mw=50.0,
    )

    summary = compute_system_summary(bus_results, branch_results, gen_results, bus_csv)

    assert abs(summary.total_loss_mw - 50.0) < 0.1
    assert abs(summary.power_balance_residual_mw) < 0.1


def test_compute_system_summary_warns_on_imbalance(tmp_path: Path) -> None:
    """T14: System summary correctly computes residual for imbalanced data."""
    bus_results, branch_results, gen_results, bus_csv = _create_balanced_test_data(
        tmp_path,
        total_gen_mw=1000.0,
        total_load_mw=945.0,
        total_loss_mw=50.0,
    )

    summary = compute_system_summary(bus_results, branch_results, gen_results, bus_csv)

    # residual = gen - load - losses = 1000 - 945 - 50 = 5
    assert abs(summary.power_balance_residual_mw - 5.0) < 0.1


# ===========================================================================
# T15-T16: Integration tests (require FNM_PATH and D6/D8 outputs)
# ===========================================================================


@pytest.mark.fnm
def test_fnm_acpf_reference_produces_all_files(tmp_path: Path, require_fnm: object) -> None:
    """T15: build_acpf_reference produces all four output files with real FNM data."""
    intermediate_dir = Path("data/fnm/intermediate/canonical")
    snapshot_json = Path("data/fnm/intermediate/snapshot/snapshot_confirmation.json")

    if not intermediate_dir.is_dir() or not snapshot_json.exists():
        pytest.skip("D6/D8 intermediate outputs not available")

    output_dir = tmp_path / "acpf"
    result_dir = build_acpf_reference(
        intermediate_dir=intermediate_dir,
        snapshot_json_path=snapshot_json,
        canonical_parser="matpower",
        output_dir=output_dir,
    )

    # All four output files must exist
    assert (result_dir / "buses_acpf.csv").exists()
    assert (result_dir / "branches_acpf.csv").exists()
    assert (result_dir / "generators_acpf.csv").exists()
    assert (result_dir / "summary_acpf.json").exists()

    # Bus CSV should have >20,000 rows for a 30K network
    with open(result_dir / "buses_acpf.csv", encoding="utf-8") as f:
        bus_rows = sum(1 for _ in f) - 1  # subtract header
    assert bus_rows > 20000, f"Expected >20K bus rows, got {bus_rows}"

    # Branch CSV should have >30,000 rows
    with open(result_dir / "branches_acpf.csv", encoding="utf-8") as f:
        branch_rows = sum(1 for _ in f) - 1
    assert branch_rows > 30000, f"Expected >30K branch rows, got {branch_rows}"

    # Generator CSV should have >1,000 rows
    with open(result_dir / "generators_acpf.csv", encoding="utf-8") as f:
        gen_rows = sum(1 for _ in f) - 1
    assert gen_rows > 1000, f"Expected >1K generator rows, got {gen_rows}"

    # Summary JSON solution_source should match classification
    summary = json.loads((result_dir / "summary_acpf.json").read_text(encoding="utf-8"))
    classification = summary["snapshot_classification"]
    if classification == "solved":
        assert summary["solution_source"] == "extracted"
    else:
        assert summary["solution_source"] == "computed"

    # Log key stats for manual review
    print("\n--- ACPF Reference Summary ---")
    print(f"  Buses: {bus_rows}")
    print(f"  Branches: {branch_rows}")
    print(f"  Generators: {gen_rows}")
    print(f"  Solution source: {summary['solution_source']}")
    print(f"  Total gen MW: {summary['system_summary']['total_gen_mw']:.1f}")
    print(f"  Total load MW: {summary['system_summary']['total_load_mw']:.1f}")
    print(f"  Total loss MW: {summary['system_summary']['total_loss_mw']:.1f}")
    print(f"  Balance residual MW: {summary['system_summary']['power_balance_residual_mw']:.4f}")


@pytest.mark.fnm
def test_fnm_acpf_reference_power_balance(tmp_path: Path, require_fnm: object) -> None:
    """T16: ACPF reference power balance is within tolerance."""
    intermediate_dir = Path("data/fnm/intermediate/canonical")
    snapshot_json = Path("data/fnm/intermediate/snapshot/snapshot_confirmation.json")

    if not intermediate_dir.is_dir() or not snapshot_json.exists():
        pytest.skip("D6/D8 intermediate outputs not available")

    output_dir = tmp_path / "acpf"
    build_acpf_reference(
        intermediate_dir=intermediate_dir,
        snapshot_json_path=snapshot_json,
        canonical_parser="matpower",
        output_dir=output_dir,
    )

    summary = json.loads((output_dir / "summary_acpf.json").read_text(encoding="utf-8"))
    ss = summary["system_summary"]

    # Power balance residual < 1 MW
    assert abs(ss["power_balance_residual_mw"]) < 1.0, (
        f"Power balance residual {ss['power_balance_residual_mw']:.4f} MW exceeds 1.0 MW"
    )

    # Generation must exceed load (to cover losses)
    assert ss["total_gen_mw"] > ss["total_load_mw"], (
        f"Generation {ss['total_gen_mw']:.1f} MW <= Load {ss['total_load_mw']:.1f} MW"
    )

    # Losses must be positive
    assert ss["total_loss_mw"] > 0, f"Losses {ss['total_loss_mw']:.1f} MW <= 0"

    # Losses < 10% of generation
    loss_pct = ss["total_loss_mw"] / ss["total_gen_mw"]
    assert loss_pct < 0.10, f"Losses {loss_pct:.2%} of generation exceeds 10% threshold"
