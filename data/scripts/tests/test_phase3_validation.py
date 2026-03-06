"""Tests for phase3_validation.py — 18 unit tests for PRD 03/07.

All tests are self-contained with no external file dependencies or network calls.
"""

from __future__ import annotations

from scripts.phase3_validation import (
    BessUnitRecord,
    BranchRecord,
    BusRecord,
    CheckCategory,
    CheckStatus,
    CrossPhaseConsistencyResult,
    DrBusRecord,
    FlowgateRecord,
    NetworkTopology,
    NetworkValidationResult,
    ReserveEligibilityRecord,
    build_validation_report,
    check_bess_bus_existence,
    check_bess_fleet_fraction,
    check_bess_reserve_eligibility,
    check_dr_bus_existence,
    check_dr_curtailment_fraction,
    check_flowgate_branch_disjoint,
    check_flowgate_branch_existence,
    check_flowgate_limits,
    check_no_bess_dr_overlap,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_topology(
    buses: list[tuple[int, int, float]],  # (bus, bus_type, pd_mw)
    branches: list[tuple[int, int, int, float]] | None = None,  # (idx, from, to, rate_a)
    system_peak_mw: float | None = None,
) -> NetworkTopology:
    """Build a minimal NetworkTopology for testing.

    Args:
        buses: List of (bus_number, bus_type, pd_mw) tuples.
        branches: List of (branch_idx, from_bus, to_bus, rate_a_mw) tuples.
        system_peak_mw: Override for system peak. Defaults to sum of positive Pd.
    """
    bus_records = [BusRecord(bus=b, bus_type=bt, pd_mw=pd, area=1) for b, bt, pd in buses]
    branch_records = []
    if branches:
        branch_records = [
            BranchRecord(branch_idx=idx, from_bus=fb, to_bus=tb, rate_a_mw=ra)
            for idx, fb, tb, ra in branches
        ]

    bus_set = frozenset(b.bus for b in bus_records)
    bus_pd_map = {b.bus: b.pd_mw for b in bus_records}
    bus_type_map = {b.bus: b.bus_type for b in bus_records}
    branch_idx_set = frozenset(br.branch_idx for br in branch_records)
    branch_rate_map = {br.branch_idx: br.rate_a_mw for br in branch_records}

    if system_peak_mw is None:
        system_peak_mw = sum(b.pd_mw for b in bus_records if b.pd_mw > 0)

    return NetworkTopology(
        network_id="TEST",
        buses=bus_records,
        branches=branch_records,
        bus_set=bus_set,
        bus_pd_map=bus_pd_map,
        bus_type_map=bus_type_map,
        branch_idx_set=branch_idx_set,
        branch_rate_map=branch_rate_map,
        system_peak_mw=system_peak_mw,
    )


# ---------------------------------------------------------------------------
# Test 1: BESS bus existence — all valid
# ---------------------------------------------------------------------------


def test_check_bess_bus_existence_all_valid() -> None:
    """All BESS unit buses exist in .m file with valid bus types (type 1)."""
    topology = _make_topology(
        buses=[(1, 1, 100.0), (2, 1, 200.0), (3, 1, 300.0), (10, 1, 400.0), (20, 1, 500.0)],
    )
    bess_units = [
        BessUnitRecord(unit_id="B1", bus=1, power_mw=10.0, cyclic_soc=True),
        BessUnitRecord(unit_id="B2", bus=10, power_mw=20.0, cyclic_soc=True),
        BessUnitRecord(unit_id="B3", bus=20, power_mw=30.0, cyclic_soc=True),
    ]
    result = check_bess_bus_existence(bess_units, topology)

    assert result.status == CheckStatus.PASS
    assert result.items_checked == 3
    assert result.items_failed == 0
    assert result.items_passed == 3
    assert not result.details


# ---------------------------------------------------------------------------
# Test 2: BESS bus existence — missing bus
# ---------------------------------------------------------------------------


def test_check_bess_bus_existence_missing_bus() -> None:
    """BESS unit at bus 99 which does not exist in the .m file."""
    topology = _make_topology(
        buses=[(1, 1, 100.0), (2, 1, 200.0), (3, 1, 300.0)],
    )
    bess_units = [
        BessUnitRecord(unit_id="B1", bus=99, power_mw=10.0, cyclic_soc=True),
    ]
    result = check_bess_bus_existence(bess_units, topology)

    assert result.status == CheckStatus.FAIL
    assert result.items_failed == 1
    assert any("99" in d for d in result.details)


# ---------------------------------------------------------------------------
# Test 3: BESS bus existence — rejects reference bus type
# ---------------------------------------------------------------------------


def test_check_bess_bus_existence_rejects_ref_bus_type() -> None:
    """BESS unit at bus 3 which has bus_type=3 (reference bus)."""
    topology = _make_topology(
        buses=[(1, 1, 100.0), (2, 2, 200.0), (3, 3, 300.0)],
    )
    bess_units = [
        BessUnitRecord(unit_id="B1", bus=3, power_mw=10.0, cyclic_soc=True),
    ]
    result = check_bess_bus_existence(bess_units, topology)

    assert result.status == CheckStatus.FAIL
    assert result.items_failed == 1
    assert any("bus type" in d.lower() or "invalid" in d.lower() for d in result.details)


# ---------------------------------------------------------------------------
# Test 4: DR bus existence — nonzero Pd
# ---------------------------------------------------------------------------


def test_check_dr_bus_existence_nonzero_pd() -> None:
    """Bus 10 has Pd=500, bus 20 has Pd=0. DR at both; bus 20 should fail."""
    topology = _make_topology(
        buses=[(10, 1, 500.0), (20, 1, 0.0)],
    )
    dr_buses = [
        DrBusRecord(dr_id="DR1", bus=10, max_curtail_mw=50.0),
        DrBusRecord(dr_id="DR2", bus=20, max_curtail_mw=25.0),
    ]
    result = check_dr_bus_existence(dr_buses, topology)

    assert result.status == CheckStatus.FAIL
    assert result.items_failed == 1
    assert result.items_checked == 2
    # bus 10 passes, bus 20 fails (zero Pd)
    assert any("20" in d for d in result.details)


# ---------------------------------------------------------------------------
# Test 5: Flowgate branch existence — all valid
# ---------------------------------------------------------------------------


def test_check_flowgate_branch_existence_all_valid() -> None:
    """Two flowgates with branch IDs [1,2] and [4,5], all exist."""
    topology = _make_topology(
        buses=[(1, 1, 100.0)],
        branches=[
            (1, 1, 2, 100.0),
            (2, 2, 3, 100.0),
            (3, 3, 4, 100.0),
            (4, 4, 5, 100.0),
            (5, 5, 6, 100.0),
        ],
    )
    flowgates = [
        FlowgateRecord(
            flowgate_id="FG1",
            branch_ids=[1, 2],
            weights=[1.0, 0.8],
            limit_mw=150.0,
            direction="both",
        ),
        FlowgateRecord(
            flowgate_id="FG2",
            branch_ids=[4, 5],
            weights=[1.0, 0.9],
            limit_mw=180.0,
            direction="both",
        ),
    ]
    result = check_flowgate_branch_existence(flowgates, topology)

    assert result.status == CheckStatus.PASS
    assert result.items_checked == 2
    assert result.items_failed == 0


# ---------------------------------------------------------------------------
# Test 6: Flowgate branch existence — missing branch
# ---------------------------------------------------------------------------


def test_check_flowgate_branch_existence_missing_branch() -> None:
    """Flowgate references branch 99 which doesn't exist."""
    topology = _make_topology(
        buses=[(1, 1, 100.0)],
        branches=[(1, 1, 2, 100.0), (2, 2, 3, 100.0), (3, 3, 4, 100.0)],
    )
    flowgates = [
        FlowgateRecord(
            flowgate_id="FG1",
            branch_ids=[1, 99],
            weights=[1.0, 0.8],
            limit_mw=80.0,
            direction="both",
        ),
    ]
    result = check_flowgate_branch_existence(flowgates, topology)

    assert result.status == CheckStatus.FAIL
    assert any("99" in d for d in result.details)


# ---------------------------------------------------------------------------
# Test 7: BESS fleet fraction — within range
# ---------------------------------------------------------------------------


def test_check_bess_fleet_fraction_within_range() -> None:
    """Total 380 MW BESS on 10000 MW peak = 3.8%, within [3%, 5%]."""
    topology = _make_topology(
        buses=[(1, 1, 10000.0)],
        system_peak_mw=10000.0,
    )
    bess_units = [
        BessUnitRecord(unit_id="B1", bus=1, power_mw=80.0, cyclic_soc=True),
        BessUnitRecord(unit_id="B2", bus=1, power_mw=90.0, cyclic_soc=True),
        BessUnitRecord(unit_id="B3", bus=1, power_mw=100.0, cyclic_soc=True),
        BessUnitRecord(unit_id="B4", bus=1, power_mw=110.0, cyclic_soc=True),
    ]
    result = check_bess_fleet_fraction(bess_units, topology)

    assert result.status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Test 8: BESS fleet fraction — below minimum
# ---------------------------------------------------------------------------


def test_check_bess_fleet_fraction_below_minimum() -> None:
    """Total 100 MW BESS on 10000 MW peak = 1.0%, below 3%."""
    topology = _make_topology(
        buses=[(1, 1, 10000.0)],
        system_peak_mw=10000.0,
    )
    bess_units = [
        BessUnitRecord(unit_id="B1", bus=1, power_mw=50.0, cyclic_soc=True),
        BessUnitRecord(unit_id="B2", bus=1, power_mw=50.0, cyclic_soc=True),
    ]
    result = check_bess_fleet_fraction(bess_units, topology)

    assert result.status == CheckStatus.FAIL
    assert any("3%" in d or "below" in d.lower() for d in result.details)


# ---------------------------------------------------------------------------
# Test 9: DR curtailment fraction — within range
# ---------------------------------------------------------------------------


def test_check_dr_curtailment_fraction_within_range() -> None:
    """Total 400 MW DR on 10000 MW peak = 4.0%, within [2%, 8%]."""
    topology = _make_topology(
        buses=[(1, 1, 10000.0)],
        system_peak_mw=10000.0,
    )
    # 6 DR buses, each ~66.7 MW, total 400 MW
    dr_buses = [DrBusRecord(dr_id=f"DR{i}", bus=1, max_curtail_mw=400.0 / 6) for i in range(6)]
    result = check_dr_curtailment_fraction(dr_buses, topology)

    assert result.status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Test 10: Flowgate limits — positive and bounded
# ---------------------------------------------------------------------------


def test_check_flowgate_limits_positive_and_bounded() -> None:
    """Test PASS with limit=800 < sum(rate_a)=900, and FAIL with limit=1000."""
    topology = _make_topology(
        buses=[(1, 1, 100.0)],
        branches=[(1, 1, 2, 500.0), (2, 2, 3, 400.0)],
    )

    # PASS case: 0 < 800 < 900
    fg_pass = FlowgateRecord(
        flowgate_id="FG1",
        branch_ids=[1, 2],
        weights=[1.0, 1.0],
        limit_mw=800.0,
        direction="both",
    )
    result_pass = check_flowgate_limits([fg_pass], topology)
    assert result_pass.status == CheckStatus.PASS

    # FAIL case: 1000 >= 900
    fg_fail = FlowgateRecord(
        flowgate_id="FG2",
        branch_ids=[1, 2],
        weights=[1.0, 1.0],
        limit_mw=1000.0,
        direction="both",
    )
    result_fail = check_flowgate_limits([fg_fail], topology)
    assert result_fail.status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# Test 11: BESS reserve eligibility — all present
# ---------------------------------------------------------------------------


def test_check_bess_reserve_eligibility_all_present() -> None:
    """All 3 BESS units have matching reserve eligibility entries."""
    bess_units = [
        BessUnitRecord(unit_id="BESS_SMALL_001", bus=1, power_mw=50.0, cyclic_soc=True),
        BessUnitRecord(unit_id="BESS_SMALL_002", bus=2, power_mw=60.0, cyclic_soc=True),
        BessUnitRecord(unit_id="BESS_SMALL_003", bus=3, power_mw=70.0, cyclic_soc=True),
    ]
    reserve_rows = [
        ReserveEligibilityRecord(
            gen_uid="BESS_SMALL_001",
            tech_class="bess",
            spinning_eligible=True,
            non_spinning_eligible=True,
        ),
        ReserveEligibilityRecord(
            gen_uid="BESS_SMALL_002",
            tech_class="bess",
            spinning_eligible=True,
            non_spinning_eligible=True,
        ),
        ReserveEligibilityRecord(
            gen_uid="BESS_SMALL_003",
            tech_class="bess",
            spinning_eligible=True,
            non_spinning_eligible=True,
        ),
    ]
    result = check_bess_reserve_eligibility(bess_units, reserve_rows)

    assert result.status == CheckStatus.PASS
    assert result.items_checked == 3
    assert result.items_failed == 0


# ---------------------------------------------------------------------------
# Test 12: BESS reserve eligibility — missing entry
# ---------------------------------------------------------------------------


def test_check_bess_reserve_eligibility_missing_entry() -> None:
    """2 BESS units but only 1 matching reserve eligibility entry."""
    bess_units = [
        BessUnitRecord(unit_id="BESS_SMALL_001", bus=1, power_mw=50.0, cyclic_soc=True),
        BessUnitRecord(unit_id="BESS_SMALL_002", bus=2, power_mw=60.0, cyclic_soc=True),
    ]
    reserve_rows = [
        ReserveEligibilityRecord(
            gen_uid="BESS_SMALL_001",
            tech_class="bess",
            spinning_eligible=True,
            non_spinning_eligible=True,
        ),
        # BESS_SMALL_002 is missing
    ]
    result = check_bess_reserve_eligibility(bess_units, reserve_rows)

    assert result.status == CheckStatus.FAIL
    assert result.items_failed == 1
    assert any("BESS_SMALL_002" in d for d in result.details)


# ---------------------------------------------------------------------------
# Test 13: BESS/DR overlap — disjoint
# ---------------------------------------------------------------------------


def test_check_no_bess_dr_overlap_disjoint() -> None:
    """BESS at buses {10,20,30}, DR at buses {40,50,60}. No overlap."""
    bess_units = [
        BessUnitRecord(unit_id="B1", bus=10, power_mw=50.0, cyclic_soc=True),
        BessUnitRecord(unit_id="B2", bus=20, power_mw=60.0, cyclic_soc=True),
        BessUnitRecord(unit_id="B3", bus=30, power_mw=70.0, cyclic_soc=True),
    ]
    dr_buses = [
        DrBusRecord(dr_id="DR1", bus=40, max_curtail_mw=25.0),
        DrBusRecord(dr_id="DR2", bus=50, max_curtail_mw=30.0),
        DrBusRecord(dr_id="DR3", bus=60, max_curtail_mw=35.0),
    ]
    result = check_no_bess_dr_overlap(bess_units, dr_buses)

    assert result.status == CheckStatus.PASS
    assert result.items_checked == 6  # 3 BESS + 3 DR unique buses
    assert result.items_failed == 0


# ---------------------------------------------------------------------------
# Test 14: BESS/DR overlap — shared bus
# ---------------------------------------------------------------------------


def test_check_no_bess_dr_overlap_shared_bus() -> None:
    """BESS at bus 10 and DR also at bus 10."""
    bess_units = [
        BessUnitRecord(unit_id="B1", bus=10, power_mw=50.0, cyclic_soc=True),
    ]
    dr_buses = [
        DrBusRecord(dr_id="DR1", bus=10, max_curtail_mw=25.0),
    ]
    result = check_no_bess_dr_overlap(bess_units, dr_buses)

    assert result.status == CheckStatus.FAIL
    assert any("10" in d for d in result.details)


# ---------------------------------------------------------------------------
# Test 15: Flowgate branch disjoint — no overlap
# ---------------------------------------------------------------------------


def test_check_flowgate_branch_disjoint_no_overlap() -> None:
    """3 flowgates with branch_ids [1,2], [3,4], [5]. All disjoint."""
    flowgates = [
        FlowgateRecord(
            flowgate_id="FG1",
            branch_ids=[1, 2],
            weights=[1.0, 0.8],
            limit_mw=100.0,
            direction="both",
        ),
        FlowgateRecord(
            flowgate_id="FG2",
            branch_ids=[3, 4],
            weights=[1.0, 0.7],
            limit_mw=120.0,
            direction="both",
        ),
        FlowgateRecord(
            flowgate_id="FG3", branch_ids=[5], weights=[1.0], limit_mw=80.0, direction="both"
        ),
    ]
    result = check_flowgate_branch_disjoint(flowgates)

    assert result.status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Test 16: Flowgate branch disjoint — overlap
# ---------------------------------------------------------------------------


def test_check_flowgate_branch_disjoint_overlap() -> None:
    """2 flowgates share branch 3: [1,2,3] and [3,4,5]."""
    flowgates = [
        FlowgateRecord(
            flowgate_id="FG1",
            branch_ids=[1, 2, 3],
            weights=[1.0, 0.8, 0.6],
            limit_mw=200.0,
            direction="both",
        ),
        FlowgateRecord(
            flowgate_id="FG2",
            branch_ids=[3, 4, 5],
            weights=[1.0, 0.9, 0.7],
            limit_mw=250.0,
            direction="both",
        ),
    ]
    result = check_flowgate_branch_disjoint(flowgates)

    assert result.status == CheckStatus.FAIL
    assert any("3" in d for d in result.details)
    assert any("FG1" in d and "FG2" in d for d in result.details)


# ---------------------------------------------------------------------------
# Test 17: Build validation report — overall pass
# ---------------------------------------------------------------------------


def test_build_validation_report_overall_pass() -> None:
    """Two networks with all PASS checks, cross-phase all true => overall PASS."""
    from scripts.phase3_validation import CheckResult as CR

    checks_small = [
        CR(
            check_id="a",
            check_name="test",
            category=CheckCategory.TOPOLOGICAL_INTEGRITY,
            status=CheckStatus.PASS,
            message="ok",
            details=[],
            items_checked=5,
            items_passed=5,
            items_failed=0,
        ),
    ]
    checks_medium = [
        CR(
            check_id="a",
            check_name="test",
            category=CheckCategory.TOPOLOGICAL_INTEGRITY,
            status=CheckStatus.PASS,
            message="ok",
            details=[],
            items_checked=3,
            items_passed=3,
            items_failed=0,
        ),
    ]

    nr_small = NetworkValidationResult(
        network_id="ACTIVSg2000",
        checks=checks_small,
        total_checks=1,
        passed=1,
        warned=0,
        failed=0,
        overall_pass=True,
    )
    nr_medium = NetworkValidationResult(
        network_id="ACTIVSg10k",
        checks=checks_medium,
        total_checks=1,
        passed=1,
        warned=0,
        failed=0,
        overall_pass=True,
    )

    cross_phase = CrossPhaseConsistencyResult(
        tiny_bess_columns=["unit_id", "bus_id"],
        phase3_bess_columns=["unit_id", "bus"],
        bess_column_match=True,
        tiny_flowgate_columns=["flowgate_id"],
        phase3_flowgate_columns=["flowgate_id"],
        flowgate_column_match=True,
        all_flowgate_limits_positive=True,
        all_bess_cyclic_soc_true=True,
        details=[],
    )

    report = build_validation_report([nr_small, nr_medium], cross_phase)

    assert report.overall_pass is True
    assert report.total_failed == 0


# ---------------------------------------------------------------------------
# Test 18: Build validation report — any fail blocks pass
# ---------------------------------------------------------------------------


def test_build_validation_report_any_fail_blocks_pass() -> None:
    """SMALL all PASS, MEDIUM has one FAIL => overall FAIL."""
    from scripts.phase3_validation import CheckResult as CR

    checks_small = [
        CR(
            check_id="a",
            check_name="test",
            category=CheckCategory.TOPOLOGICAL_INTEGRITY,
            status=CheckStatus.PASS,
            message="ok",
            details=[],
            items_checked=5,
            items_passed=5,
            items_failed=0,
        ),
    ]
    checks_medium = [
        CR(
            check_id="a",
            check_name="test",
            category=CheckCategory.TOPOLOGICAL_INTEGRITY,
            status=CheckStatus.FAIL,
            message="failed",
            details=["bus 99 missing"],
            items_checked=3,
            items_passed=2,
            items_failed=1,
        ),
    ]

    nr_small = NetworkValidationResult(
        network_id="ACTIVSg2000",
        checks=checks_small,
        total_checks=1,
        passed=1,
        warned=0,
        failed=0,
        overall_pass=True,
    )
    nr_medium = NetworkValidationResult(
        network_id="ACTIVSg10k",
        checks=checks_medium,
        total_checks=1,
        passed=0,
        warned=0,
        failed=1,
        overall_pass=False,
    )

    cross_phase = CrossPhaseConsistencyResult(
        tiny_bess_columns=[],
        phase3_bess_columns=[],
        bess_column_match=True,
        tiny_flowgate_columns=[],
        phase3_flowgate_columns=[],
        flowgate_column_match=True,
        all_flowgate_limits_positive=True,
        all_bess_cyclic_soc_true=True,
        details=[],
    )

    report = build_validation_report([nr_small, nr_medium], cross_phase)

    assert report.overall_pass is False
    assert report.total_failed >= 1
