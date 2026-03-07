"""Tests for DCPF-vs-ACPF Characterization (PRD 03/04).

Tests T01-T12 are synthetic (no FNM data required).
Tests T13-T14 require FNM_PATH and D2/D3 outputs.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from fnm.scripts.dcpf_acpf_characterization import (
    AggregateStats,
    BranchDeviation,
    BusDeviation,
    CharacterizationResult,
    ComplianceFractions,
    DeviationCause,
    annotate_branch_causes,
    annotate_bus_causes,
    build_characterization,
    compute_aggregate_stats,
    compute_branch_deviations,
    compute_bus_deviations,
    compute_compliance_fractions,
    join_branches,
    join_buses,
    write_characterization_json,
)

# ---------------------------------------------------------------------------
# Helpers for writing synthetic CSV/JSON files
# ---------------------------------------------------------------------------


def _write_acpf_bus_csv(path: Path, rows: list[dict]) -> None:
    """Write a synthetic buses_acpf.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bus", "VM", "VA"])
        for r in rows:
            writer.writerow([r["bus"], r.get("VM", 1.0), r["VA"]])


def _write_dcpf_bus_csv(path: Path, rows: list[dict]) -> None:
    """Write a synthetic buses_dcpf.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bus", "VA"])
        for r in rows:
            writer.writerow([r["bus"], r["VA"]])


def _write_acpf_branch_csv(path: Path, rows: list[dict]) -> None:
    """Write a synthetic branches_acpf.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["from_bus", "to_bus", "ckt", "P_from", "Q_from", "P_to", "Q_to"])
        for r in rows:
            writer.writerow(
                [
                    r["from_bus"],
                    r["to_bus"],
                    r["ckt"],
                    r.get("P_from", 0),
                    r.get("Q_from", 0),
                    r.get("P_to", 0),
                    r.get("Q_to", 0),
                ]
            )


def _write_dcpf_branch_csv(path: Path, rows: list[dict]) -> None:
    """Write a synthetic branches_dcpf.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["from_bus", "to_bus", "ckt", "P_flow_MW"])
        for r in rows:
            writer.writerow([r["from_bus"], r["to_bus"], r["ckt"], r["P_flow_MW"]])


def _write_summary_json(path: Path, data: dict) -> None:
    """Write a synthetic summary JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_intermediate_bus_csv(path: Path, rows: list[dict]) -> None:
    """Write a synthetic intermediate format bus CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bus_i", "base_kv", "area", "type"])
        for r in rows:
            writer.writerow(
                [
                    r.get("bus", r.get("bus_i", 0)),
                    r.get("base_kv", 0),
                    r.get("area", 0),
                    r.get("type", 1),
                ]
            )


def _write_intermediate_branch_csv(path: Path, rows: list[dict]) -> None:
    """Write a synthetic intermediate format branch CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["f_bus", "t_bus", "br_x", "tap", "shift", "br_status", "ckt", "rate_a"])
        for r in rows:
            writer.writerow(
                [
                    r.get("from_bus", 0),
                    r.get("to_bus", 0),
                    r.get("x_pu", r.get("br_x", 0.01)),
                    r.get("tap_ratio", r.get("tap", 0)),
                    r.get("shift_deg", r.get("shift", 0)),
                    r.get("status", r.get("br_status", 1)),
                    r.get("ckt", "1"),
                    r.get("rate_a", ""),
                ]
            )


def _make_acpf_summary(slack_bus: int = 1) -> dict:
    """Create a minimal ACPF summary JSON dict."""
    return {
        "system_summary": {
            "total_gen_mw": 1000.0,
            "total_load_mw": 950.0,
            "total_loss_mw": 50.0,
            "slack_bus": slack_bus,
        },
    }


def _make_dcpf_summary(slack_bus: int = 1) -> dict:
    """Create a minimal DCPF summary JSON dict."""
    return {
        "settings": {
            "slack_bus": slack_bus,
        },
        "power_summary": {
            "total_generation_mw": 950.0,
            "total_load_mw": 950.0,
        },
    }


