"""Tests for flowgate_definition.py -- Phase 3 PRD 06."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.dcopf_congestion import (
    BranchLoading,
    CongestedCorridor,
    CongestionCandidate,
    LoadLevel,
)
from scripts.flowgate_definition import (
    FlowgateBranch,
    FlowgateDefinition,
    FlowgateDirection,
    FlowgateWeight,
    compute_flowgate_weights,
    compute_weighted_flow_sum,
    define_flowgates,
    define_single_flowgate,
    load_congestion_candidates_csv,
    reconstruct_corridors,
    select_flowgate_corridors,
    write_flowgates_csv,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candidate(
    branch_idx: int,
    from_bus: int,
    to_bus: int,
    rate_a: float = 500.0,
    util_peak: float = 0.85,
    util_shoulder: float = 0.60,
    util_valley: float = 0.40,
    corridor_group_id: int | None = 1,
) -> CongestionCandidate:
    """Create a CongestionCandidate for testing."""
    max_util = max(util_peak, util_shoulder, util_valley)
    if max_util == util_peak:
        binding = LoadLevel.PEAK
    elif max_util == util_shoulder:
        binding = LoadLevel.SHOULDER
    else:
        binding = LoadLevel.VALLEY
    return CongestionCandidate(
        branch_idx=branch_idx,
        from_bus=from_bus,
        to_bus=to_bus,
        rate_a_mw=rate_a,
        utilization_peak=util_peak,
        utilization_shoulder=util_shoulder,
        utilization_valley=util_valley,
        max_utilization=max_util,
        binding_load_level=binding,
        corridor_group_id=corridor_group_id,
    )


def _make_corridor(
    corridor_id: int,
    candidates: list[CongestionCandidate],
) -> CongestedCorridor:
    """Create a CongestedCorridor from candidates."""
    max_util = max(c.max_utilization for c in candidates)
    binding_branch = max(candidates, key=lambda c: c.max_utilization)

    bus_counts: dict[int, int] = {}
    for c in candidates:
        bus_counts[c.from_bus] = bus_counts.get(c.from_bus, 0) + 1
        bus_counts[c.to_bus] = bus_counts.get(c.to_bus, 0) + 1
    shared = sorted(b for b, count in bus_counts.items() if count > 1)

    return CongestedCorridor(
        corridor_id=corridor_id,
        branches=candidates,
        shared_buses=shared,
        max_utilization=max_util,
        binding_load_level=binding_branch.binding_load_level,
        branch_count=len(candidates),
    )


def _make_branch_loading(
    branch_idx: int,
    from_bus: int,
    to_bus: int,
    flow_mw: float,
    rate_a: float = 500.0,
) -> BranchLoading:
    """Create a BranchLoading for testing."""
    return BranchLoading(
        branch_idx=branch_idx,
        from_bus=from_bus,
        to_bus=to_bus,
        flow_mw=flow_mw,
        rate_a_mw=rate_a,
        utilization=abs(flow_mw) / rate_a if rate_a > 0 else 0.0,
    )


def _write_candidates_csv(path: Path, candidates: list[CongestionCandidate]) -> None:
    """Write a synthetic congestion_candidates.csv."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "branch_idx",
                "from_bus",
                "to_bus",
                "rate_a_mw",
                "utilization_peak",
                "utilization_shoulder",
                "utilization_valley",
                "max_utilization",
                "binding_load_level",
                "corridor_group_id",
            ]
        )
        for c in candidates:
            writer.writerow(
                [
                    c.branch_idx,
                    c.from_bus,
                    c.to_bus,
                    int(c.rate_a_mw),
                    f"{c.utilization_peak:.4f}",
                    f"{c.utilization_shoulder:.4f}",
                    f"{c.utilization_valley:.4f}",
                    f"{c.max_utilization:.4f}",
                    c.binding_load_level.value,
                    c.corridor_group_id if c.corridor_group_id is not None else "",
                ]
            )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoadCongestionCandidatesCsv:
    """Tests for load_congestion_candidates_csv."""

    def test_load_congestion_candidates_csv_correct_count(self, tmp_path: Path) -> None:
        """12-row synthetic CSV returns exactly 12 CongestionCandidate records."""
        candidates = [
            _make_candidate(
                branch_idx=i + 1,
                from_bus=100 + i,
                to_bus=200 + i,
                util_peak=0.85 + i * 0.01,
                corridor_group_id=(i % 3) + 1,
            )
            for i in range(12)
        ]

        csv_path = tmp_path / "congestion_candidates.csv"
        _write_candidates_csv(csv_path, candidates)

        result = load_congestion_candidates_csv(csv_path)

        assert len(result) == 12
        # All should have corridor_group_id populated
        for c in result:
            assert c.corridor_group_id is not None


