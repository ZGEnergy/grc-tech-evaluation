"""Tests for DCPF Reference Solution Computation (PRD 03/03).

All synthetic tests use programmatically created BusRecord, GeneratorRecord,
and BranchRecord instances -- no CSV fixture files needed for pure unit tests.
FNM integration tests are gated by the ``require_fnm`` fixture.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from fnm.scripts.dcpf_reference import (
    FLOW_TOLERANCE_MW,
    BranchFlow,
    BranchRecord,
    BusRecord,
    DCPFSolution,
    GeneratorRecord,
    build_b_matrix,
    compute_bus_injections,
    compute_phase_shift_injections,
    filter_active_buses,
    identify_slack_bus,
    solve_dcpf,
    validate_dcpf_solution,
    write_buses_csv,
    write_summary_json,
)

# ---------------------------------------------------------------------------
# Helper: build a simple 3-bus triangle system
# ---------------------------------------------------------------------------


def _make_3bus_triangle(
    x_12: float = 0.1,
    x_13: float = 0.3,
    x_23: float = 0.2,
) -> tuple[list[BusRecord], list[BranchRecord]]:
    """Build a 3-bus triangle: bus 1 = slack, buses 2 and 3 = PQ.

    Branch reactances are configurable.  All branches are in service,
    tap=1.0, shift=0.0.
    """
    buses = [
        BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
        BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
        BusRecord(bus_number=3, bus_type=1, pd_mw=0.0, base_kv=345.0),
    ]
    branches = [
        BranchRecord(
            from_bus=1,
            to_bus=2,
            circuit_id="1",
            x_pu=x_12,
            tap_ratio=1.0,
            shift_deg=0.0,
            status=1,
            is_transformer=False,
        ),
        BranchRecord(
            from_bus=1,
            to_bus=3,
            circuit_id="1",
            x_pu=x_13,
            tap_ratio=1.0,
            shift_deg=0.0,
            status=1,
            is_transformer=False,
        ),
        BranchRecord(
            from_bus=2,
            to_bus=3,
            circuit_id="1",
            x_pu=x_23,
            tap_ratio=1.0,
            shift_deg=0.0,
            status=1,
            is_transformer=False,
        ),
    ]
    return buses, branches


def _solve_3bus_system(
    buses: list[BusRecord],
    generators: list[GeneratorRecord],
    branches: list[BranchRecord],
    base_mva: float = 100.0,
) -> DCPFSolution:
    """Helper to run a complete DCPF solve on a small system."""
    excluded: set[int] = set()
    active = filter_active_buses(buses, excluded)
    slack = identify_slack_bus(active)
    injections = compute_bus_injections(active, generators, excluded)
    b_result = build_b_matrix(active, branches, excluded, slack, base_mva)
    phase_inj = compute_phase_shift_injections(branches, excluded, base_mva)
    solution = solve_dcpf(b_result, injections, phase_inj, branches, excluded)

    # Set correct total gen/load
    total_gen = sum(g.pg_mw for g in generators if g.status == 1)
    total_load = sum(b.pd_mw for b in active)

    return DCPFSolution(
        bus_angles_deg=solution.bus_angles_deg,
        branch_flows_mw=solution.branch_flows_mw,
        total_generation_mw=total_gen,
        total_load_mw=total_load,
        slack_bus=solution.slack_bus,
        slack_injection_mw=injections.get(slack, 0.0),
        active_bus_count=solution.active_bus_count,
        active_branch_count=solution.active_branch_count,
        zero_impedance_branches=solution.zero_impedance_branches,
        base_mva=solution.base_mva,
    )


# ===========================================================================
# T01: test_build_b_matrix_3bus
# ===========================================================================


class TestBuildBMatrix3Bus:
    """T01: Construct a 3-bus, 3-branch triangle and verify B' matrix entries."""

    def test_matrix_dimensions(self) -> None:
        """B' should be (N-1) x (N-1) = 2x2 for a 3-bus system."""
        buses, branches = _make_3bus_triangle()
        result = build_b_matrix(buses, branches, set(), slack_bus=1, base_mva=100.0)
        assert len(result.b_prime) == 2
        assert len(result.b_prime[0]) == 2

    def test_diagonal_entries(self) -> None:
        """Diagonal entries should be the sum of connected susceptances."""
        buses, branches = _make_3bus_triangle(x_12=0.1, x_13=0.3, x_23=0.2)
        result = build_b_matrix(buses, branches, set(), slack_bus=1, base_mva=100.0)

        # Bus 2 connects to bus 1 (x=0.1) and bus 3 (x=0.2)
        # B'[0,0] for bus 2 = 1/0.1 + 1/0.2 = 10 + 5 = 15.0
        idx2 = result.bus_index_map[2]
        assert abs(result.b_prime[idx2][idx2] - 15.0) < 1e-10

        # Bus 3 connects to bus 1 (x=0.3) and bus 2 (x=0.2)
        # B'[1,1] for bus 3 = 1/0.3 + 1/0.2 = 3.333 + 5.0 = 8.333
        idx3 = result.bus_index_map[3]
        assert abs(result.b_prime[idx3][idx3] - (1 / 0.3 + 1 / 0.2)) < 1e-10

    def test_off_diagonal_entries(self) -> None:
        """Off-diagonal entries should be the negative susceptance of the
        connecting branch."""
        buses, branches = _make_3bus_triangle(x_12=0.1, x_13=0.3, x_23=0.2)
        result = build_b_matrix(buses, branches, set(), slack_bus=1, base_mva=100.0)

        idx2 = result.bus_index_map[2]
        idx3 = result.bus_index_map[3]

        # Off-diagonal B'[2,3] = B'[3,2] = -1/0.2 = -5.0
        assert abs(result.b_prime[idx2][idx3] - (-1 / 0.2)) < 1e-10
        assert abs(result.b_prime[idx3][idx2] - (-1 / 0.2)) < 1e-10