def _setup_synthetic_characterization(
    tmp_path: Path,
    *,
    acpf_buses: list[dict] | None = None,
    dcpf_buses: list[dict] | None = None,
    acpf_branches: list[dict] | None = None,
    dcpf_branches: list[dict] | None = None,
    intermediate_buses: list[dict] | None = None,
    intermediate_branches: list[dict] | None = None,
    slack_bus: int = 1,
) -> tuple[Path, Path, Path, Path]:
    """Set up synthetic data for build_characterization.

    Returns:
        (acpf_dir, dcpf_dir, intermediate_dir, output_dir)
    """
    acpf_dir = tmp_path / "acpf"
    dcpf_dir = tmp_path / "dcpf"
    int_dir = tmp_path / "intermediate"
    out_dir = tmp_path / "output"

    # Default buses: 25 matched buses with small deviations
    if acpf_buses is None:
        acpf_buses = [{"bus": i, "VM": 1.0, "VA": float(i)} for i in range(1, 26)]
    if dcpf_buses is None:
        dcpf_buses = [{"bus": i, "VA": float(i) + 0.5} for i in range(1, 26)]

    # Default branches: 35 matched branches
    if acpf_branches is None:
        acpf_branches = [
            {
                "from_bus": i,
                "to_bus": i + 1,
                "ckt": "1",
                "P_from": float(50 + i),
                "Q_from": 10.0,
                "P_to": float(-49 - i),
                "Q_to": -9.0,
            }
            for i in range(1, 36)
        ]
    if dcpf_branches is None:
        dcpf_branches = [
            {"from_bus": i, "to_bus": i + 1, "ckt": "1", "P_flow_MW": float(52 + i)}
            for i in range(1, 36)
        ]

    # Default intermediate buses
    if intermediate_buses is None:
        intermediate_buses = [
            {"bus_i": i, "base_kv": 230.0, "area": 1, "type": 3 if i == slack_bus else 1}
            for i in range(1, 40)
        ]

    # Default intermediate branches
    if intermediate_branches is None:
        intermediate_branches = [
            {
                "from_bus": i,
                "to_bus": i + 1,
                "br_x": 0.01,
                "tap": 0,
                "shift": 0,
                "br_status": 1,
                "ckt": "1",
                "rate_a": 500,
            }
            for i in range(1, 40)
        ]

    _write_acpf_bus_csv(acpf_dir / "buses_acpf.csv", acpf_buses)
    _write_dcpf_bus_csv(dcpf_dir / "buses_dcpf.csv", dcpf_buses)
    _write_acpf_branch_csv(acpf_dir / "branches_acpf.csv", acpf_branches)
    _write_dcpf_branch_csv(dcpf_dir / "branches_dcpf.csv", dcpf_branches)
    _write_summary_json(acpf_dir / "summary_acpf.json", _make_acpf_summary(slack_bus))
    _write_summary_json(dcpf_dir / "summary_dcpf.json", _make_dcpf_summary(slack_bus))
    _write_intermediate_bus_csv(int_dir / "bus.csv", intermediate_buses)
    _write_intermediate_branch_csv(int_dir / "branch.csv", intermediate_branches)

    return acpf_dir, dcpf_dir, int_dir, out_dir


# ---------------------------------------------------------------------------
# T01-T03: Join operation tests
# ---------------------------------------------------------------------------


class TestJoinBuses:
    """T01: test_join_buses_inner_join."""

    def test_join_buses_inner_join(self) -> None:
        """ACPF buses [1..5], DCPF buses [2..6] -> 4 matched (2-5)."""
        acpf = [{"bus": i, "VM": 1.0, "VA": float(i)} for i in range(1, 6)]
        dcpf = [{"bus": i, "VA": float(i) + 0.1} for i in range(2, 7)]

        matched, summary = join_buses(acpf, dcpf)

        assert len(matched) == 4
        matched_bus_nums = {m["bus"] for m in matched}
        assert matched_bus_nums == {2, 3, 4, 5}

        assert summary["buses_in_acpf"] == 5
        assert summary["buses_in_dcpf"] == 5
        assert summary["buses_matched"] == 4
        assert summary["buses_acpf_only"] == 1
        assert summary["buses_dcpf_only"] == 1