class TestReconstructCorridors:
    """Tests for reconstruct_corridors."""

    def test_reconstruct_corridors_groups_by_id(self) -> None:
        """8 candidates with 3 corridor groups produce 3 CongestedCorridor objects."""
        candidates = [
            # Corridor 1: 3 branches (highest utilization)
            _make_candidate(1, 100, 200, util_peak=0.95, corridor_group_id=1),
            _make_candidate(2, 100, 300, util_peak=0.90, corridor_group_id=1),
            _make_candidate(3, 200, 300, util_peak=0.88, corridor_group_id=1),
            # Corridor 2: 3 branches
            _make_candidate(4, 400, 500, util_peak=0.85, corridor_group_id=2),
            _make_candidate(5, 400, 600, util_peak=0.83, corridor_group_id=2),
            _make_candidate(6, 500, 600, util_peak=0.82, corridor_group_id=2),
            # Corridor 3: 2 branches (lowest utilization)
            _make_candidate(7, 700, 800, util_peak=0.81, corridor_group_id=3),
            _make_candidate(8, 700, 900, util_peak=0.80, corridor_group_id=3),
        ]

        corridors = reconstruct_corridors(candidates)

        assert len(corridors) == 3
        # Sorted by max_utilization descending
        branch_counts = [c.branch_count for c in corridors]
        assert branch_counts == [3, 3, 2]
        assert corridors[0].max_utilization > corridors[1].max_utilization
        assert corridors[1].max_utilization > corridors[2].max_utilization

    def test_reconstruct_corridors_rejects_none_corridor_id(self) -> None:
        """Candidate with corridor_group_id=None raises ValueError."""
        candidates = [
            _make_candidate(1, 100, 200, corridor_group_id=None),
        ]

        with pytest.raises(ValueError, match="corridor_group_id=None"):
            reconstruct_corridors(candidates)


class TestSelectFlowgateCorridors:
    """Tests for select_flowgate_corridors."""

    def test_select_flowgate_corridors_top_five(self) -> None:
        """8 corridors with max_flowgates=5 selects top 5, excludes 3."""
        corridors = [
            _make_corridor(
                i + 1,
                [_make_candidate(i + 1, 100 * i, 100 * i + 1, util_peak=0.99 - i * 0.02)],
            )
            for i in range(8)
        ]

        selected, excluded = select_flowgate_corridors(corridors, max_flowgates=5)

        assert len(selected) == 5
        assert len(excluded) == 3
        # Selected should be the top 5 by max_utilization
        assert selected[0].max_utilization >= selected[4].max_utilization
        # Excluded should be the bottom 3
        assert excluded[0].max_utilization <= selected[-1].max_utilization

    def test_select_flowgate_corridors_fewer_than_min(self) -> None:
        """2 corridors with min_flowgates=3 selects all 2, no error."""
        corridors = [
            _make_corridor(
                i + 1,
                [_make_candidate(i + 1, 100 * i, 100 * i + 1, util_peak=0.90 - i * 0.05)],
            )
            for i in range(2)
        ]

        selected, excluded = select_flowgate_corridors(corridors, min_flowgates=3)

        assert len(selected) == 2
        assert len(excluded) == 0

    def test_select_flowgate_corridors_rejects_empty(self) -> None:
        """Empty corridor list raises ValueError."""
        with pytest.raises(ValueError, match="No congestion corridors"):
            select_flowgate_corridors([])


