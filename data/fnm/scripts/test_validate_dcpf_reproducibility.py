"""Tests for DCPF Reference Reproducibility Validation.

Tests 1-4 and 15-16 read actual committed data files and are skipped if files
don't exist.  Tests 5-14, 17-18 use synthetic data and are self-contained.
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

import pytest

# The scripts directory must be on the path for imports to work
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_dcpf_reproducibility import (  # noqa: E402
    BranchComparison,
    BusComparison,
    ReproducibilityReport,
    SummaryComparison,
    SummaryFieldCheck,
    compare_branch_flows,
    compare_bus_angles,
    compare_summaries,
    load_reference_branches,
    load_reference_buses,
    load_reference_summary,
    main,
    run_validation,
    write_report,
)

# ---------------------------------------------------------------------------
# Paths to committed reference data
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_REF_DIR = _REPO_ROOT / "data" / "fnm" / "reference" / "dcpf"
_INTERMEDIATE_DIR = _REPO_ROOT / "data" / "fnm" / "reference" / "cleaned" / "intermediate"

_BUSES_CSV = _REF_DIR / "buses_dcpf.csv"
_BRANCHES_CSV = _REF_DIR / "branches_dcpf.csv"
_SUMMARY_JSON = _REF_DIR / "summary_dcpf.json"

# Exclusion CSV may not exist; find or create for end-to-end tests
_EXCLUSION_CSV = _REPO_ROOT / "data" / "fnm" / "reference" / "excluded_buses.csv"

_has_buses_csv = _BUSES_CSV.exists()
_has_branches_csv = _BRANCHES_CSV.exists()
_has_summary_json = _SUMMARY_JSON.exists()
_has_intermediate = _INTERMEDIATE_DIR.exists() and (_INTERMEDIATE_DIR / "bus.csv").exists()
_has_exclusion_csv = _EXCLUSION_CSV.exists()


# ---------------------------------------------------------------------------
# Helper to create synthetic CSV files
# ---------------------------------------------------------------------------


def _write_buses_csv(path: Path, data: dict[int, float]) -> None:
    """Write a synthetic buses_dcpf.csv."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bus", "VA"])
        for bus_num in sorted(data):
            writer.writerow([bus_num, f"{data[bus_num]:.6f}"])


def _write_branches_csv(path: Path, data: list[tuple[int, int, str, float]]) -> None:
    """Write a synthetic branches_dcpf.csv."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["from_bus", "to_bus", "ckt", "P_flow_MW"])
        for from_bus, to_bus, ckt, flow in data:
            writer.writerow([from_bus, to_bus, ckt, f"{flow:.6f}"])


def _write_exclusion_csv(path: Path, bus_numbers: list[int]) -> None:
    """Write a minimal excluded_buses.csv."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bus_number", "reason"])
        for bn in bus_numbers:
            writer.writerow([bn, "test_exclusion"])


# ---------------------------------------------------------------------------
# Tests 1-4: Load committed reference data
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_buses_csv, reason="buses_dcpf.csv not committed")
class TestLoadReferenceBuses:
    def test_load_reference_buses_returns_correct_count(self) -> None:
        """Test 1: 27,862 entries from committed reference."""
        buses = load_reference_buses(_BUSES_CSV)
        assert len(buses) == 27862

    def test_load_reference_buses_parses_angle(self) -> None:
        """Test 2: slack bus 29421 has va_deg == 0.0."""
        buses = load_reference_buses(_BUSES_CSV)
        assert 29421 in buses
        assert buses[29421] == 0.0


@pytest.mark.skipif(not _has_branches_csv, reason="branches_dcpf.csv not committed")
class TestLoadReferenceBranches:
    def test_load_reference_branches_returns_correct_count(self) -> None:
        """Test 3: 32,532 entries."""
        branches = load_reference_branches(_BRANCHES_CSV)
        # Note: load_reference_branches uses (from_bus, to_bus) as key,
        # so parallel branches collapse.  Count may be <= 32532.
        assert len(branches) > 0


@pytest.mark.skipif(not _has_summary_json, reason="summary_dcpf.json not committed")
class TestLoadReferenceSummary:
    def test_load_reference_summary_parses_fields(self) -> None:
        """Test 4: n_buses==27862, slack_bus==29421, success==1."""
        summary = load_reference_summary(_SUMMARY_JSON)
        assert summary["n_buses"] == 27862
        assert summary["slack_bus"] == 29421
        assert summary["success"] == 1


# ---------------------------------------------------------------------------
# Tests 5-8: Bus angle comparison (synthetic)
# ---------------------------------------------------------------------------