class TestJoinBranches:
    """T02: test_join_branches_composite_key."""

    def test_join_branches_composite_key(self) -> None:
        """Composite key (from_bus, to_bus, ckt) matching with parallel circuits."""
        acpf = [
            {"from_bus": 1, "to_bus": 2, "ckt": "1", "P_from": 100.0},
            {"from_bus": 1, "to_bus": 2, "ckt": "2", "P_from": 80.0},
            {"from_bus": 3, "to_bus": 4, "ckt": "1", "P_from": 50.0},
        ]
        dcpf = [
            {"from_bus": 1, "to_bus": 2, "ckt": "1", "P_flow_MW": 105.0},
            {"from_bus": 1, "to_bus": 2, "ckt": "2", "P_flow_MW": 82.0},
            {"from_bus": 5, "to_bus": 6, "ckt": "1", "P_flow_MW": 30.0},
        ]

        matched, summary = join_branches(acpf, dcpf)

        assert len(matched) == 2
        assert summary["branches_acpf_only"] == 1
        assert summary["branches_dcpf_only"] == 1


class TestJoinBusesEmptyIntersection:
    """T03: test_join_buses_empty_intersection_raises."""

    def test_join_buses_empty_intersection_raises(self, tmp_path: Path) -> None:
        """ACPF buses [1,2,3], DCPF buses [4,5,6] -> ValueError on zero match."""
        acpf_buses = [{"bus": i, "VM": 1.0, "VA": float(i)} for i in [1, 2, 3]]
        dcpf_buses = [{"bus": i, "VA": float(i)} for i in [4, 5, 6]]

        # Need branches that also won't match, but at least exist
        acpf_branches = [
            {
                "from_bus": 1,
                "to_bus": 2,
                "ckt": "1",
                "P_from": 100.0,
                "Q_from": 0,
                "P_to": -100,
                "Q_to": 0,
            }
            for _ in range(35)
        ]
        dcpf_branches = [
            {"from_bus": 4, "to_bus": 5, "ckt": "1", "P_flow_MW": 100.0} for _ in range(35)
        ]

        acpf_dir, dcpf_dir, int_dir, out_dir = _setup_synthetic_characterization(
            tmp_path,
            acpf_buses=acpf_buses,
            dcpf_buses=dcpf_buses,
            acpf_branches=acpf_branches,
            dcpf_branches=dcpf_branches,
        )

        with pytest.raises(ValueError, match="zero matched buses"):
            build_characterization(acpf_dir, dcpf_dir, int_dir, out_dir)


# ---------------------------------------------------------------------------
# T04-T06: Deviation computation tests
# ---------------------------------------------------------------------------


class TestBusDeviationSigns:
    """T04: test_bus_deviation_signs."""

    def test_bus_deviation_signs(self) -> None:
        """VA_acpf=10, VA_dcpf=12 -> delta=2; VA_acpf=-5, VA_dcpf=-7 -> delta=-2."""
        matched = [
            {"bus": 1, "VM_acpf": 1.0, "VA_acpf": 10.0, "VA_dcpf": 12.0},
            {"bus": 2, "VM_acpf": 1.0, "VA_acpf": -5.0, "VA_dcpf": -7.0},
        ]
        intermediate_buses: list[dict] = []

        devs = compute_bus_deviations(matched, intermediate_buses)

        assert len(devs) == 2
        # Bus 1: delta = 12 - 10 = 2.0
        assert devs[0].bus == 1
        assert math.isclose(devs[0].delta_VA_deg, 2.0)
        assert math.isclose(devs[0].abs_delta_VA_deg, 2.0)

        # Bus 2: delta = -7 - (-5) = -2.0
        assert devs[1].bus == 2
        assert math.isclose(devs[1].delta_VA_deg, -2.0)
        assert math.isclose(devs[1].abs_delta_VA_deg, 2.0)