class TestComputeFlowgateWeights:
    """Tests for compute_flowgate_weights."""

    def test_compute_flowgate_weights_single_branch(self) -> None:
        """Single-branch corridor gets normalized_weight=1.0."""
        candidate = _make_candidate(42, 100, 200, util_peak=0.90)
        corridor = _make_corridor(1, [candidate])

        branch_loadings = {
            "peak": [_make_branch_loading(42, 100, 200, flow_mw=450.0)],
            "shoulder": [_make_branch_loading(42, 100, 200, flow_mw=300.0)],
            "valley": [_make_branch_loading(42, 100, 200, flow_mw=200.0)],
        }

        weights = compute_flowgate_weights(corridor, branch_loadings)

        assert len(weights) == 1
        assert weights[0].normalized_weight == 1.0
        assert weights[0].branch_idx == 42

    def test_compute_flowgate_weights_multi_branch(self) -> None:
        """Two-branch corridor: A=400 MW, B=300 MW => weights 1.0, 0.75."""
        cand_a = _make_candidate(10, 100, 200, util_peak=0.90, corridor_group_id=1)
        cand_b = _make_candidate(11, 100, 300, util_peak=0.85, corridor_group_id=1)
        corridor = _make_corridor(1, [cand_a, cand_b])

        branch_loadings = {
            "peak": [
                _make_branch_loading(10, 100, 200, flow_mw=400.0),
                _make_branch_loading(11, 100, 300, flow_mw=300.0),
            ],
            "shoulder": [
                _make_branch_loading(10, 100, 200, flow_mw=250.0),
                _make_branch_loading(11, 100, 300, flow_mw=200.0),
            ],
            "valley": [
                _make_branch_loading(10, 100, 200, flow_mw=150.0),
                _make_branch_loading(11, 100, 300, flow_mw=100.0),
            ],
        }

        weights = compute_flowgate_weights(corridor, branch_loadings)

        assert len(weights) == 2
        # Sorted by branch_idx
        w_a = next(w for w in weights if w.branch_idx == 10)
        w_b = next(w for w in weights if w.branch_idx == 11)

        assert w_a.normalized_weight == 1.0
        assert w_b.normalized_weight == pytest.approx(0.75, abs=1e-6)

    def test_compute_flowgate_weights_rejects_zero_flow(self) -> None:
        """All-zero flows at binding level raises ValueError."""
        candidate = _make_candidate(42, 100, 200, util_peak=0.90)
        corridor = _make_corridor(1, [candidate])

        branch_loadings = {
            "peak": [_make_branch_loading(42, 100, 200, flow_mw=0.0)],
            "shoulder": [_make_branch_loading(42, 100, 200, flow_mw=0.0)],
            "valley": [_make_branch_loading(42, 100, 200, flow_mw=0.0)],
        }

        with pytest.raises(ValueError, match="All branch flows are zero"):
            compute_flowgate_weights(corridor, branch_loadings)


class TestComputeWeightedFlowSum:
    """Tests for compute_weighted_flow_sum."""

    def test_compute_weighted_flow_sum(self) -> None:
        """Two branches: 1.0*400.0 + 0.75*300.0 = 625.0."""
        weights = [
            FlowgateWeight(
                branch_idx=10,
                from_bus=100,
                to_bus=200,
                flow_mw=400.0,
                raw_weight=1.0,
                normalized_weight=1.0,
            ),
            FlowgateWeight(
                branch_idx=11,
                from_bus=100,
                to_bus=300,
                flow_mw=300.0,
                raw_weight=0.75,
                normalized_weight=0.75,
            ),
        ]

        loadings = [
            _make_branch_loading(10, 100, 200, flow_mw=400.0),
            _make_branch_loading(11, 100, 300, flow_mw=300.0),
        ]

        result = compute_weighted_flow_sum(weights, loadings)

        assert result == pytest.approx(625.0, abs=1e-6)


class TestDefineSingleFlowgate:
    """Tests for define_single_flowgate."""

    def test_define_single_flowgate_limit_95_pct(self) -> None:
        """Single-branch, max flow 500 MW at peak => limit = 475.0 MW."""
        candidate = _make_candidate(42, 100, 200, util_peak=0.95)
        corridor = _make_corridor(1, [candidate])

        branch_loadings = {
            "peak": [_make_branch_loading(42, 100, 200, flow_mw=500.0)],
            "shoulder": [_make_branch_loading(42, 100, 200, flow_mw=350.0)],
            "valley": [_make_branch_loading(42, 100, 200, flow_mw=250.0)],
        }

        fg = define_single_flowgate(corridor, 1, branch_loadings, limit_factor=0.95)

        assert fg.limit_mw == pytest.approx(475.0, abs=1e-6)
        assert fg.calibration_load_level == "peak"
        assert fg.flowgate_id == "FG_1"
        assert fg.max_observed_flow_mw == pytest.approx(500.0, abs=1e-6)