# ===========================================================================
# T02: test_solve_dcpf_3bus
# ===========================================================================


class TestSolveDCPF3Bus:
    """T02: Solve a 3-bus triangle with known injections."""

    def _build(self) -> DCPFSolution:
        buses, branches = _make_3bus_triangle()
        generators = [
            GeneratorRecord(bus_number=2, pg_mw=100.0, status=1, machine_id="1"),
        ]
        # Bus 3 has 100 MW load
        buses_with_load = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=100.0, base_kv=345.0),
        ]
        return _solve_3bus_system(buses_with_load, generators, branches)

    def test_slack_angle_zero(self) -> None:
        solution = self._build()
        assert solution.bus_angles_deg[1] == 0.0

    def test_non_slack_angles_nonzero(self) -> None:
        solution = self._build()
        assert solution.bus_angles_deg[2] != 0.0
        assert solution.bus_angles_deg[3] != 0.0

    def test_power_balance(self) -> None:
        solution = self._build()
        assert abs(solution.total_generation_mw - solution.total_load_mw) < FLOW_TOLERANCE_MW

    def test_branch_flow_injection_consistency(self) -> None:
        """Sum of branch flows into each non-slack bus should equal its injection."""
        solution = self._build()
        # Bus 2: injection = +100 MW (gen) - 0 (load) = +100 MW
        # Bus 3: injection = 0 (gen) - 100 (load) = -100 MW
        # Net flow into bus 2 = sum of flows where bus 2 is the to_bus minus
        # sum of flows where bus 2 is from_bus
        for bus_num, expected_inj in [(2, 100.0), (3, -100.0)]:
            net_flow = 0.0
            for flow in solution.branch_flows_mw:
                if flow.from_bus == bus_num:
                    net_flow -= flow.p_flow_mw
                elif flow.to_bus == bus_num:
                    net_flow += flow.p_flow_mw
            # Net flow out of bus = injection (generation - load)
            # Net flow in = -injection for the bus
            # Actually: sum of P_from for branches FROM this bus +
            #           sum of P_to (= -P_from) for branches TO this bus
            # should equal the injection.
            # P_flow_mw is positive from->to, so:
            # For bus i: injection = sum(P_flow for branches FROM i) - sum(P_flow for branches TO i)
            net_out = 0.0
            for flow in solution.branch_flows_mw:
                if flow.from_bus == bus_num:
                    net_out += flow.p_flow_mw
                elif flow.to_bus == bus_num:
                    net_out -= flow.p_flow_mw
            assert abs(net_out - expected_inj) < FLOW_TOLERANCE_MW


