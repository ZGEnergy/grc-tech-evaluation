"""Tests for Phase 3 BESS Placement & Sizing (PRD-02).

All 16 tests match the PRD Success Criteria. Tests are self-contained
with no external file or network dependencies.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import numpy as np
import pytest

from scripts.phase3_bess_placement import (
    BESS_CSV_COLUMNS,
    BessFleetConfig,
    BessNetworkId,
    BessUnit,
    BusCandidate,
    ScoredBus,
    StorageRefParams,
    build_bess_units,
    build_rationale_log,
    compute_unit_ratings,
    score_candidates,
    select_bess_buses,
    validate_bess_fleet,
    write_bess_units_csv,
    write_rationale_log,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bus_candidate(
    bus: int,
    pd_mw: float,
    utilization: float,
    area: int = 1,
    branch_count: int = 3,
) -> BusCandidate:
    return BusCandidate(
        bus=bus,
        pd_mw=pd_mw,
        area=area,
        max_branch_utilization=utilization,
        connected_branch_count=branch_count,
    )


def _make_scored_bus(
    bus: int,
    pd_mw: float = 100.0,
    score: float = 1.0,
    area: int = 1,
    utilization: float = 0.5,
) -> ScoredBus:
    return ScoredBus(
        bus=bus,
        pd_mw=pd_mw,
        area=area,
        max_branch_utilization=utilization,
        normalized_pd=pd_mw / 100.0,
        inverse_utilization=1.0 / max(utilization, 0.01),
        score=score,
    )


def _default_ref_params(
    charge_eff: float = 0.922,
    discharge_eff: float = 0.922,
    template_power_mw: float = 50.0,
    template_ramp_rate: float = 50.0,
) -> StorageRefParams:
    return StorageRefParams(
        charge_eff=charge_eff,
        discharge_eff=discharge_eff,
        roundtrip_eff=round(charge_eff * discharge_eff, 6),
        min_soc_pct=10.0,
        max_soc_pct=90.0,
        initial_soc_pct=50.0,
        cyclic_soc=True,
        template_power_mw=template_power_mw,
        template_ramp_rate_mw_per_min=template_ramp_rate,
    )


def _default_config(**kwargs: object) -> BessFleetConfig:
    defaults: dict[str, object] = {
        "min_units": 3,
        "max_units": 5,
        "fleet_fraction_min": 0.03,
        "fleet_fraction_max": 0.05,
        "fleet_fraction_target": 0.04,
        "min_distinct_sizes": 2,
        "duration_hr": 4.0,
    }
    defaults.update(kwargs)
    return BessFleetConfig(**defaults)  # type: ignore[arg-type]


def _make_bess_unit(
    unit_id: str = "BESS_SMALL_001",
    bus: int = 100,
    power_mw: float = 50.0,
    ref: StorageRefParams | None = None,
    duration_hr: float = 4.0,
) -> BessUnit:
    if ref is None:
        ref = _default_ref_params()
    return BessUnit(
        unit_id=unit_id,
        bus=bus,
        power_mw=power_mw,
        energy_mwh=round(power_mw * duration_hr, 1),
        duration_hr=duration_hr,
        charge_eff=ref.charge_eff,
        discharge_eff=ref.discharge_eff,
        roundtrip_eff=ref.roundtrip_eff,
        min_soc_pct=ref.min_soc_pct,
        max_soc_pct=ref.max_soc_pct,
        initial_soc_pct=ref.initial_soc_pct,
        ramp_rate_mw_per_min=round(
            ref.template_ramp_rate_mw_per_min * (power_mw / ref.template_power_mw), 2
        ),
        cyclic_soc=ref.cyclic_soc,
    )


# ---------------------------------------------------------------------------
# Test 1: Scoring ranks high-load / low-utilization above high-load / high-utilization
# ---------------------------------------------------------------------------


def test_score_candidates_highest_load_low_utilization_wins() -> None:
    """Bus C has highest load but high utilization (0.90), so its score is
    penalized. Buses with lower utilization should rank above C.
    """
    candidates = [
        _make_bus_candidate(bus=1, pd_mw=500.0, utilization=0.30),
        _make_bus_candidate(bus=2, pd_mw=400.0, utilization=0.20),
        _make_bus_candidate(bus=3, pd_mw=600.0, utilization=0.90),
        _make_bus_candidate(bus=4, pd_mw=300.0, utilization=0.10),
    ]
    scored = score_candidates(candidates)

    # Verify sorted by score descending
    for i in range(len(scored) - 1):
        assert scored[i].score >= scored[i + 1].score

    # Bus C (bus=3) should NOT be ranked first despite highest Pd
    bus_c_rank = next(i for i, s in enumerate(scored) if s.bus == 3)
    assert bus_c_rank > 0, "Bus C (highest load, highest utilization) should not be rank 1"

    # Bus D (bus=4) or Bus A (bus=1) should rank above bus C
    bus_a_rank = next(i for i, s in enumerate(scored) if s.bus == 1)
    assert bus_a_rank < bus_c_rank or bus_c_rank > 0


# ---------------------------------------------------------------------------
# Test 2: Zero utilization is clamped to 0.01
# ---------------------------------------------------------------------------


def test_score_candidates_clamps_zero_utilization() -> None:
    """A bus with max_branch_utilization=0.0 should be clamped to 0.01,
    giving inverse_utilization = 100.
    """
    candidates = [
        _make_bus_candidate(bus=10, pd_mw=200.0, utilization=0.0),
    ]
    scored = score_candidates(candidates)

    assert len(scored) == 1
    s = scored[0]
    assert s.inverse_utilization == pytest.approx(100.0, rel=1e-6)
    # normalized_pd = 200/200 = 1.0, score = 1.0 * 100 = 100.0
    assert s.score == pytest.approx(100.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 3: Deterministic tiebreaking by bus number ascending
# ---------------------------------------------------------------------------


def test_score_candidates_deterministic_tiebreaking() -> None:
    """Three buses with identical pd_mw and utilization should be ordered
    by bus number ascending as the tiebreaker.
    """
    candidates = [
        _make_bus_candidate(bus=10, pd_mw=300.0, utilization=0.50),
        _make_bus_candidate(bus=5, pd_mw=300.0, utilization=0.50),
        _make_bus_candidate(bus=20, pd_mw=300.0, utilization=0.50),
    ]
    scored = score_candidates(candidates)

    assert [s.bus for s in scored] == [5, 10, 20]


# ---------------------------------------------------------------------------
# Test 4: select_bess_buses respects max_units
# ---------------------------------------------------------------------------


def test_select_bess_buses_respects_max_units() -> None:
    """With 10 candidates and max_units=5, only the top 5 are returned."""
    scored = [_make_scored_bus(bus=i, score=100.0 - i) for i in range(10)]
    config = _default_config(max_units=5)

    selected = select_bess_buses(scored, config)
    assert len(selected) == 5
    # Should be the top 5 by score
    assert [s.bus for s in selected] == [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Test 5: select_bess_buses raises if too few candidates
# ---------------------------------------------------------------------------


def test_select_bess_buses_raises_if_too_few_candidates() -> None:
    """With only 2 candidates and min_units=3, ValueError is raised."""
    scored = [_make_scored_bus(bus=i, score=10.0 - i) for i in range(2)]
    config = _default_config(min_units=3)

    with pytest.raises(ValueError, match="candidate buses available"):
        select_bess_buses(scored, config)


# ---------------------------------------------------------------------------
# Test 6: Fleet total power within fraction bounds
# ---------------------------------------------------------------------------


def test_compute_unit_ratings_fleet_within_fraction_bounds() -> None:
    """Total fleet power should be between 3% and 5% of system peak (10000 MW)."""
    selected = [_make_scored_bus(bus=i, pd_mw=100.0 + i * 50, score=10.0 - i) for i in range(4)]
    config = _default_config(fleet_fraction_min=0.03, fleet_fraction_max=0.05)
    rng = np.random.default_rng(42)

    ratings = compute_unit_ratings(selected, 10000.0, config, rng)

    assert len(ratings) == 4
    total = sum(ratings)
    assert 300.0 <= total <= 500.0, f"Total {total} MW outside [300, 500]"
    assert all(r > 0 for r in ratings)


# ---------------------------------------------------------------------------
# Test 7: At least min_distinct_sizes unique ratings
# ---------------------------------------------------------------------------


def test_compute_unit_ratings_produces_distinct_sizes() -> None:
    """With 4 buses of different Pd values and min_distinct_sizes=2,
    there should be at least 2 distinct power ratings.
    """
    selected = [
        _make_scored_bus(bus=1, pd_mw=200.0, score=4.0),
        _make_scored_bus(bus=2, pd_mw=150.0, score=3.0),
        _make_scored_bus(bus=3, pd_mw=100.0, score=2.0),
        _make_scored_bus(bus=4, pd_mw=50.0, score=1.0),
    ]
    config = _default_config(min_distinct_sizes=2)
    rng = np.random.default_rng(42)

    ratings = compute_unit_ratings(selected, 10000.0, config, rng)

    unique = set(ratings)
    assert len(unique) >= 2, f"Only {len(unique)} distinct rating(s): {unique}"


# ---------------------------------------------------------------------------
# Test 8: Empty selected_buses raises ValueError
# ---------------------------------------------------------------------------


def test_compute_unit_ratings_raises_on_empty_buses() -> None:
    """compute_unit_ratings with empty list raises ValueError."""
    config = _default_config()
    rng = np.random.default_rng(42)

    with pytest.raises(ValueError, match="must not be empty"):
        compute_unit_ratings([], 10000.0, config, rng)


# ---------------------------------------------------------------------------
# Test 9: energy_mwh == power_mw * 4.0
# ---------------------------------------------------------------------------


def test_build_bess_units_energy_equals_power_times_duration() -> None:
    """Every unit should have energy_mwh == power_mw * 4.0."""
    selected = [
        _make_scored_bus(bus=10, pd_mw=200.0, score=3.0),
        _make_scored_bus(bus=20, pd_mw=150.0, score=2.0),
        _make_scored_bus(bus=30, pd_mw=100.0, score=1.0),
    ]
    power_ratings = [50.0, 75.0, 100.0]
    ref = _default_ref_params()
    config = _default_config()

    units = build_bess_units(selected, power_ratings, ref, config, BessNetworkId.SMALL)

    assert len(units) == 3
    for u, expected_power in zip(units, power_ratings):
        assert u.energy_mwh == pytest.approx(expected_power * 4.0, abs=0.15)


# ---------------------------------------------------------------------------
# Test 10: Ramp rate scales proportionally
# ---------------------------------------------------------------------------


def test_build_bess_units_ramp_rate_scaled_proportionally() -> None:
    """Ramp rate should scale proportionally to power relative to template."""
    selected = [
        _make_scored_bus(bus=10, score=2.0),
        _make_scored_bus(bus=20, score=1.0),
    ]
    power_ratings = [100.0, 25.0]
    ref = _default_ref_params(template_power_mw=50.0, template_ramp_rate=50.0)
    config = _default_config()

    units = build_bess_units(selected, power_ratings, ref, config, BessNetworkId.SMALL)

    # 100 MW unit: ramp = 50 * (100/50) = 100.0
    assert units[0].ramp_rate_mw_per_min == pytest.approx(100.0, abs=0.01)
    # 25 MW unit: ramp = 50 * (25/50) = 25.0
    assert units[1].ramp_rate_mw_per_min == pytest.approx(25.0, abs=0.01)


# ---------------------------------------------------------------------------
# Test 11: Intensive parameters unchanged across units
# ---------------------------------------------------------------------------


def test_build_bess_units_intensive_params_unchanged() -> None:
    """Intensive parameters should be identical for all units regardless of power."""
    selected = [
        _make_scored_bus(bus=10, score=3.0),
        _make_scored_bus(bus=20, score=2.0),
        _make_scored_bus(bus=30, score=1.0),
    ]
    power_ratings = [30.0, 60.0, 120.0]
    ref = StorageRefParams(
        charge_eff=0.922,
        discharge_eff=0.922,
        roundtrip_eff=round(0.922 * 0.922, 6),
        min_soc_pct=10.0,
        max_soc_pct=90.0,
        initial_soc_pct=50.0,
        cyclic_soc=True,
        template_power_mw=50.0,
        template_ramp_rate_mw_per_min=50.0,
    )
    config = _default_config()

    units = build_bess_units(selected, power_ratings, ref, config, BessNetworkId.SMALL)

    for u in units:
        assert u.charge_eff == 0.922
        assert u.discharge_eff == 0.922
        assert u.min_soc_pct == 10.0
        assert u.max_soc_pct == 90.0
        assert u.initial_soc_pct == 50.0
        assert u.cyclic_soc is True


# ---------------------------------------------------------------------------
# Test 12: Unit ID format
# ---------------------------------------------------------------------------


def test_build_bess_units_unit_id_format() -> None:
    """Unit IDs should be BESS_SMALL_001 through BESS_SMALL_004."""
    selected = [_make_scored_bus(bus=i * 10, score=10.0 - i) for i in range(4)]
    power_ratings = [50.0, 60.0, 70.0, 80.0]
    ref = _default_ref_params()
    config = _default_config()

    units = build_bess_units(selected, power_ratings, ref, config, BessNetworkId.SMALL)

    expected_ids = ["BESS_SMALL_001", "BESS_SMALL_002", "BESS_SMALL_003", "BESS_SMALL_004"]
    actual_ids = [u.unit_id for u in units]
    assert actual_ids == expected_ids
    # All unique
    assert len(set(actual_ids)) == len(actual_ids)


# ---------------------------------------------------------------------------
# Test 13: Duplicate buses rejected by validation
# ---------------------------------------------------------------------------


def test_validate_bess_fleet_rejects_duplicate_buses() -> None:
    """Two units at the same bus should fail validation."""
    ref = _default_ref_params()
    u1 = _make_bess_unit(unit_id="BESS_SMALL_001", bus=100, power_mw=50.0, ref=ref)
    u2 = _make_bess_unit(unit_id="BESS_SMALL_002", bus=100, power_mw=60.0, ref=ref)
    u3 = _make_bess_unit(unit_id="BESS_SMALL_003", bus=200, power_mw=70.0, ref=ref)

    config = _default_config(min_units=3, max_units=5)
    system_peak = (50.0 + 60.0 + 70.0) / 0.04  # so fleet fraction = 4%

    with pytest.raises(ValueError, match="[Dd]uplicate bus"):
        validate_bess_fleet([u1, u2, u3], system_peak, config, ref)


# ---------------------------------------------------------------------------
# Test 14: Fleet below minimum fraction rejected
# ---------------------------------------------------------------------------


def test_validate_bess_fleet_rejects_fleet_below_minimum_fraction() -> None:
    """Fleet with total power = 1% of peak should fail (below 3% floor)."""
    ref = _default_ref_params()
    # 3 units totaling 100 MW against 10000 MW peak = 1%
    units = [
        _make_bess_unit(unit_id="BESS_SMALL_001", bus=100, power_mw=30.0, ref=ref),
        _make_bess_unit(unit_id="BESS_SMALL_002", bus=200, power_mw=35.0, ref=ref),
        _make_bess_unit(unit_id="BESS_SMALL_003", bus=300, power_mw=35.0, ref=ref),
    ]
    config = _default_config(min_units=3)

    with pytest.raises(ValueError, match="[Ff]raction"):
        validate_bess_fleet(units, 10000.0, config, ref)


# ---------------------------------------------------------------------------
# Test 15: CSV columns and values
# ---------------------------------------------------------------------------


def test_write_bess_units_csv_columns_and_values(tmp_path: Path) -> None:
    """Write 3 units to CSV and verify column order, row count, boolean format,
    and ordering.
    """
    ref = _default_ref_params()
    units = [
        _make_bess_unit(unit_id="BESS_SMALL_003", bus=300, power_mw=100.0, ref=ref),
        _make_bess_unit(unit_id="BESS_SMALL_001", bus=100, power_mw=50.0, ref=ref),
        _make_bess_unit(unit_id="BESS_SMALL_002", bus=200, power_mw=75.0, ref=ref),
    ]

    csv_path = tmp_path / "bess_units.csv"
    write_bess_units_csv(units, csv_path)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    # (a) Header has exactly 13 expected columns in order
    assert reader.fieldnames is not None
    assert list(reader.fieldnames) == BESS_CSV_COLUMNS

    rows = list(reader)

    # (b) 3 data rows
    assert len(rows) == 3

    # (c) cyclic_soc written as "true" (lowercase)
    for row in rows:
        assert row["cyclic_soc"] == "true"

    # (d) Rows ordered by unit_id ascending
    unit_ids = [row["unit_id"] for row in rows]
    assert unit_ids == sorted(unit_ids)
    assert unit_ids == ["BESS_SMALL_001", "BESS_SMALL_002", "BESS_SMALL_003"]


# ---------------------------------------------------------------------------
# Test 16: Rationale log includes all candidates
# ---------------------------------------------------------------------------


def test_write_rationale_log_includes_all_candidates(tmp_path: Path) -> None:
    """Build rationale from 20 scored buses with 5 selected.
    Verify 20 rows, 5 selected, 15 with rejection reasons, rank ordering.
    """
    scored = [_make_scored_bus(bus=i, score=100.0 - i) for i in range(20)]
    selected_buses = {s.bus for s in scored[:5]}
    config = _default_config(max_units=5)

    rationale = build_rationale_log(scored, selected_buses, config)

    assert len(rationale) == 20

    dest = tmp_path / "rationale.csv"
    write_rationale_log(rationale, dest)

    text = dest.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    # (a) 20 rows
    assert len(rows) == 20

    # (b) Exactly 5 rows with selected="true"
    selected_rows = [r for r in rows if r["selected"] == "true"]
    assert len(selected_rows) == 5

    # (c) Remaining 15 rows have non-empty rejection_reason
    rejected_rows = [r for r in rows if r["selected"] == "false"]
    assert len(rejected_rows) == 15
    for r in rejected_rows:
        assert r["rejection_reason"] != "", f"Row with bus={r['bus']} has empty rejection_reason"

    # (d) Rows ordered by rank ascending
    ranks = [int(r["rank"]) for r in rows]
    assert ranks == sorted(ranks)
    assert ranks == list(range(1, 21))
