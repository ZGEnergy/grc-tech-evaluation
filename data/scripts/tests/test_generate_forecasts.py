"""Tests for generate_forecasts.py — Forecast Generation from Actuals (PRD 04/03).

All tests are self-contained with synthetic data. No external file dependencies.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from scripts.fit_student_t import (
    HourClassification,
    HourFitResult,
    PooledFitResult,
    ResourceFitResult,
    ResourceType,
    StudentTParams,
)
from scripts.generate_forecasts import (
    ForecastConfig,
    GeneratorProfile,
    add_bias,
    clamp_forecast,
    generate_forecast_single,
    inject_noise,
    load_actual_profiles,
    smooth_profile,
    write_forecast_csv,
    zero_night_hours,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HOUR_COLUMNS = [f"HR_{k}" for k in range(1, 25)]


def _write_synthetic_csv(path: Path, rows: list[dict[str, str | float]]) -> None:
    """Write a synthetic canonical CSV file with gen_uid and HR_1..HR_24."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["gen_uid"] + _HOUR_COLUMNS
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _make_row(gen_uid: str, values: list[float]) -> dict[str, str | float]:
    """Build a CSV row dict from gen_uid and 24 hourly values."""
    row: dict[str, str | float] = {"gen_uid": gen_uid}
    for i, col in enumerate(_HOUR_COLUMNS):
        row[col] = values[i]
    return row