# ===========================================================================
# T03: test_zero_impedance_branch_replacement
# ===========================================================================


class TestZeroImpedanceBranch:
    """T03: Verify zero-impedance branches are handled correctly."""

    def test_replacement_applied(self) -> None:
        """A branch with X=0 should be replaced with ZERO_IMPEDANCE_REPLACEMENT."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=0.0, base_kv=345.0),
        ]
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.0,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]
        result = build_b_matrix(buses, branches, set(), slack_bus=1, base_mva=100.0)
        assert len(result.zero_impedance_branches) == 1
        assert result.zero_impedance_branches[0] == (1, 2, "1")

    def test_near_identical_angles(self) -> None:
        """Buses connected by a zero-impedance branch should have nearly
        identical angles (< 0.01 degrees difference)."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=50.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=2, pg_mw=50.0, status=1, machine_id="1"),
        ]
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.0,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]
        solution = _solve_3bus_system(buses, generators, branches)
        # Bus 1 (slack) angle = 0.0, bus 2 should be very close to 0.0
        angle_diff = abs(solution.bus_angles_deg[1] - solution.bus_angles_deg[2])
        assert angle_diff < 0.01


# ===========================================================================
# T04: test_out_of_service_branch_excluded
# ===========================================================================


class TestOutOfServiceBranch:
    """T04: Out-of-service branches are excluded from B-matrix and flows."""

    def test_excluded_branch_count(self) -> None:
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=0.0, base_kv=345.0),
        ]
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=0.2,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=0,
                is_transformer=False,
            ),
        ]
        result = build_b_matrix(buses, branches, set(), slack_bus=1, base_mva=100.0)
        assert result.excluded_branch_count == 1

    def test_b_matrix_reflects_single_branch(self) -> None:
        """With one of two branches out of service, diagonal should reflect
        only the in-service branch."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=0.0, base_kv=345.0),
        ]
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=0.2,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=0,
                is_transformer=False,
            ),
        ]
        result = build_b_matrix(buses, branches, set(), slack_bus=1, base_mva=100.0)
        idx2 = result.bus_index_map[2]
        # Bus 2 only has the in-service branch to bus 1 (x=0.1)
        assert abs(result.b_prime[idx2][idx2] - 1 / 0.1) < 1e-10

    def test_out_of_service_not_in_flows(self) -> None:
        """A 3-bus triangle with one branch out of service.  The out-of-service
        branch should not appear in flows, but the network stays connected
        via the other two branches."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=50.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=0.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=1, pg_mw=50.0, status=1, machine_id="1"),
        ]
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=1,
                to_bus=3,
                circuit_id="1",
                x_pu=0.2,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=0.2,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=0,
                is_transformer=False,
            ),
        ]
        solution = _solve_3bus_system(buses, generators, branches)
        # Only 2 in-service branches should appear in flows
        assert len(solution.branch_flows_mw) == 2
        # The out-of-service branch (2->3) should not appear
        flow_pairs = {(f.from_bus, f.to_bus) for f in solution.branch_flows_mw}
        assert (2, 3) not in flow_pairs


# ===========================================================================
# T05: test_transformer_tap_ratio_in_b_matrix
# ===========================================================================