class TestBranchDeviationNearZeroFlow:
    """T05: test_branch_deviation_near_zero_flow_excluded."""

    def test_branch_deviation_near_zero_flow_excluded(self) -> None:
        """Branch A (100 MW) gets pct; branch B (0.5 MW) gets None for pct."""
        matched = [
            {"from_bus": 1, "to_bus": 2, "ckt": "1", "P_from_acpf": 100.0, "P_flow_dcpf": 105.0},
            {"from_bus": 3, "to_bus": 4, "ckt": "1", "P_from_acpf": 0.5, "P_flow_dcpf": 1.0},
        ]
        intermediate_branches: list[dict] = []

        devs = compute_branch_deviations(matched, intermediate_branches)

        assert len(devs) == 2

        # Branch A: delta_P_pct = (105-100)/100 * 100 = 5%
        assert math.isclose(devs[0].delta_P_pct, 5.0)  # type: ignore[arg-type]
        assert math.isclose(devs[0].abs_delta_P_pct, 5.0)  # type: ignore[arg-type]

        # Branch B: near-zero flow -> None
        assert devs[1].delta_P_pct is None
        assert devs[1].abs_delta_P_pct is None


class TestBranchDeviationPercentageDirection:
    """T06: test_branch_deviation_percentage_direction."""

    def test_branch_deviation_percentage_direction(self) -> None:
        """P_from_acpf=-200, P_flow_dcpf=-180 -> delta_P_MW=20, delta_P_pct=10%."""
        matched = [
            {"from_bus": 1, "to_bus": 2, "ckt": "1", "P_from_acpf": -200.0, "P_flow_dcpf": -180.0},
        ]
        intermediate_branches: list[dict] = []

        devs = compute_branch_deviations(matched, intermediate_branches)

        assert len(devs) == 1
        bd = devs[0]

        # delta_P_MW = -180 - (-200) = 20.0
        assert math.isclose(bd.delta_P_MW, 20.0)
        assert math.isclose(bd.abs_delta_P_MW, 20.0)

        # delta_P_pct = 20 / 200 * 100 = 10.0
        assert bd.delta_P_pct is not None
        assert math.isclose(bd.delta_P_pct, 10.0)
        assert bd.abs_delta_P_pct is not None
        assert math.isclose(bd.abs_delta_P_pct, 10.0)


# ---------------------------------------------------------------------------
# T07-T09: Aggregate statistics and compliance tests
# ---------------------------------------------------------------------------


class TestAggregateStatsKnownDistribution:
    """T07: test_aggregate_stats_known_distribution."""

    def test_aggregate_stats_known_distribution(self) -> None:
        """90 values of 1.0 and 10 values of 5.0."""
        values = [1.0] * 90 + [5.0] * 10

        stats = compute_aggregate_stats(values)

        # mean = (90*1 + 10*5) / 100 = 140/100 = 1.4
        assert math.isclose(stats.mean, 1.4, rel_tol=1e-6)
        assert math.isclose(stats.median, 1.0)
        assert stats.max == 5.0
        # p95: at index 94.05 in sorted array (all 1.0 up to index 89, then 5.0)
        # So p95 should be 5.0
        assert math.isclose(stats.p95, 5.0)


class TestComplianceFractions:
    """T08: test_compliance_fractions_known_distribution."""

    def test_compliance_fractions_known_distribution(self) -> None:
        """90 values of 1.0, 10 values of 5.0 with thresholds [0.5, 1.0, 2.0, 5.0]."""
        values = [1.0] * 90 + [5.0] * 10

        comp = compute_compliance_fractions(values, [0.5, 1.0, 2.0, 5.0])

        assert len(comp.fractions) == 4
        # 0% below 0.5 (all values are >= 1.0)
        assert math.isclose(comp.fractions[0], 0.0)
        # 90% at or below 1.0
        assert math.isclose(comp.fractions[1], 0.90)
        # 90% at or below 2.0
        assert math.isclose(comp.fractions[2], 0.90)
        # 100% at or below 5.0
        assert math.isclose(comp.fractions[3], 1.0)