def _make_student_t_params(
    *,
    wind_df: float = 4.0,
    wind_loc: float = 0.0,
    wind_scale: float = 0.05,
    solar_df: float = 3.5,
    solar_loc: float = 0.0,
    solar_scale: float = 0.04,
    night_hours: list[int] | None = None,
) -> StudentTParams:
    """Build a minimal StudentTParams for testing.

    All daytime hours get the same df/loc/scale. Night hours get sentinel values.
    """
    if night_hours is None:
        night_hours = []

    def _make_resource(
        rt: ResourceType,
        df: float,
        loc: float,
        scale: float,
        nights: list[int],
    ) -> ResourceFitResult:
        per_hour: list[HourFitResult] = []
        for h in range(24):
            if h in nights:
                per_hour.append(
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
                per_hour.append(
                    HourFitResult(
                        hour=h,
                        classification=HourClassification.DAYTIME,
                        is_fitted=True,
                        df=df,
                        loc=loc,
                        scale=scale,
                        ks_statistic=0.05,
                        ks_pvalue=0.5,
                        sample_size=1000,
                        ks_rejected_at_05=False,
                    )
                )

        pooled = PooledFitResult(
            df=df,
            loc=loc,
            scale=scale,
            ks_statistic=0.05,
            ks_pvalue=0.5,
            sample_size=24000,
            ks_rejected_at_05=False,
            hours_excluded=sorted(nights),
        )

        return ResourceFitResult(
            resource_type=rt,
            per_hour=per_hour,
            pooled=pooled,
            night_hours=sorted(nights),
            total_generators_pooled=10,
            total_days_in_source=365,
        )

    return StudentTParams(
        network_source="ACTIVSg2000",
        wind=_make_resource(ResourceType.WIND, wind_df, wind_loc, wind_scale, []),
        solar=_make_resource(ResourceType.SOLAR, solar_df, solar_loc, solar_scale, night_hours),
        representative_day_date="2019-07-15",
        script_version="0.1.0",
        generated_at="2024-01-01T00:00:00+00:00",
        fitting_method="scipy.stats.t.fit MLE",
        validation_method="scipy.stats.kstest two-sided",
    )


# ---------------------------------------------------------------------------
# Test 1: load_actual_profiles shape
# ---------------------------------------------------------------------------


def test_load_actual_profiles_shape(tmp_path: Path) -> None:
    """3-generator CSV produces 3 GeneratorProfile objects, each with 24 values."""
    rows = [
        _make_row("GEN_1", [float(i) for i in range(24)]),
        _make_row("GEN_2", [10.0] * 24),
        _make_row("GEN_3", [5.0 * i for i in range(24)]),
    ]
    csv_path = tmp_path / "wind_actual_24h.csv"
    _write_synthetic_csv(csv_path, rows)

    profiles = load_actual_profiles(csv_path, ResourceType.WIND)

    assert len(profiles) == 3
    for p in profiles:
        assert len(p.values) == 24


# ---------------------------------------------------------------------------
# Test 2: load_actual_profiles pmax from max value
# ---------------------------------------------------------------------------


def test_load_actual_profiles_pmax_from_max_value(tmp_path: Path) -> None:
    """pmax equals the maximum observed value across 24 hours."""
    values = [0.0, 10.0, 50.0, 30.0] + [0.0] * 20
    rows = [_make_row("GEN_A", values)]
    csv_path = tmp_path / "wind_actual_24h.csv"
    _write_synthetic_csv(csv_path, rows)

    profiles = load_actual_profiles(csv_path, ResourceType.WIND)

    assert profiles[0].pmax == 50.0


# ---------------------------------------------------------------------------
# Test 3: load_actual_profiles all-zero pmax
# ---------------------------------------------------------------------------


def test_load_actual_profiles_all_zero_pmax(tmp_path: Path) -> None:
    """All-zero generator has pmax == 0.0."""
    rows = [_make_row("GEN_ZERO", [0.0] * 24)]
    csv_path = tmp_path / "solar_actual_24h.csv"
    _write_synthetic_csv(csv_path, rows)

    profiles = load_actual_profiles(csv_path, ResourceType.SOLAR)

    assert profiles[0].pmax == 0.0


# ---------------------------------------------------------------------------
# Test 4: smooth_profile window=1 identity
# ---------------------------------------------------------------------------


def test_smooth_profile_window_1_identity() -> None:
    """Window of 1 returns the input unchanged."""
    values = np.arange(24, dtype=float)
    result = smooth_profile(values, window=1)
    np.testing.assert_array_equal(result, values)


# ---------------------------------------------------------------------------
# Test 5: smooth_profile window=3 center
# ---------------------------------------------------------------------------


def test_smooth_profile_window_3_center() -> None:
    """Window=3 at an interior point averages 3 neighbors."""
    values = np.zeros(24)
    values[5] = 30.0
    # smoothed[5] = mean(values[4], values[5], values[6]) = mean(0, 30, 0) = 10
    result = smooth_profile(values, window=3)
    assert result[5] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Test 6: smooth_profile edge handling
# ---------------------------------------------------------------------------


def test_smooth_profile_edge_handling() -> None:
    """Partial window at left edge uses only 2 elements."""
    values = np.ones(24)
    values[0] = 10.0
    # smoothed[0] with window=3: partial at left edge -> mean(values[0], values[1])
    # = mean(10.0, 1.0) = 5.5
    result = smooth_profile(values, window=3)
    assert result[0] == pytest.approx(5.5)


# ---------------------------------------------------------------------------
# Test 7: add_bias positive wind
# ---------------------------------------------------------------------------


def test_add_bias_positive_wind() -> None:
    """Wind bias +2% of pmax=500 adds 10.0 to every hour."""
    smoothed = np.full(24, 100.0)
    result = add_bias(smoothed, pmax=500.0, bias_fraction=0.02)
    np.testing.assert_allclose(result, 110.0)


# ---------------------------------------------------------------------------
# Test 8: add_bias negative solar
# ---------------------------------------------------------------------------


def test_add_bias_negative_solar() -> None:
    """Solar bias -1% of pmax=400 subtracts 4.0 from every hour."""
    smoothed = np.full(24, 200.0)
    result = add_bias(smoothed, pmax=400.0, bias_fraction=-0.01)
    np.testing.assert_allclose(result, 196.0)


# ---------------------------------------------------------------------------
# Test 9: inject_noise with zero actual produces zero noise
# ---------------------------------------------------------------------------


def test_inject_noise_zero_actual_produces_zero_noise() -> None:
    """When actual is all zeros, output equals biased (no noise added)."""
    biased = np.full(24, 50.0)
    actual = np.zeros(24)
    params = _make_student_t_params()
    rng = np.random.Generator(np.random.PCG64(99))

    result = inject_noise(biased, actual, params, ResourceType.WIND, rng)

    np.testing.assert_array_equal(result, biased)


# ---------------------------------------------------------------------------
# Test 10: inject_noise deterministic with seed
# ---------------------------------------------------------------------------


def test_inject_noise_deterministic_with_seed() -> None:
    """Same seed produces bitwise identical results."""
    biased = np.linspace(10.0, 100.0, 24)
    actual = np.linspace(5.0, 80.0, 24)
    params = _make_student_t_params()

    rng1 = np.random.Generator(np.random.PCG64(123))
    result1 = inject_noise(biased.copy(), actual, params, ResourceType.WIND, rng1)

    rng2 = np.random.Generator(np.random.PCG64(123))
    result2 = inject_noise(biased.copy(), actual, params, ResourceType.WIND, rng2)

    np.testing.assert_array_equal(result1, result2)


# ---------------------------------------------------------------------------
# Test 11: clamp_forecast lower bound
# ---------------------------------------------------------------------------


def test_clamp_forecast_lower_bound() -> None:
    """Negative values become 0.0, non-negative unchanged."""
    forecast = np.array([-10.0, -1.0, 0.0, 50.0] + [25.0] * 20)
    result = clamp_forecast(forecast, pmax=100.0)

    assert result[0] == 0.0
    assert result[1] == 0.0
    assert result[2] == 0.0
    assert result[3] == 50.0


# ---------------------------------------------------------------------------
# Test 12: clamp_forecast upper bound
# ---------------------------------------------------------------------------


def test_clamp_forecast_upper_bound() -> None:
    """Values above pmax become pmax, values at or below unchanged."""
    forecast = np.array([0.0, 25.0, 50.0, 75.0, 100.0] + [30.0] * 19)
    result = clamp_forecast(forecast, pmax=50.0)

    assert result[0] == 0.0
    assert result[1] == 25.0
    assert result[2] == 50.0
    assert result[3] == 50.0
    assert result[4] == 50.0


# ---------------------------------------------------------------------------
# Test 13: zero_night_hours solar
# ---------------------------------------------------------------------------


def test_zero_night_hours_solar() -> None:
    """Night hours are zeroed, daylight hours unchanged."""
    forecast = np.full(24, 10.0)
    night_hours = [0, 1, 2, 22, 23]
    result = zero_night_hours(forecast, night_hours)

    for h in night_hours:
        assert result[h] == 0.0
    for h in range(3, 22):
        assert result[h] == 10.0


# ---------------------------------------------------------------------------
# Test 14: generate_forecast_single pipeline order
# ---------------------------------------------------------------------------


def test_generate_forecast_single_pipeline_order() -> None:
    """Full pipeline: forecast differs from actual, respects bounds and night hours."""
    ramp = np.linspace(0.0, 100.0, 24)
    actual = GeneratorProfile(
        gen_uid="SOLAR_1",
        resource_type=ResourceType.SOLAR,
        pmax=100.0,
        values=ramp,
    )
    night_hours = [0, 1, 2, 22, 23]
    params = _make_student_t_params(night_hours=night_hours)
    config = ForecastConfig(smoothing_window=3, master_seed=42)
    rng = np.random.Generator(np.random.PCG64(42))

    result = generate_forecast_single(actual, params, config, night_hours, rng)

    # (a) Forecast differs from actual due to smoothing + noise
    assert not np.array_equal(result.values, ramp)

    # (b) Within [0, Pmax]
    assert np.all(result.values >= 0.0)
    assert np.all(result.values <= 100.0)

    # (c) Night hours are zero
    for h in night_hours:
        assert result.values[h] == 0.0


# ---------------------------------------------------------------------------
# Test 15: generate_forecast_single zero pmax returns zero
# ---------------------------------------------------------------------------


def test_generate_forecast_single_zero_pmax_returns_zero() -> None:
    """Zero-capacity generator returns all-zero forecast."""
    actual = GeneratorProfile(
        gen_uid="DEAD_GEN",
        resource_type=ResourceType.WIND,
        pmax=0.0,
        values=np.zeros(24),
    )
    params = _make_student_t_params()
    config = ForecastConfig()
    rng = np.random.Generator(np.random.PCG64(42))

    result = generate_forecast_single(actual, params, config, [], rng)

    np.testing.assert_array_equal(result.values, np.zeros(24))


# ---------------------------------------------------------------------------
# Test 16: write_forecast_csv roundtrip
# ---------------------------------------------------------------------------


def test_write_forecast_csv_roundtrip(tmp_path: Path) -> None:
    """Write then read back preserves gen_uids and values (to 4 dp)."""
    profiles = [
        GeneratorProfile(
            gen_uid="W_1",
            resource_type=ResourceType.WIND,
            pmax=100.0,
            values=np.linspace(0.0, 95.1234, 24),
        ),
        GeneratorProfile(
            gen_uid="W_2",
            resource_type=ResourceType.WIND,
            pmax=200.0,
            values=np.linspace(10.5678, 180.9999, 24),
        ),
    ]
    csv_path = tmp_path / "wind_forecast_24h.csv"
    write_forecast_csv(profiles, csv_path)

    loaded = load_actual_profiles(csv_path, ResourceType.WIND)

    assert len(loaded) == 2
    assert loaded[0].gen_uid == "W_1"
    assert loaded[1].gen_uid == "W_2"

    for orig, back in zip(profiles, loaded):
        np.testing.assert_allclose(back.values, orig.values, atol=1e-4)