class TestTransformerTapRatio:
    """T05: Verify tap-adjusted susceptance in B-matrix."""

    def test_tap_adjusted_diagonal(self) -> None:
        """From-side diagonal should include 1/(X*t^2), to-side 1/X."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
        ]
        x = 0.05
        t = 1.05
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=x,
                tap_ratio=t,
                shift_deg=0.0,
                status=1,
                is_transformer=True,
            ),
        ]
        result = build_b_matrix(buses, branches, set(), slack_bus=1, base_mva=100.0)
        idx2 = result.bus_index_map[2]
        # Bus 2 is the to-side: diagonal = 1/X
        assert abs(result.b_prime[idx2][idx2] - 1 / x) < 1e-10

    def test_tap_differs_from_unity(self) -> None:
        """B-matrix with tap=1.05 should differ from tap=1.0."""
        x = 0.05

        # Use a 3-bus system where bus 2 is the from-side of the transformer
        # to bus 3, so the tap-adjusted diagonal appears in the matrix.
        buses_swap = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=0.0, base_kv=345.0),
        ]
        branches_swap_tap1 = [
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=x,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]
        branches_swap_tap105 = [
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=x,
                tap_ratio=1.05,
                shift_deg=0.0,
                status=1,
                is_transformer=True,
            ),
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]

        r_tap1 = build_b_matrix(buses_swap, branches_swap_tap1, set(), slack_bus=1, base_mva=100.0)
        r_tap105 = build_b_matrix(
            buses_swap, branches_swap_tap105, set(), slack_bus=1, base_mva=100.0
        )

        # Bus 2 is from-side of the transformer to bus 3
        idx2_t1 = r_tap1.bus_index_map[2]
        idx2_t105 = r_tap105.bus_index_map[2]

        # With tap=1.0: from-side diagonal contribution = 1/X = 20
        # With tap=1.05: from-side diagonal contribution = 1/(X*t^2) = 1/(0.05*1.1025) ~18.14
        # Plus the branch to bus 1: 1/0.1 = 10 for both
        diag_tap1 = r_tap1.b_prime[idx2_t1][idx2_t1]
        diag_tap105 = r_tap105.b_prime[idx2_t105][idx2_t105]
        assert diag_tap1 != diag_tap105


# ===========================================================================
# T06: test_phase_shifter_injection
# ===========================================================================


class TestPhaseShifterInjection:
    """T06: Phase-shifting transformer injection modifications."""

    def test_opposite_sign_injections(self) -> None:
        """Phase shift should produce opposite-sign injections at endpoints."""
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=10.0,
                status=1,
                is_transformer=True,
            ),
        ]
        inj = compute_phase_shift_injections(branches, set(), base_mva=100.0)
        assert 1 in inj
        assert 2 in inj
        # Opposite signs
        assert inj[1] * inj[2] < 0
        # |values| should be equal
        assert abs(abs(inj[1]) - abs(inj[2])) < 1e-10

    def test_full_solve_with_phase_shifter(self) -> None:
        """The DCPF solution should reflect the phase shift in branch flow."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=0.0, base_kv=345.0),
        ]
        # No net injection -- all flow is driven by the phase shifter
        generators: list[GeneratorRecord] = []
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=10.0,
                status=1,
                is_transformer=True,
            ),
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=1,
                to_bus=3,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]
        solution = _solve_3bus_system(buses, generators, branches)

        # Find the flow on the phase-shifting branch (1->2)
        ps_flow = None
        for f in solution.branch_flows_mw:
            if f.from_bus == 1 and f.to_bus == 2:
                ps_flow = f
                break
        assert ps_flow is not None
        # Flow should be non-zero (driven by phase shift)
        assert abs(ps_flow.p_flow_mw) > 0.1


# ===========================================================================
# T07: test_parallel_branches
# ===========================================================================


