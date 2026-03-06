"""Tests for Student-t distribution fitting (PRD 04/01).

All tests are self-contained with synthetic data generated via numpy.
No external data files are required.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from scripts.fit_student_t import (
    HourClassification,
    HourFitResult,
    PooledFitResult,
    ResourceFitResult,
    ResourceType,
    StudentTParams,
    build_student_t_params,
    classify_night_hours,
    compute_hourly_changes,
    fit_resource_type,
    fit_student_t_single,
    load_student_t_json,
    pool_changes_by_hour,
    validate_fit_ks,
    write_student_t_json,
)

# ---------------------------------------------------------------------------
# Tests for compute_hourly_changes
# ---------------------------------------------------------------------------


def test_compute_hourly_changes_shape() -> None:
    """Construct a synthetic (8760, 5) array and verify output shape is (8759, 5)."""
    rng = np.random.default_rng(42)
    generation = rng.random((8760, 5))
    changes = compute_hourly_changes(generation)
    assert changes.shape == (8759, 5)


def test_compute_hourly_changes_values() -> None:
    """Verify constant increment of 1.0 yields all-ones change array."""
    generation = np.arange(8760, dtype=np.float64).reshape(-1, 1)
    changes = compute_hourly_changes(generation)
    assert changes.shape == (8759, 1)
    np.testing.assert_allclose(changes, 1.0)


def test_compute_hourly_changes_rejects_wrong_length() -> None:
    """Verify ValueError for array with wrong number of rows."""
    generation = np.zeros((100, 3))
    with pytest.raises(ValueError, match="8760"):
        compute_hourly_changes(generation)


# ---------------------------------------------------------------------------
# Tests for pool_changes_by_hour
# ---------------------------------------------------------------------------


def test_pool_changes_by_hour_keys() -> None:
    """Verify returned dict has exactly 24 keys (0-23)."""
    rng = np.random.default_rng(42)
    generation = rng.random((8760, 2))
    changes = compute_hourly_changes(generation)
    pooled = pool_changes_by_hour(changes)
    assert set(pooled.keys()) == set(range(24))


def test_pool_changes_by_hour_sample_size() -> None:
    """Verify total sample size across all hours equals 8759 * N_gens."""
    n_gens = 3
    rng = np.random.default_rng(42)
    generation = rng.random((8760, n_gens))
    changes = compute_hourly_changes(generation)
    pooled = pool_changes_by_hour(changes)
    total = sum(len(v) for v in pooled.values())
    assert total == 8759 * n_gens


def test_pool_changes_by_hour_assignment() -> None:
    """Verify hour assignment for a repeating pattern.

    Construct generation where value at hour h is h % 24. The change from
    hour 23 to hour 0 is (0 - 23) = -23. These changes are assigned to hour 0.
    """
    # Build (8760, 1) with repeating 0,1,2,...,23 pattern
    generation = np.array([h % 24 for h in range(8760)], dtype=np.float64).reshape(-1, 1)
    changes = compute_hourly_changes(generation)
    pooled = pool_changes_by_hour(changes)

    # Changes into hour 0: from hour 23 to hour 0
    # At each day boundary: 0 - 23 = -23
    hour_0_changes = pooled[0]
    # All values for hour 0 should be -23 (overnight) except potentially
    # some that are +1 depending on exact alignment
    # Hour 0 changes = changes at indices where (i+1) % 24 == 0, i.e. i = 23, 47, 71...
    # change[23] = gen[24] - gen[23] = 0 - 23 = -23
    assert np.all(hour_0_changes == -23)


# ---------------------------------------------------------------------------
# Tests for classify_night_hours
# ---------------------------------------------------------------------------


def test_classify_night_hours_typical_solar(tmp_path: Path) -> None:
    """Test night-hour classification with typical solar profile.

    HR_1-HR_6 and HR_22-HR_24 have zero generation; HR_7-HR_21 have positive.
    Expected night hours: [0, 1, 2, 3, 4, 5, 21, 22, 23].
    """
    csv_path = tmp_path / "solar_actual_24h.csv"
    header = ["gen_uid"] + [f"HR_{h}" for h in range(1, 25)]

    # Two generators
    rows = []
    for gen_id in ["gen_1", "gen_2"]:
        values = []
        for h in range(1, 25):
            if h <= 6 or h >= 22:
                values.append("0.0")
            else:
                values.append("100.0")
        rows.append([gen_id] + values)

    with open(csv_path, "w", newline="") as fh:
        import csv

        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)

    night_hours = classify_night_hours(csv_path)
    assert night_hours == [0, 1, 2, 3, 4, 5, 21, 22, 23]


def test_classify_night_hours_no_night(tmp_path: Path) -> None:
    """Test that all-positive generation returns empty night-hours list."""
    csv_path = tmp_path / "solar_actual_24h.csv"
    header = ["gen_uid"] + [f"HR_{h}" for h in range(1, 25)]

    row = ["gen_1"] + ["50.0"] * 24
    with open(csv_path, "w", newline="") as fh:
        import csv

        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerow(row)

    night_hours = classify_night_hours(csv_path)
    assert night_hours == []


# ---------------------------------------------------------------------------
# Tests for fit_student_t_single
# ---------------------------------------------------------------------------


def test_fit_student_t_single_recovers_params() -> None:
    """Fit Student-t(df=5, loc=0, scale=1) to 10,000 samples and check recovery."""
    rng = np.random.default_rng(12345)
    sample = stats.t.rvs(df=5, loc=0, scale=1, size=10000, random_state=rng)
    df, loc, scale = fit_student_t_single(sample)

    assert 3.5 <= df <= 7.0, f"df={df} not in [3.5, 7.0]"
    assert -0.2 <= loc <= 0.2, f"loc={loc} not in [-0.2, 0.2]"
    assert 0.8 <= scale <= 1.2, f"scale={scale} not in [0.8, 1.2]"


def test_fit_student_t_single_rejects_small_sample() -> None:
    """Verify ValueError for sample with fewer than 10 observations."""
    sample = np.array([1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="at least"):
        fit_student_t_single(sample)


# ---------------------------------------------------------------------------
# Tests for validate_fit_ks
# ---------------------------------------------------------------------------


def test_validate_fit_ks_good_fit() -> None:
    """KS test should not reject when data truly comes from Student-t."""
    rng = np.random.default_rng(99)
    sample = stats.t.rvs(df=4, loc=0, scale=1, size=5000, random_state=rng)
    df, loc, scale = fit_student_t_single(sample)
    ks_stat, p_value = validate_fit_ks(sample, df, loc, scale)

    assert p_value > 0.05, f"p-value={p_value} should be > 0.05 for good fit"


def test_validate_fit_ks_bad_fit() -> None:
    """KS test should reject for obviously non-t data (uniform)."""
    rng = np.random.default_rng(42)
    sample = rng.uniform(-3, 3, size=5000)
    df, loc, scale = fit_student_t_single(sample)
    ks_stat, p_value = validate_fit_ks(sample, df, loc, scale)

    assert p_value < 0.05, f"p-value={p_value} should be < 0.05 for bad fit"


# ---------------------------------------------------------------------------
# Tests for fit_resource_type
# ---------------------------------------------------------------------------


def _make_synthetic_changes(n_gens: int = 2, seed: int = 42) -> np.ndarray:
    """Create a synthetic (8759, n_gens) change array from Student-t draws."""
    rng = np.random.default_rng(seed)
    return stats.t.rvs(df=5, loc=0, scale=1, size=(8759, n_gens), random_state=rng)


def test_fit_resource_type_wind_all_hours_fitted() -> None:
    """All 24 hours should be fitted for wind (no night hours)."""
    changes = _make_synthetic_changes(n_gens=2)
    result = fit_resource_type(
        changes, night_hours=[], resource_type=ResourceType.WIND, total_generators=2
    )

    assert len(result.per_hour) == 24
    for hr in result.per_hour:
        assert hr.is_fitted is True
        assert hr.classification == HourClassification.DAYTIME


def test_fit_resource_type_solar_night_hours_sentinel() -> None:
    """Night hours should have sentinel values, daytime hours should be fitted."""
    changes = _make_synthetic_changes(n_gens=2)
    night = [0, 1, 2, 22, 23]
    result = fit_resource_type(
        changes, night_hours=night, resource_type=ResourceType.SOLAR, total_generators=2
    )

    assert len(result.per_hour) == 24
    for hr in result.per_hour:
        if hr.hour in night:
            assert hr.is_fitted is False
            assert hr.classification == HourClassification.NIGHTTIME
            assert math.isinf(hr.df)
            assert hr.loc == 0.0
            assert hr.scale == 0.0
        else:
            assert hr.is_fitted is True


def test_fit_resource_type_pooled_excludes_night() -> None:
    """Pooled sample should exclude nighttime hours."""
    changes = _make_synthetic_changes(n_gens=2)
    night = [0, 1, 2, 22, 23]
    result = fit_resource_type(
        changes, night_hours=night, resource_type=ResourceType.SOLAR, total_generators=2
    )

    assert result.pooled.hours_excluded == sorted(night)
    # Total changes = 8759 * 2, some assigned to night hours should be excluded
    total_all = sum(hr.sample_size for hr in result.per_hour if hr.is_fitted)
    assert result.pooled.sample_size == total_all
    assert result.pooled.sample_size < 8759 * 2


# ---------------------------------------------------------------------------
# Tests for JSON serialization roundtrip
# ---------------------------------------------------------------------------


def _make_test_params() -> StudentTParams:
    """Build a StudentTParams with known values for serialization tests."""
    wind_per_hour = []
    solar_per_hour = []
    night_hours = [0, 1, 22, 23]

    for h in range(24):
        wind_per_hour.append(
            HourFitResult(
                hour=h,
                classification=HourClassification.DAYTIME,
                is_fitted=True,
                df=5.0,
                loc=0.1,
                scale=1.2,
                ks_statistic=0.02,
                ks_pvalue=0.5,
                sample_size=730,
                ks_rejected_at_05=False,
            )
        )
        if h in night_hours:
            solar_per_hour.append(
                HourFitResult(
                    hour=h,
                    classification=HourClassification.NIGHTTIME,
                    is_fitted=False,
                    df=float("inf"),
                    loc=0.0,
                    scale=0.0,
                    ks_statistic=0.0,
                    ks_pvalue=1.0,
                    sample_size=0,
                    ks_rejected_at_05=False,
                )
            )
        else:
            solar_per_hour.append(
                HourFitResult(
                    hour=h,
                    classification=HourClassification.DAYTIME,
                    is_fitted=True,
                    df=4.0,
                    loc=0.05,
                    scale=0.8,
                    ks_statistic=0.03,
                    ks_pvalue=0.3,
                    sample_size=730,
                    ks_rejected_at_05=False,
                )
            )

    wind_pooled = PooledFitResult(
        df=5.0,
        loc=0.1,
        scale=1.2,
        ks_statistic=0.01,
        ks_pvalue=0.8,
        sample_size=17520,
        ks_rejected_at_05=False,
        hours_excluded=[],
    )
    solar_pooled = PooledFitResult(
        df=4.0,
        loc=0.05,
        scale=0.8,
        ks_statistic=0.02,
        ks_pvalue=0.4,
        sample_size=14600,
        ks_rejected_at_05=False,
        hours_excluded=night_hours,
    )

    wind_result = ResourceFitResult(
        resource_type=ResourceType.WIND,
        per_hour=wind_per_hour,
        pooled=wind_pooled,
        night_hours=[],
        total_generators_pooled=10,
        total_days_in_source=365,
    )
    solar_result = ResourceFitResult(
        resource_type=ResourceType.SOLAR,
        per_hour=solar_per_hour,
        pooled=solar_pooled,
        night_hours=night_hours,
        total_generators_pooled=8,
        total_days_in_source=365,
    )

    return StudentTParams(
        network_source="ACTIVSg2000",
        wind=wind_result,
        solar=solar_result,
        representative_day_date="2016-07-19",
        script_version="0.1.0",
        generated_at="2026-03-04T00:00:00+00:00",
        fitting_method="scipy.stats.t.fit MLE",
        validation_method="scipy.stats.kstest two-sided",
    )


def test_write_student_t_json_roundtrip(tmp_path: Path) -> None:
    """Verify JSON write/read roundtrip preserves all fields."""
    params = _make_test_params()
    json_path = tmp_path / "student_t_params.json"

    write_student_t_json(params, json_path)
    loaded = load_student_t_json(json_path)

    # Top-level metadata
    assert loaded.network_source == params.network_source
    assert loaded.representative_day_date == params.representative_day_date
    assert loaded.fitting_method == params.fitting_method
    assert loaded.validation_method == params.validation_method

    # Wind per-hour
    assert len(loaded.wind.per_hour) == 24
    for orig, loaded_hr in zip(params.wind.per_hour, loaded.wind.per_hour):
        assert loaded_hr.hour == orig.hour
        assert loaded_hr.df == pytest.approx(orig.df)
        assert loaded_hr.loc == pytest.approx(orig.loc)
        assert loaded_hr.scale == pytest.approx(orig.scale)

    # Solar night hours
    assert loaded.solar.night_hours == params.solar.night_hours
    for hr in loaded.solar.per_hour:
        if hr.hour in params.solar.night_hours:
            assert math.isinf(hr.df)
            assert hr.is_fitted is False

    # Resource types
    assert loaded.wind.resource_type == ResourceType.WIND
    assert loaded.solar.resource_type == ResourceType.SOLAR

    # Pooled
    assert loaded.wind.pooled.hours_excluded == []
    assert loaded.solar.pooled.hours_excluded == params.solar.night_hours


def test_write_student_t_json_infinity_encoding(tmp_path: Path) -> None:
    """Verify that df=inf is serialized as the string "Infinity" in JSON."""
    params = _make_test_params()
    json_path = tmp_path / "student_t_params.json"
    write_student_t_json(params, json_path)

    raw_text = json_path.read_text()
    raw_data = json.loads(raw_text)

    # Find a nighttime solar hour and check its df value
    night_hours = params.solar.night_hours
    solar_per_hour = raw_data["solar"]["per_hour"]
    for entry in solar_per_hour:
        if entry["hour"] in night_hours:
            assert entry["df"] == "Infinity", f"Expected 'Infinity' string, got {entry['df']!r}"


# ---------------------------------------------------------------------------
# Tests for build_student_t_params
# ---------------------------------------------------------------------------


def test_build_student_t_params_metadata() -> None:
    """Verify metadata fields are set correctly."""
    changes = _make_synthetic_changes(n_gens=2, seed=7)
    wind_result = fit_resource_type(
        changes, night_hours=[], resource_type=ResourceType.WIND, total_generators=2
    )
    solar_result = fit_resource_type(
        changes, night_hours=[0, 1], resource_type=ResourceType.SOLAR, total_generators=2
    )

    params = build_student_t_params(
        wind_result=wind_result,
        solar_result=solar_result,
        representative_day_date="2016-07-19",
    )

    assert "MLE" in params.fitting_method
    assert "kstest" in params.validation_method
    assert params.network_source == "ACTIVSg2000"