class TestDefineFlowgates:
    """Tests for define_flowgates."""

    def test_define_flowgates_sequential_ids(self) -> None:
        """4 corridors produce FG_1, FG_2, FG_3, FG_4."""
        corridors = []
        branch_loadings: dict[str, list[BranchLoading]] = {
            "peak": [],
            "shoulder": [],
            "valley": [],
        }

        for i in range(4):
            cand = _make_candidate(
                i + 1, 100 * (i + 1), 100 * (i + 1) + 50, util_peak=0.95 - i * 0.02
            )
            corridors.append(_make_corridor(i + 1, [cand]))
            for level in ("peak", "shoulder", "valley"):
                flow = 500.0 - i * 50 if level == "peak" else 300.0 - i * 30
                branch_loadings[level].append(
                    _make_branch_loading(i + 1, 100 * (i + 1), 100 * (i + 1) + 50, flow_mw=flow)
                )

        flowgates = define_flowgates(corridors, branch_loadings)

        assert len(flowgates) == 4
        ids = [fg.flowgate_id for fg in flowgates]
        assert ids == ["FG_1", "FG_2", "FG_3", "FG_4"]


class TestWriteFlowgatesCsv:
    """Tests for write_flowgates_csv."""

    def test_write_flowgates_csv_columns_and_format(self, tmp_path: Path) -> None:
        """CSV has 7 correct columns, semicolons for multi-branch, correct format."""
        fg_single = FlowgateDefinition(
            flowgate_id="FG_1",
            flowgate_name="Bus100-Bus200",
            branches=[FlowgateBranch(branch_idx=42, from_bus=100, to_bus=200, weight=1.0)],
            limit_mw=475.0,
            direction=FlowgateDirection.BOTH,
            calibration_load_level="peak",
            max_observed_flow_mw=500.0,
        )
        fg_multi = FlowgateDefinition(
            flowgate_id="FG_2",
            flowgate_name="Corridor_100-200_100-300",
            branches=[
                FlowgateBranch(branch_idx=42, from_bus=100, to_bus=200, weight=1.0),
                FlowgateBranch(branch_idx=43, from_bus=100, to_bus=300, weight=0.75),
            ],
            limit_mw=593.8,
            direction=FlowgateDirection.BOTH,
            calibration_load_level="shoulder",
            max_observed_flow_mw=625.0,
        )

        csv_path = tmp_path / "flowgates.csv"
        write_flowgates_csv([fg_single, fg_multi], csv_path)

        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames is not None
            # (a) Exactly 7 columns
            assert len(reader.fieldnames) == 7
            expected_cols = {
                "flowgate_id",
                "flowgate_name",
                "branch_id_list",
                "weight_list",
                "limit_mw",
                "direction",
                "calibration_load_level",
            }
            assert set(reader.fieldnames) == expected_cols

            rows = list(reader)
            assert len(rows) == 2

            # (b) Multi-branch: semicolon-separated
            multi_row = rows[1]
            assert multi_row["branch_id_list"] == "42;43"
            assert multi_row["weight_list"] == "1.00;0.75"

            # (c) limit_mw is positive float with 1 decimal
            limit_val = float(multi_row["limit_mw"])
            assert limit_val > 0
            assert "." in multi_row["limit_mw"]
            decimal_places = len(multi_row["limit_mw"].split(".")[1])
            assert decimal_places == 1

            # (d) direction is "both"
            assert multi_row["direction"] == "both"

            # (e) calibration_load_level is valid
            assert multi_row["calibration_load_level"] in ("peak", "shoulder", "valley")

    def test_write_flowgates_csv_weight_precision(self, tmp_path: Path) -> None:
        """Weight 0.7234 is written as '0.72' (2 decimal places)."""
        fg = FlowgateDefinition(
            flowgate_id="FG_1",
            flowgate_name="Test",
            branches=[
                FlowgateBranch(branch_idx=1, from_bus=10, to_bus=20, weight=0.7234),
            ],
            limit_mw=100.0,
            direction=FlowgateDirection.BOTH,
            calibration_load_level="peak",
            max_observed_flow_mw=105.3,
        )

        csv_path = tmp_path / "flowgates.csv"
        write_flowgates_csv([fg], csv_path)

        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert rows[0]["weight_list"] == "0.72"
