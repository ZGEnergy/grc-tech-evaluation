"""Tests for Pass Condition Definitions (PRD 03/05).

All tests use synthetic data with deterministic, known passing/failing counts.
No external dependencies beyond stdlib + pytest.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from fnm.scripts.pass_conditions import (
    OutlierCause,
    build_pass_condition_spec,
    evaluate_acpf,
    evaluate_dcpf,
    load_spec,
    write_json,
    write_markdown,
)

# ---------------------------------------------------------------------------
# Specification generation tests (T01-T04)
# ---------------------------------------------------------------------------


def test_build_spec_defaults() -> None:
    """T01: Verify all default threshold values."""
    spec = build_pass_condition_spec()

    # ACPF aggregate
    assert spec.acpf_aggregate.min_passing_fraction == 0.95
    assert spec.acpf_aggregate.vm_tolerance_pu == 0.005
    assert spec.acpf_aggregate.va_tolerance_deg == 0.5

    # DCPF aggregate
    assert spec.dcpf_aggregate.min_bus_passing_fraction == 0.95
    assert spec.dcpf_aggregate.va_tolerance_deg == 1.0
    assert spec.dcpf_aggregate.min_branch_passing_fraction == 0.90
    assert spec.dcpf_aggregate.p_tolerance_pct == 10.0
    assert spec.dcpf_aggregate.p_base_floor_mw == 1.0

    # ACPF hard-fail
    assert spec.acpf_hard_fail.max_failing_fraction == 0.20
    assert spec.acpf_hard_fail.vm_max_deviation_pu == 0.1
    assert spec.acpf_hard_fail.va_max_deviation_deg == 10.0

    # DCPF hard-fail
    assert spec.dcpf_hard_fail.max_bus_failing_fraction == 0.20
    assert spec.dcpf_hard_fail.max_branch_failing_fraction == 0.20
    assert spec.dcpf_hard_fail.p_max_deviation_pct == 50.0

    # Version
    assert spec.version == "1.0.0"


def test_spec_outlier_rules_count_and_order() -> None:
    """T02: Verify outlier rule count, order, and content."""
    spec = build_pass_condition_spec()
    rules = spec.outlier_classification.rules

    assert len(rules) == 5

    expected_causes = [
        OutlierCause.SWITCHED_SHUNT,
        OutlierCause.Q_LIMIT,
        OutlierCause.SLACK_DISTRIBUTION,
        OutlierCause.TAP_POSITION,
        OutlierCause.ISLAND_BOUNDARY,
    ]
    for rule, expected_cause in zip(rules, expected_causes):
        assert rule.cause == expected_cause
        assert len(rule.description) > 0
        assert len(rule.required_data) > 0
        assert len(rule.match_condition) > 0


def test_spec_voltage_tiers() -> None:
    """T03: Verify voltage-level tier definitions."""
    spec = build_pass_condition_spec()
    tiers = spec.voltage_level_tiers

    assert len(tiers) == 3

    # Tier 1: transmission >= 230 kV
    assert tiers[0].label == "transmission_230kv_plus"
    assert tiers[0].min_kv == 230.0
    assert math.isinf(tiers[0].max_kv)

    # Tier 2: subtransmission 69-230 kV
    assert tiers[1].label == "subtransmission_69_to_229kv"
    assert tiers[1].min_kv == 69.0
    assert tiers[1].max_kv == 230.0

    # Tier 3: distribution < 69 kV
    assert tiers[2].label == "distribution_below_69kv"
    assert tiers[2].min_kv == 0.0
    assert tiers[2].max_kv == 69.0

    # Verify contiguity: no gap or overlap
    # Tier 3 covers [0, 69), Tier 2 covers [69, 230), Tier 1 covers [230, inf)
    assert tiers[2].max_kv == tiers[1].min_kv
    assert tiers[1].max_kv == tiers[0].min_kv


def test_spec_reference_paths() -> None:
    """T04: Verify reference paths."""
    spec = build_pass_condition_spec()

    assert spec.bus_exclusion_registry_path == "data/fnm/reference/excluded_buses.json"
    assert spec.acpf_reference_dir == "data/fnm/reference/acpf/"
    assert spec.dcpf_reference_dir == "data/fnm/reference/dcpf/"


# ---------------------------------------------------------------------------
# Serialization round-trip tests (T05-T07)
# ---------------------------------------------------------------------------


def test_json_roundtrip(tmp_path: Path) -> None:
    """T05: JSON write + load round-trip preserves all values."""
    spec = build_pass_condition_spec()
    json_path = tmp_path / "pass_conditions.json"
    write_json(spec, json_path)

    loaded = load_spec(json_path)

    # ACPF aggregate
    assert loaded.acpf_aggregate.min_passing_fraction == spec.acpf_aggregate.min_passing_fraction
    assert loaded.acpf_aggregate.vm_tolerance_pu == spec.acpf_aggregate.vm_tolerance_pu
    assert loaded.acpf_aggregate.va_tolerance_deg == spec.acpf_aggregate.va_tolerance_deg

    # DCPF aggregate
    assert (
        loaded.dcpf_aggregate.min_bus_passing_fraction
        == spec.dcpf_aggregate.min_bus_passing_fraction
    )
    assert loaded.dcpf_aggregate.va_tolerance_deg == spec.dcpf_aggregate.va_tolerance_deg
    assert (
        loaded.dcpf_aggregate.min_branch_passing_fraction
        == spec.dcpf_aggregate.min_branch_passing_fraction
    )
    assert loaded.dcpf_aggregate.p_tolerance_pct == spec.dcpf_aggregate.p_tolerance_pct
    assert loaded.dcpf_aggregate.p_base_floor_mw == spec.dcpf_aggregate.p_base_floor_mw

    # ACPF hard-fail
    assert loaded.acpf_hard_fail.max_failing_fraction == spec.acpf_hard_fail.max_failing_fraction
    assert loaded.acpf_hard_fail.vm_max_deviation_pu == spec.acpf_hard_fail.vm_max_deviation_pu
    assert loaded.acpf_hard_fail.va_max_deviation_deg == spec.acpf_hard_fail.va_max_deviation_deg

    # DCPF hard-fail
    assert (
        loaded.dcpf_hard_fail.max_bus_failing_fraction
        == spec.dcpf_hard_fail.max_bus_failing_fraction
    )
    assert (
        loaded.dcpf_hard_fail.max_branch_failing_fraction
        == spec.dcpf_hard_fail.max_branch_failing_fraction
    )
    assert loaded.dcpf_hard_fail.p_max_deviation_pct == spec.dcpf_hard_fail.p_max_deviation_pct

    # Outlier rules
    assert len(loaded.outlier_classification.rules) == len(spec.outlier_classification.rules)

    # Voltage tiers
    assert len(loaded.voltage_level_tiers) == len(spec.voltage_level_tiers)

    # Version
    assert loaded.version == spec.version


def test_json_schema_structure(tmp_path: Path) -> None:
    """T06: Verify top-level JSON structure and numeric types."""
    spec = build_pass_condition_spec()
    json_path = tmp_path / "pass_conditions.json"
    write_json(spec, json_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Top-level keys
    assert "$schema_version" in data
    assert "$description" in data
    assert "bus_exclusion" in data
    assert "acpf" in data
    assert "dcpf" in data
    assert "voltage_level_tiers" in data

    # ACPF sub-keys
    assert "reference_dir" in data["acpf"]
    assert "reference_files" in data["acpf"]
    assert "aggregate" in data["acpf"]
    assert "hard_fail" in data["acpf"]
    assert "outlier_classification" in data["acpf"]

    # DCPF sub-keys
    assert "reference_dir" in data["dcpf"]
    assert "reference_files" in data["dcpf"]
    assert "aggregate" in data["dcpf"]
    assert "hard_fail" in data["dcpf"]

    # Check that numeric thresholds are numbers, not strings
    assert isinstance(data["acpf"]["aggregate"]["min_passing_fraction"], (int, float))
    assert isinstance(data["acpf"]["aggregate"]["vm_tolerance_pu"], (int, float))
    assert isinstance(data["acpf"]["aggregate"]["va_tolerance_deg"], (int, float))
    assert isinstance(
        data["dcpf"]["aggregate"]["bus_angle"]["min_passing_fraction"],
        (int, float),
    )
    assert isinstance(
        data["dcpf"]["aggregate"]["branch_flow"]["p_tolerance_pct"],
        (int, float),
    )


def test_markdown_generation(tmp_path: Path) -> None:
    """T07: Verify markdown content and minimum size."""
    spec = build_pass_condition_spec()
    md_path = tmp_path / "pass_conditions.md"
    write_markdown(spec, md_path)

    content = md_path.read_text(encoding="utf-8")

    # Required strings
    assert "0.005 p.u." in content or "0.005" in content
    assert "0.5 degrees" in content or "0.5" in content
    assert "95%" in content
    assert "switched_shunt" in content
    assert "hard-fail" in content or "Hard-Fail" in content or "Hard-fail" in content
    assert "DCPF" in content
    assert "ACPF" in content
    assert "voltage level" in content.lower() or "Voltage Level" in content
    assert "branch flow deviation" in content.lower() or "Branch Flow" in content

    # Non-trivial content
    assert len(content.encode("utf-8")) > 1000


# ---------------------------------------------------------------------------
# Helper: synthetic bus/branch generators
# ---------------------------------------------------------------------------


def _make_ref_buses(
    n: int,
    vm_base: float = 1.0,
    va_base: float = 0.0,
    start_bus: int = 1,
) -> list[dict]:
    """Create n synthetic reference buses."""
    buses = []
    for i in range(n):
        bus_num = start_bus + i
        # Spread VM in [0.95, 1.05] and VA in [-15, 10]
        vm = vm_base + 0.05 * (2 * (i % 10) / 9 - 1)
        va = va_base + 25.0 * (i % 20) / 19 - 15.0
        buses.append({"bus": bus_num, "VM": vm, "VA": va})
    return buses


def _make_tool_buses_acpf(
    ref_buses: list[dict],
    vm_dev: float = 0.002,
    va_dev: float = 0.1,
    fail_indices: list[int] | None = None,
    fail_vm_dev: float = 0.008,
    fail_va_dev: float = 0.1,
    hard_fail_index: int | None = None,
    hard_fail_vm_dev: float = 0.0,
    hard_fail_va_dev: float = 0.0,
) -> list[dict]:
    """Create tool buses with controlled deviations."""
    fail_set = set(fail_indices) if fail_indices else set()
    tool = []
    for i, rb in enumerate(ref_buses):
        if i == hard_fail_index:
            tool.append(
                {
                    "bus": rb["bus"],
                    "VM": rb["VM"] + hard_fail_vm_dev,
                    "VA": rb["VA"] + hard_fail_va_dev,
                }
            )
        elif i in fail_set:
            tool.append(
                {
                    "bus": rb["bus"],
                    "VM": rb["VM"] + fail_vm_dev,
                    "VA": rb["VA"] + fail_va_dev,
                }
            )
        else:
            tool.append(
                {
                    "bus": rb["bus"],
                    "VM": rb["VM"] + vm_dev,
                    "VA": rb["VA"] + va_dev,
                }
            )
    return tool


def _make_base_kv_map(
    buses: list[dict],
    kv_values: list[float] | None = None,
) -> dict[int, float]:
    """Create bus_base_kv mapping cycling through kv_values."""
    if kv_values is None:
        kv_values = [69.0, 115.0, 138.0, 230.0, 500.0]
    return {b["bus"]: kv_values[i % len(kv_values)] for i, b in enumerate(buses)}


# ---------------------------------------------------------------------------
# ACPF evaluation tests (T08-T11)
# ---------------------------------------------------------------------------


def test_acpf_all_pass() -> None:
    """T08: 100% pass with small deviations."""
    spec = build_pass_condition_spec()
    ref_buses = _make_ref_buses(100)
    tool_buses = _make_tool_buses_acpf(ref_buses, vm_dev=0.003, va_dev=0.3)
    bus_base_kv = _make_base_kv_map(ref_buses)

    verdict = evaluate_acpf(
        spec=spec,
        tool_buses=tool_buses,
        ref_buses=ref_buses,
        excluded_bus_numbers=set(),
        bus_base_kv=bus_base_kv,
        classify_outliers=False,
    )

    assert verdict.overall_pass is True
    assert verdict.hard_fail is False
    assert verdict.aggregate_metrics[0].passed is True
    assert verdict.aggregate_metrics[0].value == 1.0


def test_acpf_aggregate_fail() -> None:
    """T09: 90% pass (below 95% threshold) — aggregate fail, no hard-fail."""
    spec = build_pass_condition_spec()
    ref_buses = _make_ref_buses(100)

    # 10 buses fail with VM deviation of 0.008 (> 0.005)
    fail_indices = list(range(10))
    tool_buses = _make_tool_buses_acpf(
        ref_buses,
        vm_dev=0.002,
        va_dev=0.1,
        fail_indices=fail_indices,
        fail_vm_dev=0.008,
        fail_va_dev=0.1,
    )
    bus_base_kv = _make_base_kv_map(ref_buses)

    verdict = evaluate_acpf(
        spec=spec,
        tool_buses=tool_buses,
        ref_buses=ref_buses,
        excluded_bus_numbers=set(),
        bus_base_kv=bus_base_kv,
        classify_outliers=False,
    )

    assert verdict.overall_pass is False
    assert verdict.hard_fail is False
    assert verdict.aggregate_metrics[0].value == 0.90


def test_acpf_hard_fail_extreme_vm() -> None:
    """T10: One bus has VM deviation of 0.15 — hard-fail triggered."""
    spec = build_pass_condition_spec()
    ref_buses = _make_ref_buses(100)

    # 99 buses pass, 1 bus has extreme VM deviation
    tool_buses = _make_tool_buses_acpf(
        ref_buses,
        vm_dev=0.002,
        va_dev=0.1,
        hard_fail_index=50,
        hard_fail_vm_dev=0.15,
        hard_fail_va_dev=0.0,
    )
    bus_base_kv = _make_base_kv_map(ref_buses)

    verdict = evaluate_acpf(
        spec=spec,
        tool_buses=tool_buses,
        ref_buses=ref_buses,
        excluded_bus_numbers=set(),
        bus_base_kv=bus_base_kv,
        classify_outliers=False,
    )

    assert verdict.overall_pass is False
    assert verdict.hard_fail is True

    # Find the extreme_vm_deviation check
    vm_check = next(c for c in verdict.hard_fail_checks if c.check_name == "extreme_vm_deviation")
    assert vm_check.triggered is True


def test_acpf_hard_fail_excessive_fraction() -> None:
    """T11: 25% of buses fail — exceeds 20% hard-fail threshold."""
    spec = build_pass_condition_spec()
    ref_buses = _make_ref_buses(100)

    # 25 buses fail (VM deviation 0.008)
    fail_indices = list(range(25))
    tool_buses = _make_tool_buses_acpf(
        ref_buses,
        vm_dev=0.002,
        va_dev=0.1,
        fail_indices=fail_indices,
        fail_vm_dev=0.008,
        fail_va_dev=0.1,
    )
    bus_base_kv = _make_base_kv_map(ref_buses)

    verdict = evaluate_acpf(
        spec=spec,
        tool_buses=tool_buses,
        ref_buses=ref_buses,
        excluded_bus_numbers=set(),
        bus_base_kv=bus_base_kv,
        classify_outliers=False,
    )

    assert verdict.hard_fail is True

    fraction_check = next(
        c for c in verdict.hard_fail_checks if c.check_name == "excessive_failing_fraction"
    )
    assert fraction_check.triggered is True


# ---------------------------------------------------------------------------
# DCPF evaluation tests (T12-T14)
# ---------------------------------------------------------------------------


def _make_ref_buses_dcpf(n: int, start_bus: int = 1) -> list[dict]:
    """Create n synthetic DCPF reference buses (VA only)."""
    buses = []
    for i in range(n):
        bus_num = start_bus + i
        va = 40.0 * (i % 20) / 19 - 20.0  # VA in [-20, 20]
        buses.append({"bus": bus_num, "VA": va})
    return buses


def _make_ref_branches(n: int) -> list[dict]:
    """Create n synthetic reference branches."""
    branches = []
    for i in range(n):
        from_bus = i + 1
        to_bus = i + 2
        p_flow = 1000.0 * (2 * (i % 50) / 49 - 1)  # P in [-1000, 1000]
        branches.append(
            {
                "from_bus": from_bus,
                "to_bus": to_bus,
                "ckt": "1",
                "P_flow_MW": p_flow,
            }
        )
    return branches


def test_dcpf_all_pass() -> None:
    """T12: All buses and branches pass."""
    spec = build_pass_condition_spec()
    ref_buses = _make_ref_buses_dcpf(100)
    ref_branches = _make_ref_branches(200)

    # Tool buses: VA deviation < 0.5 (well within 1.0 tolerance)
    tool_buses = [{"bus": b["bus"], "VA": b["VA"] + 0.4} for b in ref_buses]

    # Tool branches: P deviation < 5% (well within 10% tolerance)
    tool_branches = []
    for rb in ref_branches:
        p_ref = rb["P_flow_MW"]
        p_base = max(abs(p_ref), 1.0)
        # 5% deviation from p_base
        p_tool = p_ref + 0.04 * p_base  # 4% deviation
        tool_branches.append(
            {
                "from_bus": rb["from_bus"],
                "to_bus": rb["to_bus"],
                "ckt": rb["ckt"],
                "P_flow_MW": p_tool,
            }
        )

    bus_base_kv = {b["bus"]: 230.0 for b in ref_buses}

    verdict = evaluate_dcpf(
        spec=spec,
        tool_buses=tool_buses,
        ref_buses=ref_buses,
        tool_branches=tool_branches,
        ref_branches=ref_branches,
        excluded_bus_numbers=set(),
        bus_base_kv=bus_base_kv,
    )

    assert verdict.overall_pass is True
    assert verdict.hard_fail is False


def test_dcpf_branch_flow_fail() -> None:
    """T13: Bus metric passes but branch metric fails (15% exceed P tolerance)."""
    spec = build_pass_condition_spec()
    ref_buses = _make_ref_buses_dcpf(100)
    ref_branches = _make_ref_branches(200)

    # Tool buses: all pass VA tolerance
    tool_buses = [{"bus": b["bus"], "VA": b["VA"] + 0.3} for b in ref_buses]

    # Tool branches: 170 pass, 30 fail (15% fail > 10% tolerance means
    # branch_passing = 170/200 = 0.85 < 0.90)
    tool_branches = []
    for i, rb in enumerate(ref_branches):
        p_ref = rb["P_flow_MW"]
        p_base = max(abs(p_ref), 1.0)
        if i < 30:
            # Make these fail: deviation > 10% but < 50% (no hard-fail)
            p_tool = p_ref + 0.15 * p_base  # 15% deviation
        else:
            # These pass: deviation < 10%
            p_tool = p_ref + 0.03 * p_base  # 3% deviation
        tool_branches.append(
            {
                "from_bus": rb["from_bus"],
                "to_bus": rb["to_bus"],
                "ckt": rb["ckt"],
                "P_flow_MW": p_tool,
            }
        )

    bus_base_kv = {b["bus"]: 230.0 for b in ref_buses}

    verdict = evaluate_dcpf(
        spec=spec,
        tool_buses=tool_buses,
        ref_buses=ref_buses,
        tool_branches=tool_branches,
        ref_branches=ref_branches,
        excluded_bus_numbers=set(),
        bus_base_kv=bus_base_kv,
    )

    assert verdict.overall_pass is False

    # Bus metric passes
    bus_metric = next(
        m for m in verdict.aggregate_metrics if m.metric_name == "dcpf_bus_va_aggregate"
    )
    assert bus_metric.passed is True

    # Branch metric fails
    branch_metric = next(
        m for m in verdict.aggregate_metrics if m.metric_name == "dcpf_branch_p_aggregate"
    )
    assert branch_metric.passed is False


def test_dcpf_p_base_floor() -> None:
    """T14: Verify p_base_floor prevents inflated deviation on low-flow branches."""
    spec = build_pass_condition_spec()

    # Single reference bus (to avoid zero-denominator)
    ref_buses = [{"bus": 1, "VA": 0.0}]
    tool_buses = [{"bus": 1, "VA": 0.0}]

    # One reference branch with very small flow
    ref_branches = [
        {"from_bus": 1, "to_bus": 2, "ckt": "1", "P_flow_MW": 0.1},
    ]
    # Tool branch with slightly larger flow
    tool_branches = [
        {"from_bus": 1, "to_bus": 2, "ckt": "1", "P_flow_MW": 0.5},
    ]

    bus_base_kv = {1: 230.0}

    verdict = evaluate_dcpf(
        spec=spec,
        tool_buses=tool_buses,
        ref_buses=ref_buses,
        tool_branches=tool_branches,
        ref_branches=ref_branches,
        excluded_bus_numbers=set(),
        bus_base_kv=bus_base_kv,
    )

    # Without floor: deviation = |0.5-0.1|/|0.1| * 100 = 400%
    # With floor (1.0 MW): deviation = |0.5-0.1|/1.0 * 100 = 40%
    # The branch still fails (40 > 10) but does NOT trigger the 50% hard-fail

    # Check that hard-fail for extreme branch deviation is NOT triggered
    extreme_check = next(
        c for c in verdict.hard_fail_checks if c.check_name == "extreme_branch_flow_deviation"
    )
    assert extreme_check.triggered is False
    # The value should be 40.0, not 400.0
    assert abs(extreme_check.value - 40.0) < 0.01
