"""Tests for the representative day selection & extraction module.

All tests use synthetic data generated with numpy. No actual ACTIVSg companion
CSV files are read. Tests cover daily summary computation, scoring, ranking,
profile extraction, canonical CSV writing, rationale generation, and the
process_network orchestration function.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from scripts.select_representative_day import (
    AnnualStatistics,
    DailySummary,
    ScoringWeights,
    SelectionNetworkId,
    build_selection_rationale,
    compute_annual_statistics,
    compute_daily_summaries,
    extract_day_profiles,
    rank_days,
    score_day,
    select_day,
    write_canonical_csv,
    write_rationale_json,
)

# ---------------------------------------------------------------------------
# Constants for synthetic data
# ---------------------------------------------------------------------------

HOURS_PER_YEAR = 8760
HOURS_PER_DAY = 24
DAYS_PER_YEAR = 365
N_BUSES = 3
N_WIND_GENS = 2
N_SOLAR_GENS = 2

# Reproducible RNG
RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_full_year_arrays(
    *,
    base_load: float = 100.0,
    base_wind: float = 50.0,
    base_solar: float = 30.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create synthetic full-year (8760, N) arrays with known characteristics.

    Each day has a flat profile at the base value plus small per-day variation
    driven by a deterministic RNG seed.
    """
    rng = np.random.default_rng(42)

    load = np.full((HOURS_PER_YEAR, N_BUSES), base_load, dtype=np.float64)
    wind = np.full((HOURS_PER_YEAR, N_WIND_GENS), base_wind, dtype=np.float64)
    solar = np.full((HOURS_PER_YEAR, N_SOLAR_GENS), base_solar, dtype=np.float64)

    # Add small daily variation
    for d in range(DAYS_PER_YEAR):
        start = d * HOURS_PER_DAY
        end = start + HOURS_PER_DAY
        load[start:end] += rng.uniform(-5, 5, size=(HOURS_PER_DAY, N_BUSES))
        wind[start:end] += rng.uniform(-5, 5, size=(HOURS_PER_DAY, N_WIND_GENS))
        solar[start:end] += rng.uniform(-5, 5, size=(HOURS_PER_DAY, N_SOLAR_GENS))

    return load, wind, solar


# ---------------------------------------------------------------------------
# Test 1: compute_daily_summaries returns 365 days
# ---------------------------------------------------------------------------


def test_compute_daily_summaries_365_days() -> None:
    """Construct a synthetic full-year dataset and verify 365 DailySummary objects."""
    load, wind, solar = _make_full_year_arrays()
    summaries = compute_daily_summaries(load, wind, solar)
    assert len(summaries) == DAYS_PER_YEAR
    for i, s in enumerate(summaries):
        assert s.day_index == i
        assert isinstance(s.date_str, str)
        assert s.total_load_mwh > 0
        assert s.peak_load_mw > 0


# ---------------------------------------------------------------------------
# Test 2: peak load detection on day 182
# ---------------------------------------------------------------------------


def test_compute_daily_summaries_peak_load() -> None:
    """Day 182 has highest single-hour system load."""
    load, wind, solar = _make_full_year_arrays(base_load=100.0)

    # Inject a massive peak on day 182, hour 14
    day_182_start = 182 * HOURS_PER_DAY
    load[day_182_start + 14, :] = 1000.0  # 1000 MW per bus -> 3000 MW system

    summaries = compute_daily_summaries(load, wind, solar)

    day_182 = summaries[182]
    assert day_182.peak_load_mw == pytest.approx(3000.0, rel=0.01)

    # Verify it exceeds all other days
    for i, s in enumerate(summaries):
        if i != 182:
            assert day_182.peak_load_mw > s.peak_load_mw


# ---------------------------------------------------------------------------
# Test 3: ramp magnitude detection on day 100
# ---------------------------------------------------------------------------


def test_compute_daily_summaries_ramp_magnitude() -> None:
    """Day 100 has a 500 MW hour-over-hour load increase."""
    load, wind, solar = _make_full_year_arrays(base_load=100.0)

    # Inject a large ramp on day 100: hour 17 is baseline, hour 18 jumps up
    day_100_start = 100 * HOURS_PER_DAY
    # Set hours 17 and 18 to specific values for all buses
    # System load at h17 = 100*3 = 300, at h18 = 100*3 + 500 = 800
    # So ramp = 500 MW. We put the extra on one bus.
    load[day_100_start + 17, :] = 100.0
    load[day_100_start + 18, :] = 100.0
    load[day_100_start + 18, 0] += 500.0  # bus 0 jumps by 500

    summaries = compute_daily_summaries(load, wind, solar)
    assert summaries[100].max_load_ramp_mw >= 500.0


