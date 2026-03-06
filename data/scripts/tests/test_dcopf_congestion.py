"""Tests for DC OPF Congestion Analysis (PRD 05).

All 16 unit tests per PRD 05 success criteria. Self-contained tests with
synthetic data -- no external files or network calls required.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.dcopf_congestion import (
    BranchLoading,
    CongestionAnalysisResult,
    CongestionCandidate,
    CongestionNetworkId,
    LoadLevel,
    LoadLevelSelection,
    OPFRunResult,
    OPFSolverSettings,
    cluster_congested_corridors,
    generate_octave_script,
    identify_congestion_candidates,
    parse_branch_loading_csv,
    select_load_level_hours,
    write_branch_loading_csv,
    write_calibration_log,
    write_congestion_candidates_csv,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_branch_loading(
    branch_idx: int,
    from_bus: int = 1,
    to_bus: int = 2,
    flow_mw: float = 100.0,
    rate_a_mw: float = 500.0,
    utilization: float | None = None,
) -> BranchLoading:
    """Helper to create a BranchLoading with computed utilization."""
    if utilization is None:
        utilization = flow_mw / rate_a_mw if rate_a_mw > 0 else 0.0
    return BranchLoading(
        branch_idx=branch_idx,
        from_bus=from_bus,
        to_bus=to_bus,
        flow_mw=flow_mw,
        rate_a_mw=rate_a_mw,
        utilization=utilization,
    )


def _make_opf_result(
    network_id: CongestionNetworkId,
    load_level: LoadLevel,
    branch_loadings: list[BranchLoading],
    converged: bool = True,
) -> OPFRunResult:
    """Helper to create an OPFRunResult."""
    return OPFRunResult(
        network_id=network_id,
        load_level=load_level,
        load_multiplier=1.0,
        system_load_mw=10000.0,
        converged=converged,
        objective_value=500000.0,
        branch_count=len(branch_loadings),
        branch_loadings=branch_loadings,
    )


def _make_candidate(
    branch_idx: int,
    from_bus: int,
    to_bus: int,
    rate_a_mw: float = 500.0,
    utilization_peak: float = 0.85,
    utilization_shoulder: float = 0.70,
    utilization_valley: float = 0.50,
) -> CongestionCandidate:
    """Helper to create a CongestionCandidate."""
    max_util = max(utilization_peak, utilization_shoulder, utilization_valley)
    if max_util == utilization_peak:
        binding = LoadLevel.PEAK
    elif max_util == utilization_shoulder:
        binding = LoadLevel.SHOULDER
    else:
        binding = LoadLevel.VALLEY

    return CongestionCandidate(
        branch_idx=branch_idx,
        from_bus=from_bus,
        to_bus=to_bus,
        rate_a_mw=rate_a_mw,
        utilization_peak=utilization_peak,
        utilization_shoulder=utilization_shoulder,
        utilization_valley=utilization_valley,
        max_utilization=max_util,
        binding_load_level=binding,
    )


# ---------------------------------------------------------------------------
# Test 1: select_load_level_hours returns three levels
# ---------------------------------------------------------------------------


def test_select_load_level_hours_returns_three_levels() -> None:
    """Construct a synthetic 24-element system hourly load vector with a known
    peak at HR_17 (45000 MW for SMALL-scale), a value near 75% at HR_10
    (~33750 MW), and a value near 55% at HR_4 (~24750 MW). Verify it returns
    exactly three LoadLevelSelection objects with PEAK at HR_17 and
    multiplier = 1.0.
    """
    # Build a synthetic 24-hour profile with known peak at HR_17 (index 16)
    profile = [20000.0] * 24
    profile[16] = 45000.0  # HR_17 = peak
    profile[9] = 33750.0  # HR_10 ~ 75% of peak
    profile[3] = 24750.0  # HR_4 ~ 55% of peak

    selections = select_load_level_hours(profile)

    assert len(selections) == 3

    peak_sel = next(s for s in selections if s.load_level == LoadLevel.PEAK)
    assert peak_sel.hour_ending == 17
    assert peak_sel.load_multiplier == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Test 2: shoulder and valley multipliers within tolerance
# ---------------------------------------------------------------------------


def test_select_load_level_hours_shoulder_valley_within_tolerance() -> None:
    """Using a synthetic profile, verify shoulder multiplier in [0.70, 0.80]
    and valley multiplier in [0.50, 0.60].
    """
    profile = [20000.0] * 24
    profile[16] = 45000.0  # peak
    profile[9] = 33750.0  # ~75% of peak
    profile[3] = 24750.0  # ~55% of peak

    selections = select_load_level_hours(profile)

    shoulder_sel = next(s for s in selections if s.load_level == LoadLevel.SHOULDER)
    valley_sel = next(s for s in selections if s.load_level == LoadLevel.VALLEY)

    assert 0.70 <= shoulder_sel.load_multiplier <= 0.80
    assert 0.50 <= valley_sel.load_multiplier <= 0.60


# ---------------------------------------------------------------------------
# Test 3: rejects non-24-element lists
# ---------------------------------------------------------------------------


def test_select_load_level_hours_rejects_non_24_elements() -> None:
    """Call select_load_level_hours with a 23-element list and verify ValueError."""
    with pytest.raises(ValueError, match="24"):
        select_load_level_hours([100.0] * 23)


# ---------------------------------------------------------------------------
# Test 4: parse_branch_loading_csv correct count
# ---------------------------------------------------------------------------


def test_parse_branch_loading_csv_correct_count(tmp_path: Path) -> None:
    """Write a synthetic branch loading CSV with 500 rows, parse it, and
    verify it returns exactly 500 BranchLoading records with branch_idx
    values 1 through 500.
    """
    csv_path = tmp_path / "branch_loading.csv"
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["branch_idx", "from_bus", "to_bus", "flow_mw", "rate_a_mw", "utilization"])
        for i in range(1, 501):
            writer.writerow([i, i * 10, i * 10 + 1, 100.0, 500.0, 0.2000])

    loadings = parse_branch_loading_csv(csv_path)

    assert len(loadings) == 500
    assert [bl.branch_idx for bl in loadings] == list(range(1, 501))


# ---------------------------------------------------------------------------
# Test 5: parse_branch_loading_csv utilization computed
# ---------------------------------------------------------------------------


def test_parse_branch_loading_csv_utilization_computed(tmp_path: Path) -> None:
    """Write a CSV where branch 42 has flow_mw=240.0 and rate_a_mw=300.0,
    parse it, and verify utilization for branch 42 equals 0.80.
    """
    csv_path = tmp_path / "branch_loading.csv"
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["branch_idx", "from_bus", "to_bus", "flow_mw", "rate_a_mw", "utilization"])
        # Write a few branches including branch 42
        for i in range(1, 51):
            if i == 42:
                writer.writerow([42, 420, 421, 240.0, 300.0, 0.8000])
            else:
                writer.writerow([i, i * 10, i * 10 + 1, 50.0, 500.0, 0.1000])

    loadings = parse_branch_loading_csv(csv_path)
    branch_42 = next(bl for bl in loadings if bl.branch_idx == 42)

    assert branch_42.utilization == pytest.approx(0.80, abs=0.001)


# ---------------------------------------------------------------------------
# Test 6: identify_congestion_candidates threshold filtering
# ---------------------------------------------------------------------------


def test_identify_congestion_candidates_threshold_filtering() -> None:
    """Construct three synthetic OPFRunResult objects with 500 branches each,
    where branches 10, 25, 42, 99, 200, and 350 have utilization >= 0.80
    at peak. Verify exactly 6 candidates are returned.
    """
    congested_indices = {10, 25, 42, 99, 200, 350}
    network_id = CongestionNetworkId.SMALL

    def make_loadings(level: LoadLevel) -> list[BranchLoading]:
        result = []
        for i in range(1, 501):
            if i in congested_indices and level == LoadLevel.PEAK:
                result.append(_make_branch_loading(i, flow_mw=420.0, rate_a_mw=500.0))
            else:
                result.append(_make_branch_loading(i, flow_mw=100.0, rate_a_mw=500.0))
        return result

    opf_results = [
        _make_opf_result(network_id, LoadLevel.PEAK, make_loadings(LoadLevel.PEAK)),
        _make_opf_result(network_id, LoadLevel.SHOULDER, make_loadings(LoadLevel.SHOULDER)),
        _make_opf_result(network_id, LoadLevel.VALLEY, make_loadings(LoadLevel.VALLEY)),
    ]

    candidates = identify_congestion_candidates(opf_results, threshold=0.80)

    assert len(candidates) == 6
    candidate_indices = {c.branch_idx for c in candidates}
    assert candidate_indices == congested_indices


# ---------------------------------------------------------------------------
# Test 7: candidates sorted by max_utilization descending
# ---------------------------------------------------------------------------


def test_identify_congestion_candidates_sorted_by_max_util() -> None:
    """Set branch 42's max utilization to 0.97, branches 10 and 25 to
    0.85 and 0.82. Verify candidates sorted descending with branch 42 first.
    """
    network_id = CongestionNetworkId.SMALL

    # Specific utilization values for test branches
    branch_utils: dict[int, float] = {
        10: 0.85,
        25: 0.82,
        42: 0.97,
        99: 0.81,
        200: 0.80,
        350: 0.83,
    }

    def make_loadings(level: LoadLevel) -> list[BranchLoading]:
        result = []
        for i in range(1, 501):
            if i in branch_utils and level == LoadLevel.PEAK:
                util = branch_utils[i]
                flow = util * 500.0
                result.append(_make_branch_loading(i, flow_mw=flow, rate_a_mw=500.0))
            else:
                result.append(_make_branch_loading(i, flow_mw=100.0, rate_a_mw=500.0))
        return result

    opf_results = [
        _make_opf_result(network_id, LoadLevel.PEAK, make_loadings(LoadLevel.PEAK)),
        _make_opf_result(network_id, LoadLevel.SHOULDER, make_loadings(LoadLevel.SHOULDER)),
        _make_opf_result(network_id, LoadLevel.VALLEY, make_loadings(LoadLevel.VALLEY)),
    ]

    candidates = identify_congestion_candidates(opf_results, threshold=0.80)

    assert candidates[0].branch_idx == 42
    assert candidates[0].max_utilization == pytest.approx(0.97, abs=0.01)

    # Verify descending order
    for i in range(len(candidates) - 1):
        assert candidates[i].max_utilization >= candidates[i + 1].max_utilization


# ---------------------------------------------------------------------------
# Test 8: rejects non-converged OPF
# ---------------------------------------------------------------------------


def test_identify_congestion_candidates_rejects_non_converged() -> None:
    """Construct an OPFRunResult with converged=False and verify ValueError."""
    network_id = CongestionNetworkId.SMALL
    loadings = [_make_branch_loading(i) for i in range(1, 11)]

    opf_results = [
        _make_opf_result(network_id, LoadLevel.PEAK, loadings, converged=False),
        _make_opf_result(network_id, LoadLevel.SHOULDER, loadings),
        _make_opf_result(network_id, LoadLevel.VALLEY, loadings),
    ]

    with pytest.raises(ValueError, match="did not converge"):
        identify_congestion_candidates(opf_results)


# ---------------------------------------------------------------------------
# Test 9: cluster adjacent branches
# ---------------------------------------------------------------------------


def test_cluster_congested_corridors_adjacent_branches() -> None:
    """Create three candidate branches: A (100->200), B (200->300), C (500->600).
    A and B share bus 200; C is disjoint. Verify two corridors.
    """
    a = _make_candidate(1, from_bus=100, to_bus=200)
    b = _make_candidate(2, from_bus=200, to_bus=300)
    c = _make_candidate(3, from_bus=500, to_bus=600)

    corridors = cluster_congested_corridors([a, b, c])

    assert len(corridors) == 2

    # Find corridor containing A and B
    ab_corridor = None
    c_corridor = None
    for cor in corridors:
        branch_indices = {br.branch_idx for br in cor.branches}
        if 1 in branch_indices and 2 in branch_indices:
            ab_corridor = cor
        elif 3 in branch_indices:
            c_corridor = cor

    assert ab_corridor is not None
    assert ab_corridor.branch_count == 2
    assert c_corridor is not None
    assert c_corridor.branch_count == 1


# ---------------------------------------------------------------------------
# Test 10: transitive closure
# ---------------------------------------------------------------------------


def test_cluster_congested_corridors_transitive_closure() -> None:
    """Create three candidate branches: A (10->20), B (20->30), C (30->40).
    A-B share bus 20, B-C share bus 30. All should be in one corridor.
    """
    a = _make_candidate(1, from_bus=10, to_bus=20)
    b = _make_candidate(2, from_bus=20, to_bus=30)
    c = _make_candidate(3, from_bus=30, to_bus=40)

    corridors = cluster_congested_corridors([a, b, c])

    assert len(corridors) == 1
    assert corridors[0].branch_count == 3


# ---------------------------------------------------------------------------
# Test 11: all disjoint
# ---------------------------------------------------------------------------


def test_cluster_congested_corridors_all_disjoint() -> None:
    """Create four candidate branches with no shared buses.
    Verify 4 single-branch corridors.
    """
    candidates = [
        _make_candidate(1, from_bus=10, to_bus=20),
        _make_candidate(2, from_bus=30, to_bus=40),
        _make_candidate(3, from_bus=50, to_bus=60),
        _make_candidate(4, from_bus=70, to_bus=80),
    ]

    corridors = cluster_congested_corridors(candidates)

    assert len(corridors) == 4
    for cor in corridors:
        assert cor.branch_count == 1


# ---------------------------------------------------------------------------
# Test 12: write_branch_loading_csv columns and format
# ---------------------------------------------------------------------------


def test_write_branch_loading_csv_columns_and_format(tmp_path: Path) -> None:
    """Create 10 BranchLoading records, write via write_branch_loading_csv,
    read back and verify: (a) 6 columns, (b) 10 rows, (c) flow_mw has 4
    decimal places, (d) rate_a_mw is an integer string.
    """
    loadings = [
        _make_branch_loading(
            i, from_bus=i * 10, to_bus=i * 10 + 1, flow_mw=123.4567, rate_a_mw=500.0
        )
        for i in range(1, 11)
    ]

    csv_path = tmp_path / "branch_loading.csv"
    write_branch_loading_csv(loadings, csv_path)

    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert reader.fieldnames is not None
    assert set(reader.fieldnames) == {
        "branch_idx",
        "from_bus",
        "to_bus",
        "flow_mw",
        "rate_a_mw",
        "utilization",
    }
    assert len(rows) == 10

    # Check flow_mw has 4 decimal places
    flow_str = rows[0]["flow_mw"]
    assert "." in flow_str
    decimal_places = len(flow_str.split(".")[1])
    assert decimal_places == 4

    # Check rate_a_mw is integer string
    rate_str = rows[0]["rate_a_mw"]
    assert rate_str == "500"


# ---------------------------------------------------------------------------
# Test 13: write_congestion_candidates_csv includes corridor_id
# ---------------------------------------------------------------------------


def test_write_congestion_candidates_csv_includes_corridor_id(tmp_path: Path) -> None:
    """Create 5 candidate branches in 2 corridors, write via
    write_congestion_candidates_csv, read back, and verify corridor_group_id
    column exists with correct assignments.
    """
    # Two corridors: corridor 1 = branches 1,2 (shared bus 200)
    # corridor 2 = branches 3,4,5 (shared buses 500, 600)
    candidates = [
        _make_candidate(1, from_bus=100, to_bus=200, utilization_peak=0.95),
        _make_candidate(2, from_bus=200, to_bus=300, utilization_peak=0.90),
        _make_candidate(3, from_bus=400, to_bus=500, utilization_peak=0.88),
        _make_candidate(4, from_bus=500, to_bus=600, utilization_peak=0.85),
        _make_candidate(5, from_bus=600, to_bus=700, utilization_peak=0.82),
    ]

    corridors = cluster_congested_corridors(candidates)

    csv_path = tmp_path / "congestion_candidates.csv"
    write_congestion_candidates_csv(candidates, corridors, csv_path)

    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert "corridor_group_id" in reader.fieldnames  # type: ignore[operator]
    assert len(rows) == 5

    # All rows should have a non-zero corridor_group_id
    for row in rows:
        assert int(row["corridor_group_id"]) > 0

    # Branches 1 and 2 should share the same corridor_group_id
    b1_cid = int(rows[0]["corridor_group_id"])
    b2_cid = int(rows[1]["corridor_group_id"])
    assert b1_cid == b2_cid

    # Branches 3, 4, 5 should share a different corridor_group_id
    b3_cid = int(rows[2]["corridor_group_id"])
    b4_cid = int(rows[3]["corridor_group_id"])
    b5_cid = int(rows[4]["corridor_group_id"])
    assert b3_cid == b4_cid == b5_cid
    assert b1_cid != b3_cid


# ---------------------------------------------------------------------------
# Test 14: generate_octave_script contains rundcopf
# ---------------------------------------------------------------------------


def test_generate_octave_script_contains_rundcopf() -> None:
    """Call generate_octave_script with a load_multiplier of 0.75 and verify
    the script contains 'rundcopf' and '0.75'.
    """
    script = generate_octave_script(
        cleaned_m_path=Path("/tmp/case.m"),
        matpower_path=Path("/opt/matpower8.1"),
        output_csv_path=Path("/tmp/output.csv"),
        load_multiplier=0.75,
        solver_settings=OPFSolverSettings(),
    )

    assert "rundcopf" in script
    assert "0.75" in script


# ---------------------------------------------------------------------------
# Test 15: generate_octave_script contains path setup
# ---------------------------------------------------------------------------


def test_generate_octave_script_contains_path_setup() -> None:
    """Call generate_octave_script with matpower_path='/opt/matpower8.1' and
    verify the script contains an addpath call referencing that path.
    """
    script = generate_octave_script(
        cleaned_m_path=Path("/tmp/case.m"),
        matpower_path=Path("/opt/matpower8.1"),
        output_csv_path=Path("/tmp/output.csv"),
        load_multiplier=1.0,
        solver_settings=OPFSolverSettings(),
    )

    assert "addpath" in script
    assert "/opt/matpower8.1" in script


# ---------------------------------------------------------------------------
# Test 16: calibration log contains required keys
# ---------------------------------------------------------------------------


def test_calibration_log_contains_required_keys(tmp_path: Path) -> None:
    """Build a synthetic CongestionAnalysisResult and write a calibration log.
    Read back JSON and verify required keys.
    """
    network_id = CongestionNetworkId.SMALL
    loadings = [_make_branch_loading(i) for i in range(1, 11)]

    opf_results = [
        _make_opf_result(network_id, LoadLevel.PEAK, loadings),
        _make_opf_result(network_id, LoadLevel.SHOULDER, loadings),
        _make_opf_result(network_id, LoadLevel.VALLEY, loadings),
    ]

    load_level_selections = [
        LoadLevelSelection(LoadLevel.PEAK, 17, 45000.0, 1.0),
        LoadLevelSelection(LoadLevel.SHOULDER, 10, 33750.0, 0.75),
        LoadLevelSelection(LoadLevel.VALLEY, 4, 24750.0, 0.55),
    ]

    candidates = [_make_candidate(1, 100, 200)]
    corridors = cluster_congested_corridors(candidates)

    result = CongestionAnalysisResult(
        network_id=network_id,
        opf_results=opf_results,
        load_level_selections=load_level_selections,
        congestion_threshold=0.80,
        candidates=candidates,
        corridors=corridors,
        branch_loading_csv_paths={
            LoadLevel.PEAK: "branch_loading_peak.csv",
            LoadLevel.SHOULDER: "branch_loading_shoulder.csv",
            LoadLevel.VALLEY: "branch_loading_valley.csv",
        },
        congestion_candidates_csv_path="congestion_candidates.csv",
        calibration_log_json_path="calibration_log.json",
        octave_script_paths={
            LoadLevel.PEAK: "run_dcopf_peak.m",
            LoadLevel.SHOULDER: "run_dcopf_shoulder.m",
            LoadLevel.VALLEY: "run_dcopf_valley.m",
        },
    )

    log_path = tmp_path / "calibration_log.json"
    write_calibration_log(result, OPFSolverSettings(), log_path)

    with open(log_path) as fh:
        log_data = json.load(fh)

    required_keys = {
        "network_id",
        "solver_settings",
        "load_levels",
        "opf_runs",
        "congestion_threshold",
        "candidate_count",
        "corridors",
    }
    assert required_keys <= set(log_data.keys())
