"""Tests for tiny_flowgates.py — Flowgate Identification & Calibration."""

from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path

import numpy as np
import pytest

from scripts.tiny_flowgates import (
    DERATE_FACTOR,
    MIN_FLOWGATES,
    BranchData,
    BranchFlowResult,
    BusData,
    FlowgateDefinition,
    FlowgateResult,
    GenData,
    build_b_matrix,
    build_ptdf_matrix,
    compute_branch_flows,
    compute_flowgate_limits,
    dispatch_generators_proportional,
    group_into_flowgates,
    identify_congested_branches,
    main,
    parse_matpower_case_extended,
    solve_dc_power_flow,
    write_flowgate_metadata,
    write_flowgates_csv,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_3bus_m_file(path: Path) -> None:
    """Write a minimal 3-bus MATPOWER .m file for testing.

    Topology: Bus 1 (ref) -- Bus 2 -- Bus 3
    Branch 0: 1->2, x=0.1, rateA=100
    Branch 1: 2->3, x=0.2, rateA=50
    Gen at bus 1: Pmax=100, Pmin=0
    Load at bus 3: Pd=50 MW
    """
    content = textwrap.dedent("""\
        function mpc = case3
        mpc.version = '2';
        mpc.baseMVA = 100;

        mpc.bus = [
            1	3	0	0	0	0	1	1	0	100	1	1.1	0.9;
            2	1	0	0	0	0	1	1	0	100	1	1.1	0.9;
            3	1	50	0	0	0	1	1	0	100	1	1.1	0.9;
        ];

        mpc.gen = [
            1	50	0	50	-50	1	100	1	100	0	0	0	0	0	0	0	0	0	0	0	0;
        ];

        mpc.branch = [
            1	2	0.01	0.1	0	100	100	100	0	0	1	-360	360;
            2	3	0.02	0.2	0	50	50	50	0	0	1	-360	360;
        ];

        mpc.gencost = [
            2	0	0	2	10	0;
        ];
        """)
    path.write_text(content)


def _write_5bus_m_file(path: Path) -> None:
    """Write a 5-bus MATPOWER .m file with known congestion pattern.

    Topology:
      Bus 1 (ref, gen 500MW) -- Bus 2 -- Bus 3 (load 200MW)
                                  |         |
                                Bus 4 --- Bus 5 (load 200MW, gen 100MW)

    Branches with tight ratings to cause congestion:
      0: 1->2, x=0.05, rateA=300
      1: 2->3, x=0.1,  rateA=100  (will congest)
      2: 2->4, x=0.1,  rateA=200
      3: 3->5, x=0.15, rateA=80   (will congest, adjacent to branch 1)
      4: 4->5, x=0.1,  rateA=200
    """
    content = textwrap.dedent("""\
        function mpc = case5
        mpc.version = '2';
        mpc.baseMVA = 100;

        mpc.bus = [
            1	3	0	0	0	0	1	1	0	100	1	1.1	0.9;
            2	1	0	0	0	0	1	1	0	100	1	1.1	0.9;
            3	1	200	0	0	0	1	1	0	100	1	1.1	0.9;
            4	1	0	0	0	0	1	1	0	100	1	1.1	0.9;
            5	1	200	0	0	0	1	1	0	100	1	1.1	0.9;
        ];

        mpc.gen = [
            1	0	0	500	-500	1	100	1	500	0	0	0	0	0	0	0	0	0	0	0	0;
            5	0	0	100	-100	1	100	1	100	0	0	0	0	0	0	0	0	0	0	0	0;
        ];

        mpc.branch = [
            1	2	0.005	0.05	0	300	300	300	0	0	1	-360	360;
            2	3	0.01	0.1	0	100	100	100	0	0	1	-360	360;
            2	4	0.01	0.1	0	200	200	200	0	0	1	-360	360;
            3	5	0.015	0.15	0	80	80	80	0	0	1	-360	360;
            4	5	0.01	0.1	0	200	200	200	0	0	1	-360	360;
        ];

        mpc.gencost = [
            2	0	0	2	10	0;
            2	0	0	2	20	0;
        ];
        """)
    path.write_text(content)


def _write_load_csv(path: Path, bus_loads: dict[int, float]) -> None:
    """Write a load_24h.csv with constant hourly load for simplicity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["bus_id"] + [f"HR_{h}" for h in range(1, 25)]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for bus_id, load_mw in sorted(bus_loads.items()):
            row = [bus_id] + [f"{load_mw:.4f}"] * 24
            writer.writerow(row)


@pytest.fixture
def case39_m_file(tmp_path: Path) -> Path:
    """Provide a path to the real case39.m file if available, else skip."""
    # Try to find the real case39.m in the repo
    repo_root = Path(__file__).resolve().parent.parent.parent
    real_path = repo_root / "networks" / "case39.m"
    if real_path.exists():
        return real_path
    pytest.skip("case39.m not found in data/networks/")
    return real_path  # unreachable


@pytest.fixture
def three_bus_case(tmp_path: Path) -> tuple[Path, Path]:
    """Create a 3-bus case with load CSV."""
    m_path = tmp_path / "case3.m"
    _write_3bus_m_file(m_path)
    load_path = tmp_path / "load_24h.csv"
    _write_load_csv(load_path, {3: 50.0})
    return m_path, load_path


@pytest.fixture
def five_bus_case(tmp_path: Path) -> tuple[Path, Path]:
    """Create a 5-bus case with load CSV."""
    m_path = tmp_path / "case5.m"
    _write_5bus_m_file(m_path)
    load_path = tmp_path / "load_24h.csv"
    _write_load_csv(load_path, {3: 200.0, 5: 200.0})
    return m_path, load_path


# ---------------------------------------------------------------------------
# Test 1: test_parse_matpower_case_bus_count
# ---------------------------------------------------------------------------


def test_parse_matpower_case_bus_count(case39_m_file: Path) -> None:
    """Parse case39.m fixture, verify 39 buses."""
    buses, gens, branches, base_mva = parse_matpower_case_extended(case39_m_file)
    assert len(buses) == 39


# ---------------------------------------------------------------------------
# Test 2: test_parse_matpower_case_branch_count
# ---------------------------------------------------------------------------


def test_parse_matpower_case_branch_count(case39_m_file: Path) -> None:
    """Verify correct branch count in case39.m."""
    buses, gens, branches, base_mva = parse_matpower_case_extended(case39_m_file)
    # case39 has 46 branches
    assert len(branches) == 46


# ---------------------------------------------------------------------------
# Test 3: test_build_b_matrix_shape
# ---------------------------------------------------------------------------


def test_build_b_matrix_shape(three_bus_case: tuple[Path, Path]) -> None:
    """Verify B matrix is (n_bus-1, n_bus-1) after removing ref bus."""
    m_path, _ = three_bus_case
    buses, gens, branches, base_mva = parse_matpower_case_extended(m_path)
    ref_bus_id = next(b.bus_id for b in buses if b.bus_type == 3)
    b_matrix, non_ref = build_b_matrix(buses, branches, ref_bus_id, base_mva)
    # 3 buses - 1 ref = 2x2
    assert b_matrix.shape == (2, 2)
    assert len(non_ref) == 2


# ---------------------------------------------------------------------------
# Test 4: test_build_b_matrix_symmetric
# ---------------------------------------------------------------------------


def test_build_b_matrix_symmetric(three_bus_case: tuple[Path, Path]) -> None:
    """Verify B matrix symmetry."""
    m_path, _ = three_bus_case
    buses, gens, branches, base_mva = parse_matpower_case_extended(m_path)
    ref_bus_id = next(b.bus_id for b in buses if b.bus_type == 3)
    b_matrix, _ = build_b_matrix(buses, branches, ref_bus_id, base_mva)
    np.testing.assert_array_almost_equal(b_matrix, b_matrix.T)


# ---------------------------------------------------------------------------
# Test 5: test_build_ptdf_matrix_shape
# ---------------------------------------------------------------------------


def test_build_ptdf_matrix_shape(three_bus_case: tuple[Path, Path]) -> None:
    """Verify PTDF is (n_branch, n_bus-1)."""
    m_path, _ = three_bus_case
    buses, gens, branches, base_mva = parse_matpower_case_extended(m_path)
    ref_bus_id = next(b.bus_id for b in buses if b.bus_type == 3)
    ptdf, non_ref = build_ptdf_matrix(buses, branches, ref_bus_id, base_mva)
    # 2 branches, 2 non-ref buses
    assert ptdf.shape == (2, 2)


# ---------------------------------------------------------------------------
# Test 6: test_solve_dc_power_flow_trivial
# ---------------------------------------------------------------------------


def test_solve_dc_power_flow_trivial() -> None:
    """3-bus system with known solution.

    Bus 1 (ref): gen 50MW
    Bus 2: no load/gen (pass-through)
    Bus 3: load 50MW

    Branch 0: 1->2, x=0.1
    Branch 1: 2->3, x=0.2

    In the reduced system (buses 2, 3), with baseMVA=100:
    B = [[1/0.1 + 1/0.2, -1/0.2],
         [-1/0.2,         1/0.2]]
      = [[15, -5],
         [-5,  5]]

    P_inject (p.u.): bus 2 = 0, bus 3 = -50/100 = -0.5
    theta = B_inv * P = [[-0.1], [-0.2]]  (negative = consuming)

    Branch flows:
    Branch 0 (1->2): (0 - (-0.1)) / 0.1 * 100 = 100 * 1.0 = (wait...)
    theta_1 = 0 (ref), theta_2 = theta[0], theta_3 = theta[1]
    Branch 0: (0 - theta[0]) / 0.1 = 50/100 * ... let me compute:

    B * theta = P  =>  15*t2 - 5*t3 = 0,  -5*t2 + 5*t3 = -0.5
    From eq1: t2 = t3/3
    Sub into eq2: -5*t3/3 + 5*t3 = -0.5 => t3*(5 - 5/3) = -0.5
    => t3 * 10/3 = -0.5 => t3 = -0.15
    => t2 = -0.05

    Branch 0 flow: (0 - (-0.05))/0.1 * 100 = 50 MW  (correct, all 50MW flows through)
    Branch 1 flow: (-0.05 - (-0.15))/0.2 * 100 = 50 MW
    """
    buses = [
        BusData(bus_id=1, bus_type=3, pd_mw=0.0, qd_mvar=0.0),
        BusData(bus_id=2, bus_type=1, pd_mw=0.0, qd_mvar=0.0),
        BusData(bus_id=3, bus_type=1, pd_mw=50.0, qd_mvar=0.0),
    ]
    branches = [
        BranchData(branch_index=0, from_bus=1, to_bus=2, x_pu=0.1, rate_a_mw=100.0),
        BranchData(branch_index=1, from_bus=2, to_bus=3, x_pu=0.2, rate_a_mw=50.0),
    ]
    ref_bus_id = 1
    base_mva = 100.0

    b_matrix, non_ref = build_b_matrix(buses, branches, ref_bus_id, base_mva)
    assert non_ref == [2, 3]

    # Net injection: bus 2 = 0, bus 3 = -50/100 = -0.5
    p_inject = np.array([0.0, -0.5])
    theta = solve_dc_power_flow(b_matrix, p_inject)

    np.testing.assert_almost_equal(theta[0], -0.05, decimal=10)
    np.testing.assert_almost_equal(theta[1], -0.15, decimal=10)

    flows = compute_branch_flows(theta, branches, non_ref, ref_bus_id, base_mva)
    assert len(flows) == 2
    np.testing.assert_almost_equal(flows[0].flow_mw, 50.0, decimal=6)
    np.testing.assert_almost_equal(flows[1].flow_mw, 50.0, decimal=6)


# ---------------------------------------------------------------------------
# Test 7: test_compute_branch_flows_sign_convention
# ---------------------------------------------------------------------------


def test_compute_branch_flows_sign_convention() -> None:
    """Positive flow = from -> to direction.

    2-bus system: Bus 1 (ref, gen) -> Bus 2 (load 30 MW).
    Branch: 1->2, x=0.1. Flow should be +30 MW.
    """
    buses = [
        BusData(bus_id=1, bus_type=3, pd_mw=0.0, qd_mvar=0.0),
        BusData(bus_id=2, bus_type=1, pd_mw=30.0, qd_mvar=0.0),
    ]
    branches = [
        BranchData(branch_index=0, from_bus=1, to_bus=2, x_pu=0.1, rate_a_mw=100.0),
    ]
    ref_bus_id = 1
    base_mva = 100.0

    b_matrix, non_ref = build_b_matrix(buses, branches, ref_bus_id, base_mva)
    p_inject = np.array([-0.3])  # bus 2: -30/100
    theta = solve_dc_power_flow(b_matrix, p_inject)

    flows = compute_branch_flows(theta, branches, non_ref, ref_bus_id, base_mva)
    # Flow should be positive (from bus 1 to bus 2)
    assert flows[0].flow_mw > 0.0
    np.testing.assert_almost_equal(flows[0].flow_mw, 30.0, decimal=6)


# ---------------------------------------------------------------------------
# Test 8: test_dispatch_generators_proportional
# ---------------------------------------------------------------------------


def test_dispatch_generators_proportional() -> None:
    """Verify generation matches load."""
    gens = [
        GenData(gen_index=0, bus_id=1, pg_mw=0.0, pmax_mw=200.0, pmin_mw=0.0),
        GenData(gen_index=1, bus_id=2, pg_mw=0.0, pmax_mw=100.0, pmin_mw=0.0),
    ]
    total_load = 150.0
    dispatch = dispatch_generators_proportional(gens, total_load)

    total_gen = sum(dispatch.values())
    np.testing.assert_almost_equal(total_gen, total_load, decimal=6)

    # Proportional: gen0 = 200/300 * 150 = 100, gen1 = 100/300 * 150 = 50
    np.testing.assert_almost_equal(dispatch[1], 100.0, decimal=6)
    np.testing.assert_almost_equal(dispatch[2], 50.0, decimal=6)


# ---------------------------------------------------------------------------
# Test 9: test_identify_congested_branches_threshold
# ---------------------------------------------------------------------------


def test_identify_congested_branches_threshold() -> None:
    """Branches at exactly 80% are included."""
    flows = [
        BranchFlowResult(
            branch_index=0,
            from_bus=1,
            to_bus=2,
            flow_mw=80.0,
            rate_a_mw=100.0,
            loading_pct=80.0,
        ),
        BranchFlowResult(
            branch_index=1,
            from_bus=2,
            to_bus=3,
            flow_mw=40.0,
            rate_a_mw=100.0,
            loading_pct=40.0,
        ),
    ]
    congested = identify_congested_branches(flows, threshold=0.80)
    assert len(congested) == 1
    assert congested[0].branch_index == 0


# ---------------------------------------------------------------------------
# Test 10: test_identify_congested_branches_below_threshold
# ---------------------------------------------------------------------------


def test_identify_congested_branches_below_threshold() -> None:
    """Branches at 79% excluded."""
    flows = [
        BranchFlowResult(
            branch_index=0,
            from_bus=1,
            to_bus=2,
            flow_mw=79.0,
            rate_a_mw=100.0,
            loading_pct=79.0,
        ),
        BranchFlowResult(
            branch_index=1,
            from_bus=2,
            to_bus=3,
            flow_mw=50.0,
            rate_a_mw=100.0,
            loading_pct=50.0,
        ),
    ]
    congested = identify_congested_branches(flows, threshold=0.80)
    assert len(congested) == 0


# ---------------------------------------------------------------------------
# Test 11: test_group_into_flowgates_adjacent
# ---------------------------------------------------------------------------


def test_group_into_flowgates_adjacent() -> None:
    """Two branches sharing bus 2 form one flowgate."""
    branches = [
        BranchData(branch_index=0, from_bus=1, to_bus=2, x_pu=0.1, rate_a_mw=100.0),
        BranchData(branch_index=1, from_bus=2, to_bus=3, x_pu=0.2, rate_a_mw=100.0),
        BranchData(branch_index=2, from_bus=4, to_bus=5, x_pu=0.1, rate_a_mw=100.0),
    ]
    congested = [
        BranchFlowResult(
            branch_index=0,
            from_bus=1,
            to_bus=2,
            flow_mw=90.0,
            rate_a_mw=100.0,
            loading_pct=90.0,
        ),
        BranchFlowResult(
            branch_index=1,
            from_bus=2,
            to_bus=3,
            flow_mw=85.0,
            rate_a_mw=100.0,
            loading_pct=85.0,
        ),
    ]
    groups = group_into_flowgates(congested, branches)
    # They share bus 2, so they should be in one group
    assert len(groups) == 1
    assert len(groups[0]) == 2


# ---------------------------------------------------------------------------
# Test 12: test_group_into_flowgates_isolated
# ---------------------------------------------------------------------------


def test_group_into_flowgates_isolated() -> None:
    """Non-adjacent branches form separate flowgates."""
    branches = [
        BranchData(branch_index=0, from_bus=1, to_bus=2, x_pu=0.1, rate_a_mw=100.0),
        BranchData(branch_index=1, from_bus=4, to_bus=5, x_pu=0.2, rate_a_mw=100.0),
    ]
    congested = [
        BranchFlowResult(
            branch_index=0,
            from_bus=1,
            to_bus=2,
            flow_mw=90.0,
            rate_a_mw=100.0,
            loading_pct=90.0,
        ),
        BranchFlowResult(
            branch_index=1,
            from_bus=4,
            to_bus=5,
            flow_mw=85.0,
            rate_a_mw=100.0,
            loading_pct=85.0,
        ),
    ]
    groups = group_into_flowgates(congested, branches)
    assert len(groups) == 2
    assert all(len(g) == 1 for g in groups)


# ---------------------------------------------------------------------------
# Test 13: test_compute_flowgate_limits_derate
# ---------------------------------------------------------------------------


def test_compute_flowgate_limits_derate() -> None:
    """Limit = min(rateA) * 0.95."""
    group = [
        BranchFlowResult(
            branch_index=0,
            from_bus=1,
            to_bus=2,
            flow_mw=90.0,
            rate_a_mw=100.0,
            loading_pct=90.0,
        ),
        BranchFlowResult(
            branch_index=1,
            from_bus=2,
            to_bus=3,
            flow_mw=75.0,
            rate_a_mw=80.0,
            loading_pct=93.75,
        ),
    ]
    limit = compute_flowgate_limits(group, DERATE_FACTOR)
    expected = 80.0 * 0.95
    np.testing.assert_almost_equal(limit, expected, decimal=6)


# ---------------------------------------------------------------------------
# Test 14: test_write_flowgates_csv_columns
# ---------------------------------------------------------------------------


def test_write_flowgates_csv_columns(tmp_path: Path) -> None:
    """Verify CSV columns and format."""
    flowgates = [
        FlowgateDefinition(
            flowgate_id="FG_01",
            name="FG_01_1-2",
            branches=[0],
            from_buses=[1],
            to_buses=[2],
            weights=[1.0],
            limit_mw=95.0,
            binding_load_level="peak",
            max_loading_pct=90.0,
        ),
    ]
    csv_path = tmp_path / "flowgates.csv"
    write_flowgates_csv(flowgates, csv_path)

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) == 1
    expected_cols = {
        "flowgate_id",
        "name",
        "branches",
        "weights",
        "limit_mw",
        "binding_load_level",
        "max_loading_pct",
    }
    assert set(rows[0].keys()) == expected_cols
    assert rows[0]["flowgate_id"] == "FG_01"
    assert rows[0]["branches"] == "1-2"
    assert rows[0]["weights"] == "1.00"
    assert float(rows[0]["limit_mw"]) == 95.0


# ---------------------------------------------------------------------------
# Test 15: test_write_flowgate_metadata_json
# ---------------------------------------------------------------------------


def test_write_flowgate_metadata_json(tmp_path: Path) -> None:
    """Verify JSON structure and required keys."""
    result = FlowgateResult(
        flowgates=[
            FlowgateDefinition(
                flowgate_id="FG_01",
                name="FG_01_1-2",
                branches=[0],
                from_buses=[1],
                to_buses=[2],
                weights=[1.0],
                limit_mw=95.0,
                binding_load_level="peak",
                max_loading_pct=90.0,
            ),
        ],
        branch_flows={
            "peak": [
                BranchFlowResult(
                    branch_index=0,
                    from_bus=1,
                    to_bus=2,
                    flow_mw=90.0,
                    rate_a_mw=100.0,
                    loading_pct=90.0,
                ),
            ],
        },
        metadata={"congestion_threshold": 0.80, "derate_factor": 0.95},
        output_csv_path="test.csv",
        output_json_path="test.json",
    )

    json_path = tmp_path / "flowgate_metadata.json"
    write_flowgate_metadata(result, json_path)

    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)

    required_keys = {
        "script_version",
        "congestion_threshold",
        "derate_factor",
        "load_levels",
        "num_flowgates",
        "flowgates",
        "branch_flow_summary",
    }
    assert required_keys <= set(data.keys())
    assert data["num_flowgates"] == 1
    assert "peak" in data["branch_flow_summary"]


# ---------------------------------------------------------------------------
# Test 16: test_main_produces_minimum_flowgates
# ---------------------------------------------------------------------------


def test_main_produces_minimum_flowgates(case39_m_file: Path, tmp_path: Path) -> None:
    """End-to-end with case39 fixture, >= 2 flowgates."""
    from scripts.reconcile_bus_gen import parse_matpower_case
    from scripts.tiny_load_profile import (
        distribute_load_profile,
        extract_bus_loads_from_records,
        extract_rts_gmlc_load_day,
        normalize_load_shape,
        write_load_csv,
    )

    # Generate load profile
    case_data = parse_matpower_case(case39_m_file)
    load_day = extract_rts_gmlc_load_day()
    shape = normalize_load_shape(load_day)
    bus_loads = extract_bus_loads_from_records(case_data.buses)
    rows = distribute_load_profile(shape, bus_loads)
    load_csv_path = tmp_path / "load_24h.csv"
    write_load_csv(rows, load_csv_path)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = main(
        m_file_path=case39_m_file,
        load_csv_path=load_csv_path,
        output_dir=output_dir,
    )

    assert len(result.flowgates) >= MIN_FLOWGATES
    assert (output_dir / "flowgates.csv").exists()
    assert (output_dir / "flowgate_metadata.json").exists()


# ---------------------------------------------------------------------------
# Test 17: test_flowgate_weights_nonzero
# ---------------------------------------------------------------------------


def test_flowgate_weights_nonzero(case39_m_file: Path, tmp_path: Path) -> None:
    """All weights in output are non-zero."""
    from scripts.reconcile_bus_gen import parse_matpower_case
    from scripts.tiny_load_profile import (
        distribute_load_profile,
        extract_bus_loads_from_records,
        extract_rts_gmlc_load_day,
        normalize_load_shape,
        write_load_csv,
    )

    # Generate load profile
    case_data = parse_matpower_case(case39_m_file)
    load_day = extract_rts_gmlc_load_day()
    shape = normalize_load_shape(load_day)
    bus_loads = extract_bus_loads_from_records(case_data.buses)
    rows = distribute_load_profile(shape, bus_loads)
    load_csv_path = tmp_path / "load_24h.csv"
    write_load_csv(rows, load_csv_path)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = main(
        m_file_path=case39_m_file,
        load_csv_path=load_csv_path,
        output_dir=output_dir,
    )

    for fg in result.flowgates:
        for w in fg.weights:
            assert w != 0.0, f"Zero weight found in flowgate {fg.flowgate_id}"
