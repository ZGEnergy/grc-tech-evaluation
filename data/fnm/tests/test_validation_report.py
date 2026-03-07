"""Tests for Reference Solution Validation Report (PRD 03/06).

All synthetic tests use programmatically created data structures and
tmp_path-based CSV/JSON files.  No external dependencies beyond stdlib.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from fnm.scripts.validation_report import (
    CheckStatus,
    check_acpf_generator_limits,
    check_acpf_kcl,
    check_acpf_power_balance,
    check_acpf_vm_plausibility,
    check_dcpf_flow_angle_consistency,
    check_dcpf_power_balance,
    check_dcpf_slack_angle,
    run_validation,
)

# ---------------------------------------------------------------------------
# Helpers for building synthetic test data
# ---------------------------------------------------------------------------


def _write_csv(path: Path, rows: list[dict]) -> None:
    """Write a list of dicts as a CSV file with header."""
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict) -> None:
    """Write a dict as a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===========================================================================
# T01 / T02 -- ACPF Power Balance
# ===========================================================================


class TestAcpfPowerBalance:
    """Tests for check_acpf_power_balance (ACPF Check A)."""

    def test_acpf_power_balance_pass(self) -> None:
        """T01: Power balance within tolerance -> PASS."""
        summary = {
            "system_summary": {
                "total_gen_mw": 10000.0,
                "total_load_mw": 9700.0,
                "total_loss_mw": 300.0,
                "slack_bus": 1,
            }
        }
        result = check_acpf_power_balance(summary)
        assert result.status == CheckStatus.PASS
        assert result.metric_value is not None
        assert result.metric_value < 0.01
        assert result.tolerance == 1.0

    def test_acpf_power_balance_fail(self) -> None:
        """T02: 2 MW residual -> FAIL."""
        summary = {
            "system_summary": {
                "total_gen_mw": 10000.0,
                "total_load_mw": 9700.0,
                "total_loss_mw": 298.0,
                "slack_bus": 1,
            }
        }
        result = check_acpf_power_balance(summary)
        assert result.status == CheckStatus.FAIL
        assert result.metric_value is not None
        assert abs(result.metric_value - 2.0) < 0.01


# ===========================================================================
# T03 / T04 / T05 -- ACPF Per-Bus KCL
# ===========================================================================