# ---------------------------------------------------------------------------
# Test 4: missing data detection on day 50
# ---------------------------------------------------------------------------


def test_compute_daily_summaries_missing_data() -> None:
    """Day 50 has NaN values in 3 hours."""
    load, wind, solar = _make_full_year_arrays()

    day_50_start = 50 * HOURS_PER_DAY
    # Inject NaN into 3 distinct hours
    load[day_50_start + 5, 0] = np.nan
    load[day_50_start + 10, 1] = np.nan
    wind[day_50_start + 15, 0] = np.nan

    summaries = compute_daily_summaries(load, wind, solar)
    assert summaries[50].missing_hours == 3


# ---------------------------------------------------------------------------
# Test 5: annual statistics bounds
# ---------------------------------------------------------------------------


def test_compute_annual_statistics_bounds() -> None:
    """Verify correct min, mean, max for annual statistics."""
    load, wind, solar = _make_full_year_arrays()
    summaries = compute_daily_summaries(load, wind, solar)
    stats = compute_annual_statistics(summaries)

    load_values = [s.total_load_mwh for s in summaries]
    wind_values = [s.total_wind_mwh for s in summaries]
    solar_values = [s.total_solar_mwh for s in summaries]
    ramp_values = [s.max_load_ramp_mw for s in summaries]
    rp_values = [s.renewable_penetration for s in summaries]

    assert stats.load_mwh_min == pytest.approx(min(load_values))
    assert stats.load_mwh_max == pytest.approx(max(load_values))
    assert stats.load_mwh_mean == pytest.approx(np.mean(load_values), rel=1e-6)

    assert stats.wind_mwh_min == pytest.approx(min(wind_values))
    assert stats.wind_mwh_max == pytest.approx(max(wind_values))

    assert stats.solar_mwh_min == pytest.approx(min(solar_values))
    assert stats.solar_mwh_max == pytest.approx(max(solar_values))

    assert stats.max_ramp_mw_min == pytest.approx(min(ramp_values))
    assert stats.max_ramp_mw_max == pytest.approx(max(ramp_values))

    assert stats.renewable_penetration_min == pytest.approx(min(rp_values))
    assert stats.renewable_penetration_max == pytest.approx(max(rp_values))
    assert stats.renewable_penetration_mean == pytest.approx(np.mean(rp_values), rel=1e-6)


# ---------------------------------------------------------------------------
# Test 6: score_day normalized range
# ---------------------------------------------------------------------------


def test_score_day_normalized_range() -> None:
    """Max-day scores 1.0, min-day scores 0.0 on all normalized metrics."""
    stats = AnnualStatistics(
        load_mwh_min=1000.0,
        load_mwh_mean=2000.0,
        load_mwh_max=3000.0,
        peak_load_mw_min=50.0,
        peak_load_mw_mean=100.0,
        peak_load_mw_max=150.0,
        wind_mwh_min=100.0,
        wind_mwh_mean=300.0,
        wind_mwh_max=500.0,
        solar_mwh_min=50.0,
        solar_mwh_mean=150.0,
        solar_mwh_max=250.0,
        max_ramp_mw_min=10.0,
        max_ramp_mw_mean=50.0,
        max_ramp_mw_max=100.0,
        renewable_penetration_min=0.1,
        renewable_penetration_mean=0.2,
        renewable_penetration_max=0.3,
    )
    weights = ScoringWeights()

    # Day at annual maximum for all metrics
    max_day = DailySummary(
        day_index=0,
        date_str="2016-07-19",
        total_load_mwh=3000.0,
        peak_load_mw=150.0,
        total_wind_mwh=500.0,
        total_solar_mwh=250.0,
        peak_wind_mw=30.0,
        peak_solar_mw=15.0,
        max_load_ramp_mw=100.0,
        renewable_penetration=0.3,
        missing_hours=0,
        is_weekday=True,
    )
    max_score = score_day(max_day, stats, weights, 100.0, 100.0)
    assert max_score.load_level_score == pytest.approx(1.0)
    assert max_score.wind_score == pytest.approx(1.0)
    assert max_score.solar_score == pytest.approx(1.0)
    assert max_score.ramp_score == pytest.approx(1.0)

    # Day at annual minimum for all metrics
    min_day = DailySummary(
        day_index=1,
        date_str="2016-01-01",
        total_load_mwh=1000.0,
        peak_load_mw=50.0,
        total_wind_mwh=100.0,
        total_solar_mwh=50.0,
        peak_wind_mw=5.0,
        peak_solar_mw=3.0,
        max_load_ramp_mw=10.0,
        renewable_penetration=0.1,
        missing_hours=0,
        is_weekday=True,
    )
    min_score = score_day(min_day, stats, weights, 100.0, 100.0)
    assert min_score.load_level_score == pytest.approx(0.0)
    assert min_score.wind_score == pytest.approx(0.0)
    assert min_score.solar_score == pytest.approx(0.0)
    assert min_score.ramp_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 7: anomaly penalty