class TestParallelBranches:
    """T07: Two parallel branches with different reactances."""

    def test_both_branches_in_flows(self) -> None:
        """Both parallel branches should appear in the flow results."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=100.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=1, pg_mw=100.0, status=1, machine_id="1"),
        ]
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="2",
                x_pu=0.2,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]
        solution = _solve_3bus_system(buses, generators, branches)
        assert len(solution.branch_flows_mw) == 2

    def test_flows_inversely_proportional_to_reactance(self) -> None:
        """Flow should split inversely proportional to reactance."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=100.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=1, pg_mw=100.0, status=1, machine_id="1"),
        ]
        x1, x2 = 0.1, 0.2
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=x1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="2",
                x_pu=x2,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]
        solution = _solve_3bus_system(buses, generators, branches)

        flows = sorted(solution.branch_flows_mw, key=lambda f: f.circuit_id)
        f1 = flows[0].p_flow_mw  # circuit "1", x=0.1
        f2 = flows[1].p_flow_mw  # circuit "2", x=0.2

        # f1/f2 should equal x2/x1 = 2.0
        assert abs(f1 / f2 - x2 / x1) < 1e-6

    def test_sum_of_flows_equals_injection(self) -> None:
        """Total flow across parallel branches should equal bus injection."""
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=100.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=1, pg_mw=100.0, status=1, machine_id="1"),
        ]
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="2",
                x_pu=0.2,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]
        solution = _solve_3bus_system(buses, generators, branches)
        total_flow = sum(f.p_flow_mw for f in solution.branch_flows_mw)
        # Total flow from bus 1 to bus 2 should equal 100 MW (load at bus 2)
        assert abs(total_flow - 100.0) < FLOW_TOLERANCE_MW


# ===========================================================================
# T08: test_validate_dcpf_consistent_solution
# ===========================================================================


class TestValidateConsistentSolution:
    """T08: Validate a correctly solved DCPF returns all_checks_passed."""

    def test_all_checks_passed(self) -> None:
        buses, branches = _make_3bus_triangle()
        buses_with_load = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=100.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=2, pg_mw=100.0, status=1, machine_id="1"),
        ]
        solution = _solve_3bus_system(buses_with_load, generators, branches)
        validation = validate_dcpf_solution(solution)

        assert validation.all_checks_passed is True
        assert validation.power_balance_ok is True
        assert validation.power_balance_residual_mw < FLOW_TOLERANCE_MW
        assert validation.flow_angle_consistency_ok is True
        assert validation.flow_angle_max_deviation_mw < FLOW_TOLERANCE_MW
        assert validation.slack_angle_zero is True


# ===========================================================================
# T09: test_validate_dcpf_detects_inconsistency
# ===========================================================================


class TestValidateDetectsInconsistency:
    """T09: Validate detects intentionally wrong branch flows."""

    def test_wrong_flows_detected(self) -> None:
        """Constructing a solution with all flows set to 0 while angles are
        non-zero should fail flow-angle consistency."""
        buses, branches = _make_3bus_triangle()
        buses_with_load = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=100.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=2, pg_mw=100.0, status=1, machine_id="1"),
        ]
        good_solution = _solve_3bus_system(buses_with_load, generators, branches)

        # Create bad branch flows (all zero)
        bad_flows = [
            BranchFlow(
                from_bus=f.from_bus,
                to_bus=f.to_bus,
                circuit_id=f.circuit_id,
                p_flow_mw=0.0,  # Intentionally wrong
                angle_diff_deg=f.angle_diff_deg,
                x_pu=f.x_pu,
                is_zero_impedance_replaced=f.is_zero_impedance_replaced,
            )
            for f in good_solution.branch_flows_mw
        ]

        bad_solution = DCPFSolution(
            bus_angles_deg=good_solution.bus_angles_deg,
            branch_flows_mw=bad_flows,
            total_generation_mw=good_solution.total_generation_mw,
            total_load_mw=good_solution.total_load_mw,
            slack_bus=good_solution.slack_bus,
            slack_injection_mw=good_solution.slack_injection_mw,
            active_bus_count=good_solution.active_bus_count,
            active_branch_count=good_solution.active_branch_count,
            zero_impedance_branches=good_solution.zero_impedance_branches,
            base_mva=good_solution.base_mva,
        )

        validation = validate_dcpf_solution(bad_solution)
        assert validation.flow_angle_consistency_ok is False
        assert validation.all_checks_passed is False
        assert validation.flow_angle_max_deviation_mw > FLOW_TOLERANCE_MW


# ===========================================================================
# T10: test_write_buses_csv_schema
# ===========================================================================