def _make_balanced_5bus() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Build a balanced 5-bus synthetic network.

    Bus 1: Generator 100 MW, 20 MVAr, load 0
    Bus 2: Generator 50 MW, 10 MVAr, load 0
    Bus 3: Load 60 MW, 12 MVAr
    Bus 4: Load 50 MW, 10 MVAr
    Bus 5: Load 40 MW, 8 MVAr

    Branches carry flows such that KCL is exactly satisfied.
    We assign flows manually to make KCL hold:

    Branch 1->3: P_from=40, Q_from=8, P_to=-40, Q_to=-8
    Branch 1->4: P_from=30, Q_from=6, P_to=-30, Q_to=-6
    Branch 1->5: P_from=30, Q_from=6, P_to=-30, Q_to=-6
    Branch 2->3: P_from=20, Q_from=4, P_to=-20, Q_to=-4
    Branch 2->4: P_from=20, Q_from=4, P_to=-20, Q_to=-4
    Branch 2->5: P_from=10, Q_from=2, P_to=-10, Q_to=-2

    KCL at bus 1: Gen(100,20) - Load(0,0) - BranchOut(40+30+30, 8+6+6) = 0,0
    KCL at bus 2: Gen(50,10) - Load(0,0) - BranchOut(20+20+10, 4+4+2) = 0,0
    KCL at bus 3: Gen(0,0) - Load(60,12) - BranchOut(-40-20, -8-4) = 0,0
    KCL at bus 4: Gen(0,0) - Load(50,10) - BranchOut(-30-20, -6-4) = 0,0
    KCL at bus 5: Gen(0,0) - Load(40,8) - BranchOut(-30-10, -6-2) = 0,0
    """
    acpf_buses = [
        {"bus": 1, "VM": 1.0, "VA": 0.0},
        {"bus": 2, "VM": 1.0, "VA": -1.0},
        {"bus": 3, "VM": 0.98, "VA": -2.0},
        {"bus": 4, "VM": 0.99, "VA": -1.5},
        {"bus": 5, "VM": 0.97, "VA": -2.5},
    ]

    acpf_branches = [
        {
            "from_bus": 1,
            "to_bus": 3,
            "ckt": "1",
            "P_from": 40.0,
            "Q_from": 8.0,
            "P_to": -40.0,
            "Q_to": -8.0,
        },
        {
            "from_bus": 1,
            "to_bus": 4,
            "ckt": "1",
            "P_from": 30.0,
            "Q_from": 6.0,
            "P_to": -30.0,
            "Q_to": -6.0,
        },
        {
            "from_bus": 1,
            "to_bus": 5,
            "ckt": "1",
            "P_from": 30.0,
            "Q_from": 6.0,
            "P_to": -30.0,
            "Q_to": -6.0,
        },
        {
            "from_bus": 2,
            "to_bus": 3,
            "ckt": "1",
            "P_from": 20.0,
            "Q_from": 4.0,
            "P_to": -20.0,
            "Q_to": -4.0,
        },
        {
            "from_bus": 2,
            "to_bus": 4,
            "ckt": "1",
            "P_from": 20.0,
            "Q_from": 4.0,
            "P_to": -20.0,
            "Q_to": -4.0,
        },
        {
            "from_bus": 2,
            "to_bus": 5,
            "ckt": "1",
            "P_from": 10.0,
            "Q_from": 2.0,
            "P_to": -10.0,
            "Q_to": -2.0,
        },
    ]

    acpf_generators = [
        {"bus": 1, "machine_id": "1", "P": 100.0, "Q": 20.0},
        {"bus": 2, "machine_id": "1", "P": 50.0, "Q": 10.0},
    ]

    intermediate_buses = [
        {"bus": 1, "bus_type": 3, "PD": 0.0, "QD": 0.0},
        {"bus": 2, "bus_type": 2, "PD": 0.0, "QD": 0.0},
        {"bus": 3, "bus_type": 1, "PD": 60.0, "QD": 12.0},
        {"bus": 4, "bus_type": 1, "PD": 50.0, "QD": 10.0},
        {"bus": 5, "bus_type": 1, "PD": 40.0, "QD": 8.0},
    ]

    return acpf_buses, acpf_branches, acpf_generators, intermediate_buses


class TestAcpfKcl:
    """Tests for check_acpf_kcl (ACPF Check B)."""

    def test_acpf_kcl_balanced_network(self) -> None:
        """T03: Balanced 5-bus network -> PASS."""
        acpf_buses, acpf_branches, acpf_generators, intermediate_buses = _make_balanced_5bus()
        result = check_acpf_kcl(
            acpf_buses,
            acpf_branches,
            acpf_generators,
            intermediate_buses,
            excluded_buses=set(),
        )
        assert result.status == CheckStatus.PASS
        assert result.metric_value is not None
        assert result.metric_value < 0.01
        assert result.failing_elements == 0

    def test_acpf_kcl_single_bus_violation(self) -> None:
        """T04: Perturbed branch flow at bus 1 -> FAIL."""
        acpf_buses, acpf_branches, acpf_generators, intermediate_buses = _make_balanced_5bus()
        # Perturb branch 1->3 P_from by +0.2 MW
        acpf_branches[0]["P_from"] = 40.2

        result = check_acpf_kcl(
            acpf_buses,
            acpf_branches,
            acpf_generators,
            intermediate_buses,
            excluded_buses=set(),
        )
        assert result.status == CheckStatus.FAIL
        assert result.failing_elements >= 1
        assert result.detail is not None
        bus1_entries = [d for d in result.detail if d["bus"] == 1]
        assert len(bus1_entries) >= 1
        assert bus1_entries[0]["mismatch_mva"] > 0.1

    def test_acpf_kcl_excludes_registry_buses(self) -> None:
        """T05: Excluded bus 6 is not checked."""
        acpf_buses, acpf_branches, acpf_generators, intermediate_buses = _make_balanced_5bus()
        # Add bus 6 (excluded) with a load that would cause mismatch
        acpf_buses.append({"bus": 6, "VM": 1.0, "VA": 0.0})
        intermediate_buses.append({"bus": 6, "bus_type": 1, "PD": 100.0, "QD": 50.0})

        result = check_acpf_kcl(
            acpf_buses,
            acpf_branches,
            acpf_generators,
            intermediate_buses,
            excluded_buses={6},
        )
        # Bus 6 should not appear in detail
        if result.detail:
            bus6_entries = [d for d in result.detail if d["bus"] == 6]
            assert len(bus6_entries) == 0
        # total_elements should be 5, not 6
        assert result.total_elements == 5


# ===========================================================================
# T06 / T07 -- ACPF Voltage Plausibility
# ===========================================================================


class TestAcpfVmPlausibility:
    """Tests for check_acpf_vm_plausibility (ACPF Check C)."""

    def test_acpf_vm_all_plausible(self) -> None:
        """T06: All 20 buses in [0.95, 1.05] -> PASS."""
        buses = [{"bus": i, "VM": 0.95 + (i - 1) * 0.1 / 19, "VA": 0.0} for i in range(1, 21)]
        result = check_acpf_vm_plausibility(buses, excluded_buses=set())
        assert result.status == CheckStatus.PASS
        assert result.failing_elements == 0

    def test_acpf_vm_out_of_range(self) -> None:
        """T07: Two buses out of range -> FAIL."""
        buses = [{"bus": i, "VM": 1.0, "VA": 0.0} for i in range(1, 19)]
        buses.append({"bus": 19, "VM": 0.75, "VA": 0.0})
        buses.append({"bus": 20, "VM": 1.25, "VA": 0.0})

        result = check_acpf_vm_plausibility(buses, excluded_buses=set())
        assert result.status == CheckStatus.FAIL
        assert result.failing_elements == 2
        assert result.detail is not None
        detail_buses = {d["bus"] for d in result.detail}
        assert 19 in detail_buses
        assert 20 in detail_buses


# ===========================================================================
# T08 / T09 / T10 -- ACPF Generator Limits
# ===========================================================================


def _make_generators(
    n: int, *, p_offset: float = 0.0, q_offset: float = 0.0
) -> tuple[list[dict], list[dict]]:
    """Create n generators within limits, returning (acpf, intermediate) lists."""
    acpf_gens = []
    int_gens = []
    for i in range(1, n + 1):
        p_val = 50.0
        q_val = 10.0
        acpf_gens.append({"bus": i, "machine_id": "1", "P": p_val, "Q": q_val})
        int_gens.append(
            {
                "bus": i,
                "machine_id": "1",
                "status": 1,
                "PG": p_val,
                "QG": q_val,
                "PT": 100.0,
                "PB": 0.0,
                "QT": 50.0,
                "QB": -50.0,
            }
        )
    return acpf_gens, int_gens


class TestAcpfGeneratorLimits:
    """Tests for check_acpf_generator_limits (ACPF Check D)."""

    def test_acpf_gen_limits_all_within(self) -> None:
        """T08: All 10 generators within limits -> PASS."""
        acpf_gens, int_gens = _make_generators(10)
        summary = {"system_summary": {"slack_bus": 999}}  # No match -> no exemption

        result = check_acpf_generator_limits(acpf_gens, int_gens, summary)
        assert result.status == CheckStatus.PASS
        assert result.failing_elements == 0

    def test_acpf_gen_limits_violation(self) -> None:
        """T09: Two generators with violations -> FAIL."""
        acpf_gens, int_gens = _make_generators(10)
        summary = {"system_summary": {"slack_bus": 999}}

        # Generator at bus 3: P above PT by 0.5 MW
        acpf_gens[2]["P"] = 100.6  # PT=100, tolerance=0.1 -> violation
        # Generator at bus 7: Q below QB by 0.5 MVAr
        acpf_gens[6]["Q"] = -50.6  # QB=-50, tolerance=0.1 -> violation

        result = check_acpf_generator_limits(acpf_gens, int_gens, summary)
        assert result.status == CheckStatus.FAIL
        assert result.failing_elements == 2
        assert result.detail is not None

        violation_types = set()
        for d in result.detail:
            for vt in d["violation_type"]:
                violation_types.add(vt)
        assert "P_above_PT" in violation_types
        assert "Q_below_QB" in violation_types

    def test_acpf_gen_limits_slack_exempt(self) -> None:
        """T10: Slack bus generator exempt from P-limit check."""
        acpf_gens, int_gens = _make_generators(5)
        # The slack bus is bus 1, set its P way above PT
        acpf_gens[0]["P"] = 150.0  # PT=100, +50 MW above limit
        summary = {"system_summary": {"slack_bus": 1}}

        result = check_acpf_generator_limits(acpf_gens, int_gens, summary)

        # Slack generator should NOT appear as a P-limit violator
        if result.detail:
            for d in result.detail:
                if d["bus"] == 1:
                    # Should not have P_above_PT violation
                    assert "P_above_PT" not in d["violation_type"]

        # Notes should mention slack exemption
        assert any("Slack bus generator" in n and "exempt" in n for n in result.notes)


# ===========================================================================
# T11 / T12 -- DCPF Power Balance
# ===========================================================================


class TestDcpfPowerBalance:
    """Tests for check_dcpf_power_balance (DCPF Check A)."""

    def test_dcpf_power_balance_pass(self) -> None:
        """T11: Balanced lossless network -> PASS."""
        summary = {
            "power_summary": {
                "total_generation_mw": 5000.0,
                "total_load_mw": 5000.0,
                "slack_injection_mw": 0.0,
            }
        }
        result = check_dcpf_power_balance(summary)
        assert result.status == CheckStatus.PASS
        assert result.metric_value is not None
        assert result.metric_value < 0.01

    def test_dcpf_power_balance_fail(self) -> None:
        """T12: 0.5 MW residual -> FAIL."""
        summary = {
            "power_summary": {
                "total_generation_mw": 5000.0,
                "total_load_mw": 4999.0,
                "slack_injection_mw": 0.5,
            }
        }
        result = check_dcpf_power_balance(summary)
        assert result.status == CheckStatus.FAIL
        assert result.metric_value is not None
        assert abs(result.metric_value - 0.5) < 0.01


# ===========================================================================
# T13 / T14 -- DCPF Flow-Angle Consistency
# ===========================================================================


def _make_3bus_dc_network() -> tuple[list[dict], list[dict], list[dict], dict]:
    """Build a 3-bus DC network for flow-angle tests.

    Bus 1 (slack, VA=0), Bus 2 (VA=-2.0 deg), Bus 3 (VA=-3.5 deg).
    Branches: 1-2 (X=0.01), 2-3 (X=0.02), 1-3 (X=0.03).
    baseMVA=100.
    """
    dcpf_buses = [
        {"bus": 1, "VA": 0.0},
        {"bus": 2, "VA": -2.0},
        {"bus": 3, "VA": -3.5},
    ]

    intermediate_branches = [
        {
            "from_bus": 1,
            "to_bus": 2,
            "ckt": "1",
            "x_pu": 0.01,
            "tap_ratio": 1.0,
            "shift_deg": 0.0,
            "status": 1,
        },
        {
            "from_bus": 2,
            "to_bus": 3,
            "ckt": "1",
            "x_pu": 0.02,
            "tap_ratio": 1.0,
            "shift_deg": 0.0,
            "status": 1,
        },
        {
            "from_bus": 1,
            "to_bus": 3,
            "ckt": "1",
            "x_pu": 0.03,
            "tap_ratio": 1.0,
            "shift_deg": 0.0,
            "status": 1,
        },
    ]

    base_mva = 100.0
    dcpf_summary = {"base_mva": base_mva, "settings": {"slack_bus": 1}}

    # Compute expected flows: P = (VA_from - VA_to) * pi/180 / X * baseMVA
    dcpf_branches = []
    for br in intermediate_branches:
        va_from = next(b["VA"] for b in dcpf_buses if b["bus"] == br["from_bus"])
        va_to = next(b["VA"] for b in dcpf_buses if b["bus"] == br["to_bus"])
        p_expected = (va_from - va_to) * math.pi / 180.0 / br["x_pu"] * base_mva
        dcpf_branches.append(
            {
                "from_bus": br["from_bus"],
                "to_bus": br["to_bus"],
                "ckt": br["ckt"],
                "P_flow_MW": p_expected,
            }
        )

    return dcpf_buses, dcpf_branches, intermediate_branches, dcpf_summary


class TestDcpfFlowAngleConsistency:
    """Tests for check_dcpf_flow_angle_consistency (DCPF Check B)."""

    def test_dcpf_flow_angle_consistent(self) -> None:
        """T13: Consistent 3-bus network -> PASS."""
        dcpf_buses, dcpf_branches, int_branches, dcpf_summary = _make_3bus_dc_network()
        result = check_dcpf_flow_angle_consistency(
            dcpf_buses,
            dcpf_branches,
            int_branches,
            dcpf_summary,
        )
        assert result.status == CheckStatus.PASS
        assert result.metric_value is not None
        assert result.metric_value < 0.01

    def test_dcpf_flow_angle_inconsistent(self) -> None:
        """T14: Branch 1-2 flow perturbed by 0.5 MW -> FAIL."""
        dcpf_buses, dcpf_branches, int_branches, dcpf_summary = _make_3bus_dc_network()
        # Add 0.5 MW to branch 1-2 stored flow
        dcpf_branches[0]["P_flow_MW"] += 0.5

        result = check_dcpf_flow_angle_consistency(
            dcpf_buses,
            dcpf_branches,
            int_branches,
            dcpf_summary,
        )
        assert result.status == CheckStatus.FAIL
        assert result.failing_elements >= 1
        assert result.detail is not None
        br12 = [d for d in result.detail if d["from_bus"] == 1 and d["to_bus"] == 2]
        assert len(br12) == 1
        assert abs(br12[0]["deviation_mw"] - 0.5) < 0.01


# ===========================================================================
# T15 -- DCPF Slack Angle
# ===========================================================================


class TestDcpfSlackAngle:
    """Tests for check_dcpf_slack_angle (DCPF Check C)."""

    def test_dcpf_slack_angle_zero(self) -> None:
        """T15: Slack bus angle is exactly 0.0 -> PASS."""
        dcpf_buses = [
            {"bus": 1, "VA": 0.0},
            {"bus": 2, "VA": -5.0},
            {"bus": 3, "VA": -8.0},
        ]
        dcpf_summary = {"settings": {"slack_bus": 1}}

        result = check_dcpf_slack_angle(dcpf_buses, dcpf_summary)
        assert result.status == CheckStatus.PASS
        assert result.metric_value == 0.0


# ===========================================================================
# T16 -- Integration test (requires FNM_PATH + D2/D3 outputs)
# ===========================================================================


@pytest.mark.fnm
class TestFnmValidationReport:
    """Integration test using real FNM reference data."""

    def test_fnm_validation_report_produces_outputs(
        self,
        require_fnm: dict,
        tmp_path: Path,
    ) -> None:
        """T16: Run full validation on real FNM reference data."""
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        acpf_dir = repo_root / "data" / "fnm" / "reference" / "acpf"
        dcpf_dir = repo_root / "data" / "fnm" / "reference" / "dcpf"
        intermediate_dir = repo_root / "data" / "fnm" / "intermediate" / "canonical"
        reference_dir = repo_root / "data" / "fnm" / "reference"

        run_validation(
            acpf_dir=acpf_dir,
            dcpf_dir=dcpf_dir,
            intermediate_dir=intermediate_dir,
            reference_dir=reference_dir,
            output_dir=tmp_path,
        )

        # Both output files should exist
        json_path = tmp_path / "validation_report.json"
        md_path = tmp_path / "validation_report.md"
        assert json_path.exists()
        assert md_path.exists()

        # Read and verify JSON structure
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["summary"]["total_checks"] == 7

        # No check should be skipped (all inputs should be present)
        for check in data["checks"]:
            assert check["status"] != "skip", (
                f"Check {check['check_id']} was skipped: {check.get('skip_reason')}"
            )

        # All required fields present in each check
        required_fields = {
            "check_id",
            "check_name",
            "status",
            "metric_value",
            "metric_unit",
            "tolerance",
            "tolerance_unit",
            "total_elements",
            "passing_elements",
            "failing_elements",
            "detail",
            "notes",
            "skip_reason",
        }
        for check in data["checks"]:
            missing = required_fields - set(check.keys())
            assert not missing, f"Check {check['check_id']} missing fields: {missing}"

        # Log per-check results for manual review
        for check in data["checks"]:
            print(f"  {check['check_id']}: {check['status']} (metric={check['metric_value']})")