class TestExpectedRangeCheckWarning:
    """T09: test_expected_range_check_warning."""

    def test_expected_range_check_warning(self, tmp_path: Path) -> None:
        """93% within 3 degrees -> expected_range_checks.angle fails, warning emitted."""
        # Create 25 buses: 23 with small deviations, 2 with large deviations
        # 23/25 = 92% within 3 degrees
        acpf_buses = [{"bus": i, "VM": 1.0, "VA": 0.0} for i in range(1, 26)]
        dcpf_buses_data = []
        for i in range(1, 26):
            if i <= 23:
                dcpf_buses_data.append({"bus": i, "VA": 1.0})  # delta=1.0 deg
            else:
                dcpf_buses_data.append({"bus": i, "VA": 5.0})  # delta=5.0 deg

        # Branches: 35 with moderate deviations
        acpf_branches = [
            {
                "from_bus": i,
                "to_bus": i + 1,
                "ckt": "1",
                "P_from": 100.0,
                "Q_from": 10.0,
                "P_to": -99.0,
                "Q_to": -9.0,
            }
            for i in range(1, 36)
        ]
        dcpf_branches = [
            {"from_bus": i, "to_bus": i + 1, "ckt": "1", "P_flow_MW": 102.0} for i in range(1, 36)
        ]

        acpf_dir, dcpf_dir, int_dir, out_dir = _setup_synthetic_characterization(
            tmp_path,
            acpf_buses=acpf_buses,
            dcpf_buses=dcpf_buses_data,
            acpf_branches=acpf_branches,
            dcpf_branches=dcpf_branches,
        )

        result_dir = build_characterization(acpf_dir, dcpf_dir, int_dir, out_dir)

        # Read the JSON to verify
        json_path = result_dir / "dcpf_vs_acpf_characterization.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))

        angle_check = data["expected_range_checks"]["angle_95pct_within_3deg"]
        assert angle_check["met"] is False

        # Verify warnings mention the threshold
        assert any("95%" in w and "3 degrees" in w for w in data["warnings"])


# ---------------------------------------------------------------------------
# T10-T11: Cause annotation tests
# ---------------------------------------------------------------------------


class TestBranchCausePhaseShifter:
    """T10: test_branch_cause_phase_shifter."""

    def test_branch_cause_phase_shifter(self) -> None:
        """Branch with shift_deg=15 -> PHASE_SHIFTER cause."""
        branch_devs = [
            BranchDeviation(
                from_bus=1,
                to_bus=2,
                ckt="1",
                P_from_acpf_MW=100.0,
                P_flow_dcpf_MW=110.0,
                delta_P_MW=10.0,
                abs_delta_P_MW=10.0,
                delta_P_pct=10.0,
                abs_delta_P_pct=10.0,
                x_pu=0.05,
                tap_ratio=1.0,
                shift_deg=15.0,
                is_transformer=True,
            ),
        ]
        acpf_buses = [{"bus": 1, "VM": 1.0}, {"bus": 2, "VM": 1.0}]
        intermediate_branches: list[dict] = []

        result = annotate_branch_causes(branch_devs, acpf_buses, intermediate_branches)

        assert len(result) == 1
        assert DeviationCause.PHASE_SHIFTER in result[0].causes
        assert result[0].causes[0] == DeviationCause.PHASE_SHIFTER


class TestBusCauseLowVoltage:
    """T11: test_bus_cause_low_voltage."""

    def test_bus_cause_low_voltage(self) -> None:
        """Bus with VM_acpf=0.92 -> LOW_VOLTAGE cause."""
        bus_devs = [
            BusDeviation(
                bus=1,
                VA_acpf_deg=10.0,
                VA_dcpf_deg=12.0,
                delta_VA_deg=2.0,
                abs_delta_VA_deg=2.0,
                VM_acpf_pu=0.92,
                base_kv=115.0,
                area=1,
            ),
        ]

        result = annotate_bus_causes(bus_devs, slack_bus=999, bus_adjacency={})

        assert len(result) == 1
        assert DeviationCause.LOW_VOLTAGE in result[0].causes