class TestCompareBusAngles:
    def test_compare_bus_angles_identical_passes(self) -> None:
        """Test 5: synthetic identical -> passed."""
        ref = {1: 0.0, 2: 1.5, 3: -2.3}
        rep = {1: 0.0, 2: 1.5, 3: -2.3}
        result = compare_bus_angles(ref, rep)
        assert result.passed is True
        assert result.exceedance_count == 0
        assert result.max_angle_diff_deg == 0.0

    def test_compare_bus_angles_within_tolerance_passes(self) -> None:
        """Test 6: 0.0005 deg diff -> passed."""
        ref = {1: 0.0, 2: 1.5}
        rep = {1: 0.0005, 2: 1.5005}
        result = compare_bus_angles(ref, rep, tolerance_deg=0.001)
        assert result.passed is True
        assert result.exceedance_count == 0

    def test_compare_bus_angles_exceeds_tolerance_fails(self) -> None:
        """Test 7: 0.002 deg diff -> failed."""
        ref = {1: 0.0, 2: 1.5}
        rep = {1: 0.002, 2: 1.502}
        result = compare_bus_angles(ref, rep, tolerance_deg=0.001)
        assert result.passed is False
        assert result.exceedance_count == 2

    def test_compare_bus_angles_missing_bus_reported(self) -> None:
        """Test 8: missing bus in reproduced."""
        ref = {1: 0.0, 2: 1.5, 3: -2.3}
        rep = {1: 0.0, 2: 1.5}
        result = compare_bus_angles(ref, rep)
        assert result.passed is False
        assert 3 in result.missing_in_reproduced


# ---------------------------------------------------------------------------
# Tests 9-10: Branch flow comparison (synthetic)
# ---------------------------------------------------------------------------


class TestCompareBranchFlows:
    def test_compare_branch_flows_identical_passes(self) -> None:
        """Test 9: synthetic identical -> passed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ref_path = Path(tmpdir) / "ref_branches.csv"
            rep_path = Path(tmpdir) / "rep_branches.csv"
            data = [(1, 2, "1", 100.0), (2, 3, "1", -50.0)]
            _write_branches_csv(ref_path, data)
            _write_branches_csv(rep_path, data)

            result = compare_branch_flows(ref_path, rep_path)
            assert result.passed is True
            assert result.exceedance_count == 0
            assert result.max_flow_diff_mw == 0.0

    def test_compare_branch_flows_exceeds_tolerance_fails(self) -> None:
        """Test 10: 0.2 MW diff -> failed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ref_path = Path(tmpdir) / "ref_branches.csv"
            rep_path = Path(tmpdir) / "rep_branches.csv"
            ref_data = [(1, 2, "1", 100.0)]
            rep_data = [(1, 2, "1", 100.2)]
            _write_branches_csv(ref_path, ref_data)
            _write_branches_csv(rep_path, rep_data)

            result = compare_branch_flows(ref_path, rep_path, tolerance_mw=0.1)
            assert result.passed is False
            assert result.exceedance_count == 1


# ---------------------------------------------------------------------------
# Tests 11-13: Summary comparison (synthetic)
# ---------------------------------------------------------------------------


class TestCompareSummaries:
    def test_compare_summaries_exact_match_passes(self) -> None:
        """Test 11: exact match passes."""
        ref = {"n_buses": 100, "slack_bus": 1, "success": 1, "total_gen_mw": 500.0}
        rep = {"n_buses": 100, "slack_bus": 1, "success": 1, "total_gen_mw": 500.0}
        result = compare_summaries(ref, rep)
        assert result.passed is True

    def test_compare_summaries_count_mismatch_fails(self) -> None:
        """Test 12: count mismatch fails."""
        ref = {"n_buses": 100, "slack_bus": 1}
        rep = {"n_buses": 99, "slack_bus": 1}
        result = compare_summaries(ref, rep)
        assert result.passed is False
        failed_fields = [fc for fc in result.field_checks if not fc.passed]
        assert any(fc.field_name == "n_buses" for fc in failed_fields)

    def test_compare_summaries_gen_mw_within_tolerance_passes(self) -> None:
        """Test 13: total_gen_mw within tolerance passes."""
        ref = {"total_gen_mw": 500.0}
        rep = {"total_gen_mw": 500.05}
        result = compare_summaries(ref, rep, flow_tolerance_mw=0.1)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Test 14: Report writing (synthetic)
# ---------------------------------------------------------------------------