# ---------------------------------------------------------------------------


def test_score_day_anomaly_penalty() -> None:
    """Day with missing_hours=2 gets anomaly_penalty=1.0, making composite negative."""
    stats = AnnualStatistics(
        load_mwh_min=1000.0,
        load_mwh_mean=2000.0,
        load_mwh_max=3000.0,
        peak_load_mw_min=50.0,
        peak_load_mw_mean=100.0,
        peak_load_mw_max=150.0,
        wind_mwh_min=100.0,
        wind_mwh_mean=300.0,
        wind_mwh_max=500.0,
        solar_mwh_min=50.0,
        solar_mwh_mean=150.0,
        solar_mwh_max=250.0,
        max_ramp_mw_min=10.0,
        max_ramp_mw_mean=50.0,
        max_ramp_mw_max=100.0,
        renewable_penetration_min=0.1,
        renewable_penetration_mean=0.2,
        renewable_penetration_max=0.3,
    )
    weights = ScoringWeights()

    anomaly_day = DailySummary(
        day_index=0,
        date_str="2016-03-15",
        total_load_mwh=2000.0,
        peak_load_mw=100.0,
        total_wind_mwh=300.0,
        total_solar_mwh=150.0,
        peak_wind_mw=20.0,
        peak_solar_mw=10.0,
        max_load_ramp_mw=50.0,
        renewable_penetration=0.2,
        missing_hours=2,
        is_weekday=True,
    )
    score = score_day(anomaly_day, stats, weights, 100.0, 100.0)
    assert score.anomaly_penalty == 1.0
    assert score.composite_score < 0


# ---------------------------------------------------------------------------
# Test 8: diversity score
# ---------------------------------------------------------------------------


def test_score_day_diversity_both_renewables() -> None:
    """Equal capacity factors -> diversity=1.0; zero solar -> diversity=0.0."""
    stats = AnnualStatistics(
        load_mwh_min=1000.0,
        load_mwh_mean=2000.0,
        load_mwh_max=3000.0,
        peak_load_mw_min=50.0,
        peak_load_mw_mean=100.0,
        peak_load_mw_max=150.0,
        wind_mwh_min=0.0,
        wind_mwh_mean=300.0,
        wind_mwh_max=600.0,
        solar_mwh_min=0.0,
        solar_mwh_mean=200.0,
        solar_mwh_max=400.0,
        max_ramp_mw_min=10.0,
        max_ramp_mw_mean=50.0,
        max_ramp_mw_max=100.0,
        renewable_penetration_min=0.0,
        renewable_penetration_mean=0.2,
        renewable_penetration_max=0.4,
    )
    weights = ScoringWeights()

    # Equal CFs: wind_cf = 720/(100*24) = 0.3, solar_cf = 720/(100*24) = 0.3
    equal_day = DailySummary(
        day_index=0,
        date_str="2016-06-15",
        total_load_mwh=2000.0,
        peak_load_mw=100.0,
        total_wind_mwh=720.0,
        total_solar_mwh=720.0,
        peak_wind_mw=40.0,
        peak_solar_mw=40.0,
        max_load_ramp_mw=50.0,
        renewable_penetration=0.72,
        missing_hours=0,
        is_weekday=True,
    )
    score_equal = score_day(equal_day, stats, weights, 100.0, 100.0)
    assert score_equal.diversity_score == pytest.approx(1.0)

    # Zero solar
    zero_solar_day = DailySummary(
        day_index=1,
        date_str="2016-12-15",
        total_load_mwh=2000.0,
        peak_load_mw=100.0,
        total_wind_mwh=500.0,
        total_solar_mwh=0.0,
        peak_wind_mw=30.0,
        peak_solar_mw=0.0,
        max_load_ramp_mw=50.0,
        renewable_penetration=0.25,
        missing_hours=0,
        is_weekday=True,
    )
    score_zero = score_day(zero_solar_day, stats, weights, 100.0, 100.0)
    assert score_zero.diversity_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 9: rank_days descending order