# ---------------------------------------------------------------------------
# T12: Output format test
# ---------------------------------------------------------------------------


class TestWriteCharacterizationJsonRoundtrip:
    """T12: test_write_characterization_json_roundtrip."""

    def test_write_characterization_json_roundtrip(self, tmp_path: Path) -> None:
        """Build synthetic CharacterizationResult, write JSON, read back, verify keys."""
        # Create 20 bus deviations
        bus_devs = [
            BusDeviation(
                bus=i,
                VA_acpf_deg=float(i),
                VA_dcpf_deg=float(i) + 0.5,
                delta_VA_deg=0.5,
                abs_delta_VA_deg=0.5,
                VM_acpf_pu=1.0,
                base_kv=230.0,
                area=1,
                causes=[DeviationCause.UNCATEGORIZED],
            )
            for i in range(1, 21)
        ]

        # Create 30 branch deviations
        branch_devs = [
            BranchDeviation(
                from_bus=i,
                to_bus=i + 1,
                ckt="1",
                P_from_acpf_MW=100.0,
                P_flow_dcpf_MW=105.0,
                delta_P_MW=5.0,
                abs_delta_P_MW=5.0,
                delta_P_pct=5.0,
                abs_delta_P_pct=5.0,
                x_pu=0.01,
                tap_ratio=1.0,
                shift_deg=0.0,
                is_transformer=False,
                causes=[DeviationCause.UNCATEGORIZED],
            )
            for i in range(1, 31)
        ]

        angle_stats = AggregateStats(
            count=20,
            mean=0.5,
            median=0.5,
            std=0.0,
            min=0.5,
            max=0.5,
            p05=0.5,
            p95=0.5,
        )
        flow_stats = AggregateStats(
            count=30,
            mean=5.0,
            median=5.0,
            std=0.0,
            min=5.0,
            max=5.0,
            p05=5.0,
            p95=5.0,
        )
        angle_comp = ComplianceFractions(
            thresholds=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0],
            fractions=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        )
        flow_comp = ComplianceFractions(
            thresholds=[1.0, 2.0, 5.0, 10.0, 20.0, 50.0],
            fractions=[0.0, 0.0, 1.0, 1.0, 1.0, 1.0],
        )

        result = CharacterizationResult(
            bus_deviations=bus_devs,
            branch_deviations=branch_devs,
            angle_stats_signed=angle_stats,
            angle_stats_absolute=angle_stats,
            angle_compliance=angle_comp,
            flow_mw_stats_signed=flow_stats,
            flow_mw_stats_absolute=flow_stats,
            flow_pct_stats_signed=flow_stats,
            flow_pct_stats_absolute=flow_stats,
            flow_pct_compliance=flow_comp,
            join_summary={
                "buses_in_acpf": 20,
                "buses_in_dcpf": 20,
                "buses_matched": 20,
                "buses_acpf_only": 0,
                "buses_dcpf_only": 0,
                "branches_in_acpf": 30,
                "branches_in_dcpf": 30,
                "branches_matched": 30,
                "branches_acpf_only": 0,
                "branches_dcpf_only": 0,
            },
            system_level={
                "acpf_total_gen_mw": 1000.0,
                "dcpf_total_gen_mw": 950.0,
                "acpf_total_load_mw": 950.0,
                "dcpf_total_load_mw": 950.0,
                "acpf_total_loss_mw": 50.0,
                "acpf_loss_pct_of_gen": 5.0,
                "acpf_slack_bus": 1.0,
                "dcpf_slack_bus": 1.0,
            },
            expected_range_checks={
                "angle_95pct_within_3deg": {
                    "threshold_pct": 95.0,
                    "threshold_deg": 3.0,
                    "actual_pct": 100.0,
                    "met": True,
                },
                "flow_90pct_within_10pct": {
                    "threshold_pct": 90.0,
                    "threshold_flow_pct": 10.0,
                    "actual_pct": 100.0,
                    "met": True,
                },
            },
            worst_buses=bus_devs[:5],
            worst_branches=branch_devs[:5],
            warnings=[],
            metadata={
                "acpf_summary_path": "test",
                "dcpf_summary_path": "test",
                "acpf_buses_path": "test",
                "dcpf_buses_path": "test",
                "acpf_branches_path": "test",
                "dcpf_branches_path": "test",
                "intermediate_dir": "test",
                "timestamp": "2024-01-01T00:00:00Z",
            },
        )

        json_path = tmp_path / "characterization.json"
        write_characterization_json(result, json_path)

        # Read back
        data = json.loads(json_path.read_text(encoding="utf-8"))

        # Verify all top-level keys
        expected_keys = {
            "metadata",
            "join_summary",
            "system_level",
            "angle_deviation",
            "flow_deviation_mw",
            "flow_deviation_pct",
            "expected_range_checks",
            "worst_buses",
            "worst_branches",
            "warnings",
        }
        assert set(data.keys()) == expected_keys

        # Verify worst_buses has 5 entries
        assert len(data["worst_buses"]) == 5

        # Verify angle compliance value
        assert isinstance(data["angle_deviation"]["compliance"]["pct_within_3_0_deg"], float)
        assert 0 <= data["angle_deviation"]["compliance"]["pct_within_3_0_deg"] <= 100

        # Verify near_zero_flow_threshold_mw
        assert data["flow_deviation_pct"]["near_zero_flow_threshold_mw"] == 1.0


