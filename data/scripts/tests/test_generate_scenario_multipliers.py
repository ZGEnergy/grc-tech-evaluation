"""Tests for generate_scenario_multipliers.py -- Correlated Scenario Multiplier Generation.

16 unit tests covering:
- Sample shape and sentinel zeros
- Deterministic RNG
- Iman-Conover marginals preserved and correlation imposed
- Single-gen noop
- Basic multiplier conversion and zero-forecast handling
- Clamp bounds and zero-forecast unchanged
- Night mask behavior
- CSV format and roundtrip
- Nighttime single-hour
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from scripts.fit_student_t import HourClassification, HourFitResult, ResourceType
from scripts.generate_scenario_multipliers import (
    GeneratorScenarioInput,
    ScenarioConfig,
    ScenarioMultiplierResult,
    apply_night_mask,
    clamp_multipliers,
    draw_independent_samples,
    errors_to_multipliers,
    generate_scenarios_single_hour,
    iman_conover_reorder,
    write_scenario_csv,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hour_fit(
    hour: int,
    *,
    is_fitted: bool = True,
    df: float = 5.0,
    loc: float = 0.0,
    scale: float = 1.0,
) -> HourFitResult:
    """Create an HourFitResult for testing."""
    return HourFitResult(
        hour=hour,
        classification=HourClassification.DAYTIME if is_fitted else HourClassification.NIGHTTIME,
        is_fitted=is_fitted,
        df=df,
        loc=loc,
        scale=scale,
        ks_statistic=0.05,
        ks_pvalue=0.5,
        sample_size=100,
        ks_rejected_at_05=False,
    )


def _make_24_hour_fits(
    *,
    night_hours: list[int] | None = None,
    df: float = 5.0,
    loc: float = 0.0,
    scale: float = 1.0,
) -> list[HourFitResult]:
    """Create a list of 24 HourFitResult entries."""
    if night_hours is None:
        night_hours = []
    return [
        _make_hour_fit(
            h,
            is_fitted=(h not in night_hours),
            df=df,
            loc=loc,
            scale=scale,
        )
        for h in range(24)
    ]


def _make_gen_input(
    gen_uid: str = "gen_1",
    resource_type: ResourceType = ResourceType.WIND,
    pmax: float = 100.0,
    forecast_value: float = 50.0,
    night_hours: list[int] | None = None,
) -> GeneratorScenarioInput:
    """Create a GeneratorScenarioInput for testing."""
    if night_hours is None:
        night_hours = []
    return GeneratorScenarioInput(
        gen_uid=gen_uid,
        resource_type=resource_type,
        pmax=pmax,
        forecast_values=np.full(24, forecast_value),
        night_hours=night_hours,
    )


# ---------------------------------------------------------------------------
# Test 1: samples shape
# ---------------------------------------------------------------------------


def test_draw_independent_samples_shape():
    """draw_independent_samples returns (n_scenarios, n_generators) array."""
    rng = np.random.Generator(np.random.PCG64(42))
    hour_fits = _make_24_hour_fits()
    samples = draw_independent_samples(50, 10, hour_fits, 12, rng)
    assert samples.shape == (50, 10)


# ---------------------------------------------------------------------------
# Test 2: sentinel zeros for nighttime
# ---------------------------------------------------------------------------


def test_draw_independent_samples_nighttime_zeros():
    """Nighttime hours produce all-zero samples (sentinel)."""
    rng = np.random.Generator(np.random.PCG64(42))
    hour_fits = _make_24_hour_fits(night_hours=[3])
    samples = draw_independent_samples(50, 5, hour_fits, 3, rng)
    assert samples.shape == (50, 5)
    np.testing.assert_array_equal(samples, 0.0)


# ---------------------------------------------------------------------------
# Test 3: deterministic RNG
# ---------------------------------------------------------------------------


def test_draw_independent_samples_deterministic():
    """Same seed produces identical samples."""
    hour_fits = _make_24_hour_fits()

    rng1 = np.random.Generator(np.random.PCG64(123))
    s1 = draw_independent_samples(20, 3, hour_fits, 10, rng1)

    rng2 = np.random.Generator(np.random.PCG64(123))
    s2 = draw_independent_samples(20, 3, hour_fits, 10, rng2)

    np.testing.assert_array_equal(s1, s2)


# ---------------------------------------------------------------------------
# Test 4: Iman-Conover preserves marginals
# ---------------------------------------------------------------------------


def test_iman_conover_marginals_preserved():
    """Iman-Conover reordering preserves the sorted values of each column."""
    rng_draw = np.random.Generator(np.random.PCG64(42))
    independent = rng_draw.standard_normal(size=(100, 4))

    target_corr = np.eye(4)
    target_corr[0, 1] = target_corr[1, 0] = 0.8
    target_corr[2, 3] = target_corr[3, 2] = 0.6

    rng_ic = np.random.Generator(np.random.PCG64(99))
    reordered = iman_conover_reorder(independent, target_corr, rng_ic)

    # Each column should have the same sorted values
    for j in range(4):
        np.testing.assert_allclose(
            np.sort(reordered[:, j]),
            np.sort(independent[:, j]),
            atol=1e-12,
        )


# ---------------------------------------------------------------------------
# Test 5: Iman-Conover imposes correlation
# ---------------------------------------------------------------------------


def test_iman_conover_correlation_imposed():
    """Iman-Conover produces rank correlation close to the target."""
    from scipy.stats import spearmanr

    rng_draw = np.random.Generator(np.random.PCG64(42))
    independent = rng_draw.standard_normal(size=(500, 3))

    target_corr = np.array(
        [
            [1.0, 0.7, 0.3],
            [0.7, 1.0, 0.5],
            [0.3, 0.5, 1.0],
        ]
    )

    rng_ic = np.random.Generator(np.random.PCG64(99))
    reordered = iman_conover_reorder(independent, target_corr, rng_ic)

    achieved_corr, _ = spearmanr(reordered)
    # Allow tolerance due to finite sample size
    np.testing.assert_allclose(achieved_corr, target_corr, atol=0.15)


# ---------------------------------------------------------------------------
# Test 6: single-gen noop
# ---------------------------------------------------------------------------


def test_iman_conover_single_gen_noop():
    """Iman-Conover with a single generator returns input unchanged."""
    rng = np.random.Generator(np.random.PCG64(42))
    independent = rng.standard_normal(size=(50, 1))
    target_corr = np.array([[1.0]])

    rng_ic = np.random.Generator(np.random.PCG64(99))
    reordered = iman_conover_reorder(independent, target_corr, rng_ic)

    np.testing.assert_array_equal(reordered, independent)


# ---------------------------------------------------------------------------
# Test 7: basic multiplier conversion
# ---------------------------------------------------------------------------


def test_errors_to_multipliers_basic():
    """errors_to_multipliers computes 1 + error/forecast correctly."""
    errors = np.array([[2.0, -3.0], [0.0, 5.0]])
    forecasts = np.array([10.0, 20.0])

    result = errors_to_multipliers(errors, forecasts)

    expected = np.array(
        [
            [1.0 + 2.0 / 10.0, 1.0 + (-3.0) / 20.0],
            [1.0 + 0.0 / 10.0, 1.0 + 5.0 / 20.0],
        ]
    )
    np.testing.assert_allclose(result, expected)


# ---------------------------------------------------------------------------
# Test 8: zero-forecast handling
# ---------------------------------------------------------------------------


def test_errors_to_multipliers_zero_forecast():
    """Zero forecast produces multiplier of 1.0 regardless of error."""
    errors = np.array([[5.0, -3.0]])
    forecasts = np.array([0.0, 10.0])

    result = errors_to_multipliers(errors, forecasts)

    assert result[0, 0] == 1.0  # zero forecast -> 1.0
    assert result[0, 1] == pytest.approx(1.0 + (-3.0) / 10.0)


# ---------------------------------------------------------------------------
# Test 9: clamp lower bound
# ---------------------------------------------------------------------------


def test_clamp_multipliers_lower_bound():
    """Negative multipliers are clamped to 0."""
    multipliers = np.array([[-0.5, 0.5]])
    forecasts = np.array([10.0, 10.0])
    pmaxes = np.array([100.0, 100.0])

    result = clamp_multipliers(multipliers, forecasts, pmaxes)

    assert result[0, 0] == 0.0
    assert result[0, 1] == 0.5


# ---------------------------------------------------------------------------
# Test 10: clamp upper bound
# ---------------------------------------------------------------------------


def test_clamp_multipliers_upper_bound():
    """Multipliers exceeding Pmax/forecast are clamped."""
    multipliers = np.array([[15.0, 0.5]])
    forecasts = np.array([10.0, 10.0])
    pmaxes = np.array([100.0, 100.0])

    result = clamp_multipliers(multipliers, forecasts, pmaxes)

    # Pmax/forecast = 100/10 = 10.0
    assert result[0, 0] == 10.0
    assert result[0, 1] == 0.5


# ---------------------------------------------------------------------------
# Test 11: clamp zero-forecast unchanged
# ---------------------------------------------------------------------------


def test_clamp_multipliers_zero_forecast_unchanged():
    """Zero-forecast generators keep their multiplier (should be 1.0)."""
    multipliers = np.array([[1.0, 2.0]])
    forecasts = np.array([0.0, 10.0])
    pmaxes = np.array([100.0, 100.0])

    result = clamp_multipliers(multipliers, forecasts, pmaxes)

    assert result[0, 0] == 1.0  # unchanged
    assert result[0, 1] == 2.0  # not clamped (2.0 < 100/10 = 10.0)


# ---------------------------------------------------------------------------
# Test 12: night mask sets ones for solar
# ---------------------------------------------------------------------------


def test_apply_night_mask_sets_ones():
    """Night mask sets solar generator multipliers to 1.0 during night hours."""
    multipliers = np.array([[0.5, 0.8]])
    resource_types = [ResourceType.SOLAR, ResourceType.WIND]

    result = apply_night_mask(multipliers, resource_types, hour=2, night_hours=[1, 2, 3])

    assert result[0, 0] == 1.0  # solar -> 1.0 at night
    assert result[0, 1] == 0.8  # wind unchanged


# ---------------------------------------------------------------------------
# Test 13: night mask empty noop
# ---------------------------------------------------------------------------


def test_apply_night_mask_empty_noop():
    """Empty night_hours list leaves multipliers unchanged."""
    multipliers = np.array([[0.5, 0.8]])
    resource_types = [ResourceType.SOLAR, ResourceType.WIND]

    result = apply_night_mask(multipliers, resource_types, hour=12, night_hours=[])

    np.testing.assert_array_equal(result, multipliers)


# ---------------------------------------------------------------------------
# Test 14: CSV format
# ---------------------------------------------------------------------------


def test_write_scenario_csv_format(tmp_path: Path):
    """write_scenario_csv produces correct header and row format."""
    results = [
        ScenarioMultiplierResult(
            gen_uid="gen_A",
            resource_type=ResourceType.WIND,
            multipliers=np.array(
                [
                    [1.0] * 24,
                    [0.9] * 24,
                ]
            ),
        ),
    ]

    csv_path = tmp_path / "test_scenarios.csv"
    write_scenario_csv(results, csv_path)

    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        assert header[0] == "gen_uid"
        assert header[1] == "scenario"
        assert header[2] == "HR_1"
        assert header[-1] == "HR_24"
        assert len(header) == 26  # gen_uid + scenario + 24 hours

        row1 = next(reader)
        assert row1[0] == "gen_A"
        assert row1[1] == "1"  # scenario number (1-indexed)
        assert float(row1[2]) == pytest.approx(1.0)

        row2 = next(reader)
        assert row2[0] == "gen_A"
        assert row2[1] == "2"
        assert float(row2[2]) == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Test 15: CSV roundtrip
# ---------------------------------------------------------------------------


def test_write_scenario_csv_roundtrip(tmp_path: Path):
    """CSV values round-trip within 6 decimal places."""
    rng = np.random.Generator(np.random.PCG64(42))
    mults = rng.uniform(0.5, 1.5, size=(3, 24))

    results = [
        ScenarioMultiplierResult(
            gen_uid="gen_X",
            resource_type=ResourceType.SOLAR,
            multipliers=mults,
        ),
    ]

    csv_path = tmp_path / "roundtrip.csv"
    write_scenario_csv(results, csv_path)

    # Read back
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) == 3
    for s in range(3):
        for h in range(24):
            col = f"HR_{h + 1}"
            read_val = float(rows[s][col])
            np.testing.assert_almost_equal(read_val, mults[s, h], decimal=6)


# ---------------------------------------------------------------------------
# Test 16: nighttime single-hour pipeline
# ---------------------------------------------------------------------------


def test_generate_scenarios_single_hour_nighttime():
    """Nighttime hour produces all-ones multipliers for solar generators."""
    night_hours = [0, 1, 2, 3, 22, 23]
    inputs = [
        _make_gen_input(
            gen_uid="solar_1",
            resource_type=ResourceType.SOLAR,
            pmax=100.0,
            forecast_value=50.0,
            night_hours=night_hours,
        ),
        _make_gen_input(
            gen_uid="solar_2",
            resource_type=ResourceType.SOLAR,
            pmax=80.0,
            forecast_value=40.0,
            night_hours=night_hours,
        ),
    ]
    hour_fits = _make_24_hour_fits(night_hours=night_hours)
    config = ScenarioConfig(n_scenarios=10, master_seed=42)
    corr = np.array([[1.0, 0.5], [0.5, 1.0]])
    rng = np.random.Generator(np.random.PCG64(42))

    # Hour 2 is nighttime
    multipliers, _, _ = generate_scenarios_single_hour(inputs, 2, hour_fits, corr, config, rng)

    # All multipliers should be 1.0 for nighttime solar
    np.testing.assert_array_equal(multipliers, 1.0)