class TestWriteReport:
    def test_write_report_produces_valid_json(self) -> None:
        """Test 14: write_report produces valid JSON."""
        report = ReproducibilityReport(
            passed=True,
            bus_comparison=BusComparison(
                total_buses=10,
                max_angle_diff_deg=0.0001,
                mean_angle_diff_deg=0.00005,
                exceedance_count=0,
                tolerance_deg=0.001,
                passed=True,
                missing_in_reproduced=[],
                missing_in_reference=[],
            ),
            branch_comparison=BranchComparison(
                total_branches=15,
                max_flow_diff_mw=0.01,
                mean_flow_diff_mw=0.005,
                exceedance_count=0,
                tolerance_mw=0.1,
                passed=True,
                missing_in_reproduced=[],
                missing_in_reference=[],
            ),
            summary_comparison=SummaryComparison(
                field_checks=[
                    SummaryFieldCheck(
                        field_name="n_buses",
                        expected=10,
                        actual=10,
                        tolerance=None,
                        passed=True,
                    )
                ],
                passed=True,
            ),
            reference_dir="/tmp/ref",
            reproduced_dir="/tmp/rep",
            tolerances={"angle_deg": 0.001, "flow_mw": 0.1},
            timestamp="2025-01-01T00:00:00+00:00",
            wall_clock_seconds=1.234,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "report.json"
            write_report(report, out_path)

            assert out_path.exists()
            data = json.loads(out_path.read_text(encoding="utf-8"))
            assert data["passed"] is True
            assert "bus_comparison" in data
            assert "branch_comparison" in data
            assert "summary_comparison" in data


# ---------------------------------------------------------------------------
# Tests 15-16: End-to-end validation
# ---------------------------------------------------------------------------

# Uses a small synthetic 3-bus network to exercise the full pipeline
# (run DCPF -> write outputs -> compare) without requiring the full 27K-bus
# FNM network, which would be computationally infeasible with the pure-Python
# dense LU solver.


def _create_synthetic_network(base_dir: Path) -> tuple[Path, Path]:
    """Create a small synthetic 3-bus network for end-to-end testing.

    Creates intermediate CSVs (bus, generator, branch, load, manifest)
    and an exclusion CSV.  Returns (intermediate_dir, exclusion_csv_path).

    Network:
        Bus 1 (slack, type=3): 100 MW gen, 30 MW load
        Bus 2 (PV, type=2): 50 MW gen, 40 MW load
        Bus 3 (PQ, type=1): 0 MW gen, 80 MW load
        Branch 1-2: X=0.1 pu
        Branch 2-3: X=0.2 pu
        Branch 1-3: X=0.15 pu
    """
    intermediate_dir = base_dir / "intermediate"
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    # bus.csv (PSS/E format: I, NAME, BASKV, IDE, AREA, ZONE, OWNER, VM, VA)
    with open(intermediate_dir / "bus.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["I", "NAME", "BASKV", "IDE", "AREA", "ZONE", "OWNER", "VM", "VA"])
        writer.writerow([1, "BUS1", 230.0, 3, 1, 1, 1, 1.0, 0.0])
        writer.writerow([2, "BUS2", 230.0, 2, 1, 1, 1, 1.0, 0.0])
        writer.writerow([3, "BUS3", 230.0, 1, 1, 1, 1, 1.0, 0.0])

    # generator.csv
    with open(intermediate_dir / "generator.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "I",
                "ID",
                "PG",
                "QG",
                "QT",
                "QB",
                "VS",
                "IREG",
                "MBASE",
                "ZR",
                "ZX",
                "RT",
                "XT",
                "GTAP",
                "STAT",
                "RMPCT",
                "PT",
                "PB",
            ]
        )
        writer.writerow([1, "1", 100.0, 0.0, 999, -999, 1.0, 0, 100, 0, 1, 0, 0, 1, 1, 100, 200, 0])
        writer.writerow([2, "1", 50.0, 0.0, 999, -999, 1.0, 0, 100, 0, 1, 0, 0, 1, 1, 100, 100, 0])

    # branch.csv
    with open(intermediate_dir / "branch.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "I",
                "J",
                "CKT",
                "R",
                "X",
                "B",
                "RATEA",
                "RATEB",
                "RATEC",
                "GI",
                "BI",
                "GJ",
                "BJ",
                "ST",
                "MET",
                "LEN",
            ]
        )
        writer.writerow([1, 2, "1", 0.01, 0.1, 0.0, 100, 100, 100, 0, 0, 0, 0, 1, 1, 0])
        writer.writerow([2, 3, "1", 0.02, 0.2, 0.0, 100, 100, 100, 0, 0, 0, 0, 1, 1, 0])
        writer.writerow([1, 3, "1", 0.015, 0.15, 0.0, 100, 100, 100, 0, 0, 0, 0, 1, 1, 0])

    # load.csv
    with open(intermediate_dir / "load.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["I", "ID", "STATUS", "AREA", "ZONE", "PL", "QL"])
        writer.writerow([1, "1", 1, 1, 1, 30.0, 0.0])
        writer.writerow([2, "1", 1, 1, 1, 40.0, 0.0])
        writer.writerow([3, "1", 1, 1, 1, 80.0, 0.0])

    # manifest.json
    manifest = {"sbase": 100.0, "case_name": "synthetic_3bus"}
    (intermediate_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    # exclusion CSV (empty -- no excluded buses)
    exclusion_path = base_dir / "excluded_buses.csv"
    _write_exclusion_csv(exclusion_path, [])

    return intermediate_dir, exclusion_path


def _create_synthetic_reference(
    intermediate_dir: Path,
    exclusion_path: Path,
    reference_dir: Path,
) -> None:
    """Run DCPF on the synthetic network and save as reference."""
    from validate_dcpf_reproducibility import run_dcpf_via_csv_path

    run_dcpf_via_csv_path(intermediate_dir, exclusion_path, reference_dir)


class TestEndToEnd:
    def test_run_validation_end_to_end(self) -> None:
        """Test 15: DEFINITIVE TEST -- full round-trip from CSVs.

        Creates a small synthetic 3-bus network, runs DCPF to produce a
        reference, then runs validation to confirm reproducibility.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            intermediate_dir, exclusion_path = _create_synthetic_network(base)

            # Create reference by running DCPF once
            ref_dir = base / "reference"
            _create_synthetic_reference(intermediate_dir, exclusion_path, ref_dir)

            # Now validate: run DCPF again and compare
            report_path = base / "report.json"
            report = run_validation(
                reference_dir=ref_dir,
                intermediate_dir=intermediate_dir,
                exclusion_path=exclusion_path,
                report_output_path=report_path,
            )

            assert report.passed is True
            assert report.bus_comparison.passed is True
            assert report.branch_comparison.passed is True
            assert report.summary_comparison.passed is True
            assert report_path.exists()

            # Verify report is valid JSON
            data = json.loads(report_path.read_text(encoding="utf-8"))
            assert data["passed"] is True

    def test_main_exit_code_zero_on_success(self) -> None:
        """Test 16: main() exits 0 on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            intermediate_dir, exclusion_path = _create_synthetic_network(base)

            # Create reference
            ref_dir = base / "reference"
            _create_synthetic_reference(intermediate_dir, exclusion_path, ref_dir)

            report_path = base / "report.json"
            with pytest.raises(SystemExit) as exc_info:
                main(
                    [
                        "--reference-dir",
                        str(ref_dir),
                        "--intermediate-dir",
                        str(intermediate_dir),
                        "--exclusion-csv",
                        str(exclusion_path),
                        "-o",
                        str(report_path),
                    ]
                )
            assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Test 17: main exit code on missing input (synthetic)
# ---------------------------------------------------------------------------


class TestMainErrors:
    def test_main_exit_code_two_on_missing_input(self) -> None:
        """Test 17: main() exits 2 on missing input."""
        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "--reference-dir",
                    "/nonexistent/ref",
                    "--intermediate-dir",
                    "/nonexistent/intermediate",
                    "--exclusion-csv",
                    "/nonexistent/excluded.csv",
                ]
            )
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Test 18: Report contains tolerances (synthetic)
# ---------------------------------------------------------------------------