# ---------------------------------------------------------------------------


def test_rank_days_descending_order() -> None:
    """5 synthetic days rank in descending composite_score order."""
    # Create 5-day dataset (120 hours) -- we'll use 365 days with known variation
    rng = np.random.default_rng(99)
    load = np.full((HOURS_PER_YEAR, N_BUSES), 100.0)
    wind = np.full((HOURS_PER_YEAR, N_WIND_GENS), 50.0)
    solar = np.full((HOURS_PER_YEAR, N_SOLAR_GENS), 30.0)

    # Make each day slightly different
    for d in range(DAYS_PER_YEAR):
        start = d * HOURS_PER_DAY
        end = start + HOURS_PER_DAY
        load[start:end] *= 1.0 + (d / DAYS_PER_YEAR) * 0.5
        wind[start:end] *= 1.0 + rng.uniform(0, 0.3)
        solar[start:end] *= 1.0 + rng.uniform(0, 0.3)

    summaries = compute_daily_summaries(load, wind, solar)
    stats = compute_annual_statistics(summaries)
    weights = ScoringWeights()

    ranked = rank_days(summaries, stats, weights, 200.0, 150.0)

    # Verify descending order
    for i in range(len(ranked) - 1):
        assert ranked[i].composite_score >= ranked[i + 1].composite_score


# ---------------------------------------------------------------------------
# Test 10: extract_day_profiles correct slice
# ---------------------------------------------------------------------------


def test_extract_day_profiles_correct_slice() -> None:
    """Day 10 (hours 240-263) has distinctive values."""
    load = np.zeros((HOURS_PER_YEAR, N_BUSES))
    wind = np.zeros((HOURS_PER_YEAR, N_WIND_GENS))
    solar = np.zeros((HOURS_PER_YEAR, N_SOLAR_GENS))

    # Set day 10 to known value 42.0
    start = 10 * HOURS_PER_DAY
    end = start + HOURS_PER_DAY
    load[start:end] = 42.0
    wind[start:end] = 42.0
    solar[start:end] = 42.0

    bus_ids = list(range(1, N_BUSES + 1))
    wind_ids = [f"wind_{i}" for i in range(N_WIND_GENS)]
    solar_ids = [f"solar_{i}" for i in range(N_SOLAR_GENS)]

    load_24h, wind_24h, solar_24h = extract_day_profiles(
        load, wind, solar, 10, bus_ids, wind_ids, solar_ids
    )

    assert load_24h.shape == (24, N_BUSES)
    assert wind_24h.shape == (24, N_WIND_GENS)
    assert solar_24h.shape == (24, N_SOLAR_GENS)

    np.testing.assert_array_equal(load_24h, 42.0)
    np.testing.assert_array_equal(wind_24h, 42.0)
    np.testing.assert_array_equal(solar_24h, 42.0)


# ---------------------------------------------------------------------------
# Test 11: extract_day_profiles invalid index
# ---------------------------------------------------------------------------


def test_extract_day_profiles_invalid_index() -> None:
    """ValueError for day_index=-1 and day_index=365."""
    load = np.zeros((HOURS_PER_YEAR, N_BUSES))
    wind = np.zeros((HOURS_PER_YEAR, N_WIND_GENS))
    solar = np.zeros((HOURS_PER_YEAR, N_SOLAR_GENS))

    bus_ids = list(range(1, N_BUSES + 1))
    wind_ids = [f"w{i}" for i in range(N_WIND_GENS)]
    solar_ids = [f"s{i}" for i in range(N_SOLAR_GENS)]

    with pytest.raises(ValueError, match="day_index"):
        extract_day_profiles(load, wind, solar, -1, bus_ids, wind_ids, solar_ids)

    with pytest.raises(ValueError, match="day_index"):
        extract_day_profiles(load, wind, solar, 365, bus_ids, wind_ids, solar_ids)


# ---------------------------------------------------------------------------
# Test 12: write_canonical_csv format
# ---------------------------------------------------------------------------