# ---------------------------------------------------------------------------
# T13-T14: Integration tests (require FNM_PATH and D2/D3 outputs)
# ---------------------------------------------------------------------------


@pytest.mark.fnm
class TestFnmCharacterizationProducesReports:
    """T13: test_fnm_characterization_produces_reports."""

    def test_fnm_characterization_produces_reports(self, require_fnm: dict, tmp_path: Path) -> None:
        """Run build_characterization with actual ACPF/DCPF references."""
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        acpf_dir = repo_root / "data" / "fnm" / "reference" / "acpf"
        dcpf_dir = repo_root / "data" / "fnm" / "reference" / "dcpf"
        int_dir = repo_root / "data" / "fnm" / "intermediate" / "canonical"
        out_dir = tmp_path / "output"

        result_dir = build_characterization(acpf_dir, dcpf_dir, int_dir, out_dir)

        json_path = result_dir / "dcpf_vs_acpf_characterization.json"
        md_path = result_dir / "dcpf_vs_acpf_characterization.md"
        assert json_path.exists()
        assert md_path.exists()

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["join_summary"]["buses_matched"] > 20000
        assert data["join_summary"]["branches_matched"] > 30000
        assert data["angle_deviation"]["count"] > 20000
        assert data["flow_deviation_pct"]["count"] > 20000


@pytest.mark.fnm
class TestFnmCharacterizationExpectedRanges:
    """T14: test_fnm_characterization_expected_ranges."""

    def test_fnm_characterization_expected_ranges(self, require_fnm: dict, tmp_path: Path) -> None:
        """Verify characterization meets relaxed floor thresholds."""
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        acpf_dir = repo_root / "data" / "fnm" / "reference" / "acpf"
        dcpf_dir = repo_root / "data" / "fnm" / "reference" / "dcpf"
        int_dir = repo_root / "data" / "fnm" / "intermediate" / "canonical"
        out_dir = tmp_path / "output"

        result_dir = build_characterization(acpf_dir, dcpf_dir, int_dir, out_dir)

        json_path = result_dir / "dcpf_vs_acpf_characterization.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))

        # Relaxed floors
        assert data["angle_deviation"]["compliance"]["pct_within_3_0_deg"] > 90.0
        assert data["flow_deviation_pct"]["compliance"]["pct_within_10_0_pct"] > 80.0

        # Worst-case lists
        assert len(data["worst_buses"]) == 50
        assert len(data["worst_branches"]) == 50

        # Every worst-case entry has causes
        for wb in data["worst_buses"]:
            assert len(wb["all_causes"]) > 0
        for wb in data["worst_branches"]:
            assert len(wb["all_causes"]) > 0