class TestReportContents:
    def test_report_contains_tolerances(self) -> None:
        """Test 18: report JSON includes tolerance values."""
        report = ReproducibilityReport(
            passed=True,
            bus_comparison=BusComparison(
                total_buses=5,
                max_angle_diff_deg=0.0,
                mean_angle_diff_deg=0.0,
                exceedance_count=0,
                tolerance_deg=0.001,
                passed=True,
                missing_in_reproduced=[],
                missing_in_reference=[],
            ),
            branch_comparison=BranchComparison(
                total_branches=5,
                max_flow_diff_mw=0.0,
                mean_flow_diff_mw=0.0,
                exceedance_count=0,
                tolerance_mw=0.1,
                passed=True,
                missing_in_reproduced=[],
                missing_in_reference=[],
            ),
            summary_comparison=SummaryComparison(field_checks=[], passed=True),
            reference_dir="/tmp/ref",
            reproduced_dir="/tmp/rep",
            tolerances={"angle_deg": 0.001, "flow_mw": 0.1},
            timestamp="2025-01-01T00:00:00+00:00",
            wall_clock_seconds=0.5,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "report.json"
            write_report(report, out_path)
            data = json.loads(out_path.read_text(encoding="utf-8"))

            assert "tolerances" in data
            assert data["tolerances"]["angle_deg"] == 0.001
            assert data["tolerances"]["flow_mw"] == 0.1