def test_write_canonical_csv_format(tmp_path: Path) -> None:
    """Verify CSV header, row count, and value mapping."""
    # (24, 3) array with known values
    data = np.arange(24 * 3, dtype=np.float64).reshape(24, 3)
    bus_ids = [101, 202, 303]
    dest = tmp_path / "load_24h.csv"

    write_canonical_csv(data, bus_ids, "bus_id", dest)

    with open(dest, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)

    # (a) header format
    expected_header = ["bus_id"] + [f"HR_{h}" for h in range(1, 25)]
    assert header == expected_header

    # (b) exactly 3 data rows
    assert len(rows) == 3

    # (c) values match transposed input
    for e_idx, bus_id in enumerate(bus_ids):
        assert rows[e_idx][0] == str(bus_id)
        for h in range(24):
            expected_val = round(float(data[h, e_idx]), 2)
            assert float(rows[e_idx][h + 1]) == pytest.approx(expected_val)

    # (d) HR_1 = hour index 0, HR_24 = hour index 23
    # For bus 0: HR_1 = data[0,0] = 0.0, HR_24 = data[23,0] = 69.0
    assert float(rows[0][1]) == pytest.approx(round(float(data[0, 0]), 2))
    assert float(rows[0][24]) == pytest.approx(round(float(data[23, 0]), 2))


# ---------------------------------------------------------------------------
# Test 13: write_canonical_csv hour-ending mapping
# ---------------------------------------------------------------------------


def test_write_canonical_csv_hour_ending_mapping(tmp_path: Path) -> None:
    """HR_1 = hour index 0 value, HR_24 = hour index 23 value."""
    data = np.zeros((24, 1), dtype=np.float64)
    data[0, 0] = 10.0  # hour index 0
    data[23, 0] = 230.0  # hour index 23

    dest = tmp_path / "test_he.csv"
    write_canonical_csv(data, ["gen_1"], "gen_uid", dest)

    with open(dest, newline="") as fh:
        reader = csv.DictReader(fh)
        row = next(reader)

    assert float(row["HR_1"]) == pytest.approx(10.0)
    assert float(row["HR_24"]) == pytest.approx(230.0)


# ---------------------------------------------------------------------------
# Test 14: build_selection_rationale top 10
# ---------------------------------------------------------------------------


def test_build_selection_rationale_top_10() -> None:
    """Top 10 candidates are correctly extracted and sorted."""
    load, wind, solar = _make_full_year_arrays()
    summaries = compute_daily_summaries(load, wind, solar)
    stats = compute_annual_statistics(summaries)
    weights = ScoringWeights()

    best, all_scores = select_day(summaries, stats, weights, 200.0, 100.0)

    rationale = build_selection_rationale(
        SelectionNetworkId.ACTIVSG2000,
        best,
        all_scores,
        summaries,
        stats,
        weights,
        200.0,
        100.0,
    )

    assert len(rationale.top_10_candidates) == 10
    # Sorted descending
    for i in range(9):
        assert (
            rationale.top_10_candidates[i].composite_score
            >= rationale.top_10_candidates[i + 1].composite_score
        )
    # Selected day matches the first entry
    assert rationale.composite_score == rationale.top_10_candidates[0].composite_score


# ---------------------------------------------------------------------------
# Test 15: write_rationale_json roundtrip
# ---------------------------------------------------------------------------


def test_write_rationale_json_roundtrip(tmp_path: Path) -> None:
    """JSON roundtrip preserves all critical fields."""
    load, wind, solar = _make_full_year_arrays()
    summaries = compute_daily_summaries(load, wind, solar)
    stats = compute_annual_statistics(summaries)
    weights = ScoringWeights()

    best, all_scores = select_day(summaries, stats, weights, 200.0, 100.0)
    rationale = build_selection_rationale(
        SelectionNetworkId.ACTIVSG2000,
        best,
        all_scores,
        summaries,
        stats,
        weights,
        200.0,
        100.0,
    )

    dest = tmp_path / "rationale.json"
    write_rationale_json(rationale, dest)

    with open(dest) as fh:
        data = json.load(fh)

    assert data["selected_date"] == rationale.selected_date
    assert data["composite_score"] == pytest.approx(rationale.composite_score, abs=1e-4)
    assert "scoring_weights" in data
    assert data["scoring_weights"]["load_level"] == pytest.approx(weights.load_level, abs=1e-4)
    assert "annual_statistics" in data
    assert data["annual_statistics"]["load_mwh_min"] == pytest.approx(stats.load_mwh_min, abs=1e-4)
    assert "top_10_candidates" in data
    assert len(data["top_10_candidates"]) == 10


# ---------------------------------------------------------------------------
# Test 16: process_network with target_date override
# ---------------------------------------------------------------------------