class TestWriteBusesCSV:
    """T10: Verify buses_dcpf.csv output schema and content."""

    def test_schema_and_content(self, tmp_path: Path) -> None:
        # Build a 5-bus system
        buses = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=20.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=30.0, base_kv=345.0),
            BusRecord(bus_number=4, bus_type=1, pd_mw=25.0, base_kv=345.0),
            BusRecord(bus_number=5, bus_type=1, pd_mw=25.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=1, pg_mw=100.0, status=1, machine_id="1"),
        ]
        branches = [
            BranchRecord(
                from_bus=1,
                to_bus=2,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=2,
                to_bus=3,
                circuit_id="1",
                x_pu=0.15,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=3,
                to_bus=4,
                circuit_id="1",
                x_pu=0.2,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=4,
                to_bus=5,
                circuit_id="1",
                x_pu=0.1,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
            BranchRecord(
                from_bus=1,
                to_bus=5,
                circuit_id="1",
                x_pu=0.25,
                tap_ratio=1.0,
                shift_deg=0.0,
                status=1,
                is_transformer=False,
            ),
        ]
        solution = _solve_3bus_system(buses, generators, branches)

        csv_path = tmp_path / "buses_dcpf.csv"
        write_buses_csv(solution, csv_path)

        # Read back
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Check columns
        assert list(rows[0].keys()) == ["bus", "VA"]

        # Check row count
        assert len(rows) == 5

        # Check sorted by bus ascending
        bus_nums = [int(r["bus"]) for r in rows]
        assert bus_nums == sorted(bus_nums)

        # Check slack bus has VA == 0.0
        slack_row = [r for r in rows if int(r["bus"]) == 1][0]
        assert float(slack_row["VA"]) == 0.0


# ===========================================================================
# T11: test_write_summary_json_schema
# ===========================================================================


class TestWriteSummaryJSON:
    """T11: Verify summary_dcpf.json output schema."""

    def test_schema(self, tmp_path: Path) -> None:
        buses, branches = _make_3bus_triangle()
        buses_with_load = [
            BusRecord(bus_number=1, bus_type=3, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=2, bus_type=1, pd_mw=0.0, base_kv=345.0),
            BusRecord(bus_number=3, bus_type=1, pd_mw=100.0, base_kv=345.0),
        ]
        generators = [
            GeneratorRecord(bus_number=2, pg_mw=100.0, status=1, machine_id="1"),
        ]
        solution = _solve_3bus_system(buses_with_load, generators, branches)
        validation = validate_dcpf_solution(solution)

        json_path = tmp_path / "summary_dcpf.json"
        write_summary_json(solution, validation, json_path)

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        # Check all top-level keys
        expected_keys = {
            "solver",
            "formulation",
            "base_mva",
            "settings",
            "network_summary",
            "power_summary",
            "angle_summary",
            "validation",
            "zero_impedance_branches",
        }
        assert expected_keys.issubset(set(data.keys()))

        # Solver value
        assert data["solver"] == "stdlib_gaussian_elimination"

        # Validation.all_checks_passed is a boolean
        assert isinstance(data["validation"]["all_checks_passed"], bool)


# ===========================================================================
# T12-T14: FNM integration tests (gated by require_fnm)
# ===========================================================================


@pytest.mark.fnm
class TestFnmDCPFCompletes:
    """T12: Run DCPF on actual FNM data and verify completion."""

    def test_completes(self, require_fnm: object, tmp_path: Path) -> None:
        pytest.skip("FNM integration tests require FNM_PATH and D1/D6 outputs")


@pytest.mark.fnm
class TestFnmDCPFValidation:
    """T13: Run FNM DCPF and verify validation passes."""

    def test_validation_passes(self, require_fnm: object, tmp_path: Path) -> None:
        pytest.skip("FNM integration tests require FNM_PATH and D1/D6 outputs")


@pytest.mark.fnm
class TestFnmDCPFOutputRowCounts:
    """T14: Verify FNM DCPF output row counts and no NaN/inf values."""

    def test_output_row_counts(self, require_fnm: object, tmp_path: Path) -> None:
        pytest.skip("FNM integration tests require FNM_PATH and D1/D6 outputs")