def test_process_network_target_date_override(tmp_path: Path) -> None:
    """process_network with target_date extracts that day, not the top-scored day."""
    # Create synthetic companion CSVs in raw_dir
    raw_dir = tmp_path / "ACTIVSg2000" / "raw"
    raw_dir.mkdir(parents=True)

    rng = np.random.default_rng(123)
    load_data = 100.0 + rng.uniform(-5, 5, size=(HOURS_PER_YEAR, N_BUSES))
    wind_data = 50.0 + rng.uniform(-5, 5, size=(HOURS_PER_YEAR, N_WIND_GENS))
    solar_data = 30.0 + rng.uniform(-5, 5, size=(HOURS_PER_YEAR, N_SOLAR_GENS))

    # Make day 200 distinctive for verification
    target_day_index = 200
    target_start = target_day_index * HOURS_PER_DAY
    target_end = target_start + HOURS_PER_DAY
    load_data[target_start:target_end, :] = 999.0

    # Write load CSV
    _write_synthetic_csv(
        raw_dir / "ACTIVSg2000_load.csv",
        load_data,
        [f"bus_{i + 1}" for i in range(N_BUSES)],
    )
    _write_synthetic_csv(
        raw_dir / "ACTIVSg2000_wind.csv",
        wind_data,
        [f"wind_gen_{i + 1}" for i in range(N_WIND_GENS)],
    )
    _write_synthetic_csv(
        raw_dir / "ACTIVSg2000_solar.csv",
        solar_data,
        [f"solar_gen_{i + 1}" for i in range(N_SOLAR_GENS)],
    )

    # Create a minimal cleaned .m file with genfuel
    m_dir = tmp_path / "ACTIVSg2000"
    m_dir.mkdir(exist_ok=True)
    _write_minimal_m_file(m_dir / "case_ACTIVSg2000.m")

    # Compute target date string (2016-01-01 + 200 days)
    target_date_str = (date(2016, 1, 1) + __import__("datetime").timedelta(days=200)).isoformat()

    from scripts.select_representative_day import process_network

    output_dir = tmp_path / "ACTIVSg2000"

    result = process_network(
        network_id=SelectionNetworkId.ACTIVSG2000,
        raw_dir=raw_dir,
        cleaned_m_dir=tmp_path,
        output_dir=output_dir,
        target_date=target_date_str,
    )

    assert result.selected_date == target_date_str

    # Read back the load CSV and verify all values are 999.0
    with open(result.load_csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            for h in range(1, 25):
                assert float(row[f"HR_{h}"]) == pytest.approx(999.0, rel=0.01)

    # Verify rationale records the overridden date
    with open(result.rationale_json_path) as fh:
        rationale_data = json.load(fh)
    assert rationale_data["selected_date"] == target_date_str


# ---------------------------------------------------------------------------
# Helpers for test 16
# ---------------------------------------------------------------------------


def _write_synthetic_csv(
    path: Path,
    data: np.ndarray,
    column_names: list[str],
) -> None:
    """Write a synthetic companion CSV with a Time column + data columns."""
    from datetime import datetime, timedelta

    start = datetime(2016, 1, 1, 0, 0, 0)
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Time"] + column_names)
        for i in range(data.shape[0]):
            ts = start + timedelta(hours=i)
            row = [ts.strftime("%Y-%m-%d %H:%M:%S")]
            row.extend(f"{v:.2f}" for v in data[i])
            writer.writerow(row)


def _write_minimal_m_file(path: Path) -> None:
    """Write a minimal .m file with gen and genfuel blocks."""
    n_gens = 4  # 2 wind + 2 solar
    gen_lines = []
    for i in range(n_gens):
        # bus pg qg qmax qmin vg mbase status pmax pmin
        pmax = 100.0
        gen_lines.append(f"\t{i + 1}\t0\t0\t100\t-100\t1.0\t100\t1\t{pmax}\t0")

    genfuel_entries = ["'wind'", "'wind'", "'solar'", "'solar'"]

    content = f"""function mpc = case_ACTIVSg2000
mpc.version = '2';
mpc.baseMVA = 100;
mpc.bus = [
\t1\t1\t0\t0\t0\t0\t1\t1.0\t0\t230\t1\t1.1\t0.9;
];
mpc.gen = [
{";".join(gen_lines)};
];
mpc.genfuel = {{
\t{"; ".join(genfuel_entries)};
}};
"""
    path.write_text(content)
