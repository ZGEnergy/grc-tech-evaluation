"""Tests for tiny_stochastic_scenarios.py -- Stochastic Scenario Generation (TINY).

All tests use synthetic fixtures. No dependency on actual RTS-GMLC data files.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.tiny_stochastic_scenarios import (
    HOUR_COLUMNS,
    HOURS_PER_YEAR,
    SOLAR_NIGHTTIME_HOURS,
    CorrelationResult,
    ForecastConfig,
    GeneratorMapping,
    GeneratorProfile,
    ResourceType,
    ScenarioMultiplierSet,
    StudentTFit,
    compute_capacity_factor_changes,
    estimate_tiny_correlation,
    fit_student_t_pooled,
    generate_forecast,
    generate_scenario_multipliers,
    iman_conover,
    load_rts_gmlc_full_year_profiles,
    main,
    map_tiny_to_rts_gmlc_generators,
    smooth_profile,
    write_forecast_actual_csvs,
    write_scenario_multipliers_csv,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(42))


@pytest.fixture
def synthetic_wind_8760() -> np.ndarray:
    """Synthetic 8760x4 wind profiles."""
    rng = np.random.Generator(np.random.PCG64(99))
    base = 0.35 + 0.15 * np.sin(np.linspace(0, 2 * np.pi * 365, HOURS_PER_YEAR))
    profiles = np.column_stack(
        [
            base + rng.normal(0, 0.05, HOURS_PER_YEAR),
            base * 0.9 + rng.normal(0, 0.04, HOURS_PER_YEAR),
            base * 1.1 + rng.normal(0, 0.06, HOURS_PER_YEAR),
            base * 0.95 + rng.normal(0, 0.05, HOURS_PER_YEAR),
        ]
    )
    return np.clip(profiles, 0, 1) * 150.0  # MW


@pytest.fixture
def synthetic_solar_8760() -> np.ndarray:
    """Synthetic 8760x3 solar profiles with nighttime zeros."""
    rng = np.random.Generator(np.random.PCG64(101))
    profiles = np.zeros((HOURS_PER_YEAR, 3))
    for d in range(365):
        for h in range(24):
            hour_ending = h + 1
            if hour_ending in SOLAR_NIGHTTIME_HOURS:
                continue
            # Simple bell curve for daytime
            cf = max(0, 0.8 * np.sin(np.pi * (h - 6) / 12))
            for g in range(3):
                noise = rng.normal(0, 0.03)
                profiles[d * 24 + h, g] = max(0, (cf + noise)) * 100.0
    return profiles


@pytest.fixture
def wind_gen_ids() -> list[str]:
    return ["WIND_RTS_1", "WIND_RTS_2", "WIND_RTS_3", "WIND_RTS_4"]


@pytest.fixture
def solar_gen_ids() -> list[str]:
    return ["SOLAR_RTS_1", "SOLAR_RTS_2", "SOLAR_RTS_3"]


@pytest.fixture
def wind_fit() -> StudentTFit:
    return StudentTFit(
        resource_type=ResourceType.WIND,
        df=4.5,
        loc=0.001,
        scale=0.05,
        sample_size=100000,
        num_generators_pooled=4,
    )


@pytest.fixture
def solar_fit() -> StudentTFit:
    return StudentTFit(
        resource_type=ResourceType.SOLAR,
        df=3.8,
        loc=-0.002,
        scale=0.04,
        sample_size=60000,
        num_generators_pooled=3,
    )


@pytest.fixture
def config() -> ForecastConfig:
    return ForecastConfig(
        smoothing_window=3,
        wind_bias_fraction=0.02,
        solar_bias_fraction=-0.01,
        master_seed=42,
        num_scenarios=50,
    )


@pytest.fixture
def sample_wind_actual() -> GeneratorProfile:
    """A synthetic 24-hour wind actual profile."""
    values = np.array(
        [
            63.0,
            67.5,
            72.0,
            75.0,
            70.5,
            64.5,
            57.0,
            48.0,
            42.0,
            37.5,
            33.0,
            30.0,
            27.0,
            30.0,
            34.5,
            40.5,
            48.0,
            57.0,
            66.0,
            75.0,
            82.5,
            87.0,
            78.0,
            69.0,
        ]
    )
    return GeneratorProfile(
        gen_uid="WIND_1",
        bus_id=25,
        pmax_mw=150.0,
        hourly_mw=values,
    )


@pytest.fixture
def sample_solar_actual() -> GeneratorProfile:
    """A synthetic 24-hour solar actual profile with nighttime zeros."""
    values = np.array(
        [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            5.0,
            18.0,
            42.0,
            62.0,
            78.0,
            85.0,
            88.0,
            82.0,
            70.0,
            52.0,
            30.0,
            10.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]
    )
    return GeneratorProfile(
        gen_uid="SOLAR_1",
        bus_id=18,
        pmax_mw=100.0,
        hourly_mw=values,
    )


@pytest.fixture
def tiny_units_csv(tmp_path: Path) -> Path:
    """Create a renewable_units.csv for TINY."""
    csv_path = tmp_path / "renewable_units.csv"
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid", "bus_id", "type", "pmax_mw", "area"])
        writer.writerow(["WIND_1", 25, "wind", 243.88, 2])
        writer.writerow(["WIND_2", 2, "wind", 243.88, 1])
        writer.writerow(["WIND_3", 22, "wind", 243.88, 3])
        writer.writerow(["SOLAR_1", 18, "solar", 243.88, 2])
        writer.writerow(["SOLAR_2", 15, "solar", 243.88, 3])
    return csv_path


@pytest.fixture
def sample_mappings() -> list[GeneratorMapping]:
    return [
        GeneratorMapping("WIND_1", 25, ResourceType.WIND, "WIND_RTS_1", 0),
        GeneratorMapping("WIND_2", 2, ResourceType.WIND, "WIND_RTS_2", 1),
        GeneratorMapping("WIND_3", 22, ResourceType.WIND, "WIND_RTS_3", 2),
        GeneratorMapping("SOLAR_1", 18, ResourceType.SOLAR, "SOLAR_RTS_1", 0),
        GeneratorMapping("SOLAR_2", 15, ResourceType.SOLAR, "SOLAR_RTS_2", 1),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_load_rts_gmlc_profiles_shape() -> None:
    """Test 1: Synthetic fallback produces correct shape (8760, N_gens)."""
    # Use a nonexistent directory to trigger synthetic fallback
    profiles, gen_ids = load_rts_gmlc_full_year_profiles(
        Path("/nonexistent/rts_gmlc"), ResourceType.WIND
    )
    assert profiles.shape[0] == HOURS_PER_YEAR
    assert profiles.shape[1] == len(gen_ids)
    assert profiles.shape[1] >= 3  # At least 3 wind generators
    assert all(isinstance(gid, str) for gid in gen_ids)

    # Solar
    profiles_s, gen_ids_s = load_rts_gmlc_full_year_profiles(
        Path("/nonexistent/rts_gmlc"), ResourceType.SOLAR
    )
    assert profiles_s.shape[0] == HOURS_PER_YEAR
    assert profiles_s.shape[1] == len(gen_ids_s)


def test_compute_cf_changes_shape_and_values(
    synthetic_wind_8760: np.ndarray,
) -> None:
    """Test 2: CF changes have correct shape and reasonable values."""
    pmax = np.max(synthetic_wind_8760, axis=0)
    changes = compute_capacity_factor_changes(synthetic_wind_8760, pmax)

    assert changes.shape == (HOURS_PER_YEAR - 1, synthetic_wind_8760.shape[1])
    # CF changes should be small (between -1 and 1 after normalization)
    assert np.all(changes >= -1.5)
    assert np.all(changes <= 1.5)
    # Mean should be near zero
    assert abs(np.mean(changes)) < 0.1


def test_fit_student_t_pooled_recovers_params() -> None:
    """Test 3: Fitting recovers approximate params from known distribution."""
    rng = np.random.Generator(np.random.PCG64(42))
    true_df = 5.0
    n_hours = HOURS_PER_YEAR
    n_gens = 3

    # Generate data from known Student-t
    raw = rng.standard_t(true_df, size=(n_hours, n_gens))
    # Construct as "profiles" that produce known CF changes
    profiles = np.cumsum(raw, axis=0)
    # Pad to 8760
    profiles_8760 = np.zeros((HOURS_PER_YEAR, n_gens))
    profiles_8760[: profiles.shape[0]] = profiles

    changes = compute_capacity_factor_changes(profiles_8760)
    fit = fit_student_t_pooled(changes, ResourceType.WIND)

    # df should be in a reasonable range (heavy-tailed)
    assert fit.df > 1.0
    assert fit.df < 50.0
    assert fit.sample_size > 0
    assert fit.num_generators_pooled == n_gens
    assert fit.resource_type == ResourceType.WIND


def test_fit_student_t_pooled_solar_excludes_night() -> None:
    """Test 4: Solar fitting excludes nighttime hours."""
    rng = np.random.Generator(np.random.PCG64(55))
    n_gens = 2
    profiles = np.zeros((HOURS_PER_YEAR, n_gens))

    # Set daytime hours to nonzero
    for d in range(365):
        for h in range(24):
            hour_ending = h + 1
            if hour_ending not in SOLAR_NIGHTTIME_HOURS:
                profiles[d * 24 + h, :] = rng.random(n_gens) * 100

    changes = compute_capacity_factor_changes(profiles)

    wind_fit = fit_student_t_pooled(changes, ResourceType.WIND)
    solar_fit = fit_student_t_pooled(changes, ResourceType.SOLAR)

    # Solar should have fewer samples because nighttime hours are excluded
    assert solar_fit.sample_size < wind_fit.sample_size
    assert solar_fit.resource_type == ResourceType.SOLAR


def test_map_tiny_to_rts_gmlc_generators_correct_count(
    tiny_units_csv: Path,
    wind_gen_ids: list[str],
    solar_gen_ids: list[str],
) -> None:
    """Test 5: Mapping produces 5 entries (3 wind + 2 solar)."""
    mappings = map_tiny_to_rts_gmlc_generators(tiny_units_csv, wind_gen_ids, solar_gen_ids)
    assert len(mappings) == 5
    wind_count = sum(1 for m in mappings if m.resource_type == ResourceType.WIND)
    solar_count = sum(1 for m in mappings if m.resource_type == ResourceType.SOLAR)
    assert wind_count == 3
    assert solar_count == 2


def test_map_tiny_to_rts_gmlc_generators_ordinal_order(
    tiny_units_csv: Path,
    wind_gen_ids: list[str],
    solar_gen_ids: list[str],
) -> None:
    """Test 6: Mappings use ordinal position within resource type."""
    mappings = map_tiny_to_rts_gmlc_generators(tiny_units_csv, wind_gen_ids, solar_gen_ids)

    wind_mappings = [m for m in mappings if m.resource_type == ResourceType.WIND]
    solar_mappings = [m for m in mappings if m.resource_type == ResourceType.SOLAR]

    # Wind ordinals should be 0, 1, 2
    for i, m in enumerate(wind_mappings):
        assert m.ordinal == i
        assert m.rts_gmlc_gen_id == wind_gen_ids[i]

    # Solar ordinals should be 0, 1
    for i, m in enumerate(solar_mappings):
        assert m.ordinal == i
        assert m.rts_gmlc_gen_id == solar_gen_ids[i]


def test_estimate_tiny_correlation_shape_and_psd(
    synthetic_wind_8760: np.ndarray,
    synthetic_solar_8760: np.ndarray,
    sample_mappings: list[GeneratorMapping],
) -> None:
    """Test 7: Correlation matrix is 5x5 and positive semi-definite."""
    all_profiles = np.hstack([synthetic_wind_8760, synthetic_solar_8760])
    all_ids = [
        "WIND_RTS_1",
        "WIND_RTS_2",
        "WIND_RTS_3",
        "WIND_RTS_4",
        "SOLAR_RTS_1",
        "SOLAR_RTS_2",
        "SOLAR_RTS_3",
    ]

    corr = estimate_tiny_correlation(all_profiles, sample_mappings, all_ids)

    matrix = np.array(corr.matrix)
    assert matrix.shape == (5, 5)
    assert len(corr.generator_order) == 5

    # Diagonal should be 1.0
    np.testing.assert_allclose(np.diag(matrix), 1.0, atol=1e-10)

    # Should be symmetric
    np.testing.assert_allclose(matrix, matrix.T, atol=1e-10)

    # Should be PSD
    eigvals = np.linalg.eigvalsh(matrix)
    assert np.all(eigvals >= -1e-10)
    assert corr.is_psd


def test_smooth_profile_window_3() -> None:
    """Test 8: Window-3 smoothing produces correct centered averages."""
    values = np.zeros(24)
    values[5] = 30.0  # Spike at index 5

    smoothed = smooth_profile(values, window=3)

    # Index 5: mean of indices 4, 5, 6 = (0 + 30 + 0) / 3 = 10
    assert smoothed[5] == pytest.approx(10.0)
    # Index 4: mean of indices 3, 4, 5 = (0 + 0 + 30) / 3 = 10
    assert smoothed[4] == pytest.approx(10.0)
    # Index 6: mean of indices 5, 6, 7 = (30 + 0 + 0) / 3 = 10
    assert smoothed[6] == pytest.approx(10.0)
    # Index 3: mean of indices 2, 3, 4 = 0
    assert smoothed[3] == pytest.approx(0.0)

    # Window of 1 should return identity
    identity = smooth_profile(values, window=1)
    np.testing.assert_array_equal(identity, values)


def test_generate_forecast_bounded(
    sample_wind_actual: GeneratorProfile,
    wind_fit: StudentTFit,
    config: ForecastConfig,
    rng: np.random.Generator,
) -> None:
    """Test 9: Forecast values are bounded in [0, Pmax]."""
    forecast = generate_forecast(sample_wind_actual, wind_fit, config, rng)

    assert np.all(forecast.hourly_mw >= 0.0)
    assert np.all(forecast.hourly_mw <= sample_wind_actual.pmax_mw + 1e-10)
    assert forecast.gen_uid == sample_wind_actual.gen_uid
    assert forecast.pmax_mw == sample_wind_actual.pmax_mw


def test_generate_forecast_deterministic(
    sample_wind_actual: GeneratorProfile,
    wind_fit: StudentTFit,
    config: ForecastConfig,
) -> None:
    """Test 10: Same seed produces identical forecasts."""
    rng1 = np.random.Generator(np.random.PCG64(42))
    rng2 = np.random.Generator(np.random.PCG64(42))

    forecast1 = generate_forecast(sample_wind_actual, wind_fit, config, rng1)
    forecast2 = generate_forecast(sample_wind_actual, wind_fit, config, rng2)

    np.testing.assert_array_equal(forecast1.hourly_mw, forecast2.hourly_mw)


def test_iman_conover_preserves_marginals(rng: np.random.Generator) -> None:
    """Test 11: Iman-Conover preserves marginal distributions (same values)."""
    n_samples = 200
    n_vars = 4
    samples = rng.standard_normal(size=(n_samples, n_vars)) * 5.0

    target_corr = np.eye(n_vars)
    target_corr[0, 1] = target_corr[1, 0] = 0.7
    target_corr[2, 3] = target_corr[3, 2] = -0.5

    rng_ic = np.random.Generator(np.random.PCG64(99))
    reordered = iman_conover(samples, target_corr, rng_ic)

    assert reordered.shape == samples.shape

    # Each column should contain the same set of values (just reordered)
    for j in range(n_vars):
        np.testing.assert_array_almost_equal(
            np.sort(reordered[:, j]),
            np.sort(samples[:, j]),
            decimal=10,
        )


def test_iman_conover_induces_target_correlation(rng: np.random.Generator) -> None:
    """Test 12: Iman-Conover achieves approximate target rank correlation."""
    from scipy.stats import spearmanr

    n_samples = 500
    n_vars = 3
    samples = rng.standard_normal(size=(n_samples, n_vars))

    target_corr = np.array(
        [
            [1.0, 0.8, 0.3],
            [0.8, 1.0, 0.5],
            [0.3, 0.5, 1.0],
        ]
    )

    rng_ic = np.random.Generator(np.random.PCG64(77))
    reordered = iman_conover(samples, target_corr, rng_ic)

    achieved_corr, _ = spearmanr(reordered)
    # Allow tolerance due to finite sample size
    np.testing.assert_allclose(achieved_corr, target_corr, atol=0.15)


def test_scenario_multipliers_shape(
    sample_wind_actual: GeneratorProfile,
    sample_solar_actual: GeneratorProfile,
    wind_fit: StudentTFit,
    solar_fit: StudentTFit,
    config: ForecastConfig,
) -> None:
    """Test 13: Scenario multipliers have shape (50, 5, 24)."""
    rng1 = np.random.Generator(np.random.PCG64(42))
    rng2 = np.random.Generator(np.random.PCG64(43))

    # Create 3 wind + 2 solar forecasts
    wind_forecasts = [
        generate_forecast(
            GeneratorProfile(f"WIND_{i + 1}", 25 + i, 150.0, sample_wind_actual.hourly_mw.copy()),
            wind_fit,
            config,
            rng1,
        )
        for i in range(3)
    ]
    solar_forecasts = [
        generate_forecast(
            GeneratorProfile(f"SOLAR_{i + 1}", 18 + i, 100.0, sample_solar_actual.hourly_mw.copy()),
            solar_fit,
            config,
            rng2,
        )
        for i in range(2)
    ]

    corr = CorrelationResult(
        matrix=np.eye(5).tolist(),
        generator_order=[f.gen_uid for f in wind_forecasts + solar_forecasts],
        is_psd=True,
        psd_projected=False,
    )

    scenario_set = generate_scenario_multipliers(
        wind_forecasts, solar_forecasts, wind_fit, solar_fit, corr, config
    )

    assert scenario_set.multipliers.shape == (50, 5, 24)
    assert scenario_set.num_scenarios == 50
    assert len(scenario_set.generator_order) == 5


def test_scenario_multipliers_physical_bounds(
    sample_wind_actual: GeneratorProfile,
    sample_solar_actual: GeneratorProfile,
    wind_fit: StudentTFit,
    solar_fit: StudentTFit,
    config: ForecastConfig,
) -> None:
    """Test 14: All scenario multipliers respect physical bounds >= 0."""
    rng1 = np.random.Generator(np.random.PCG64(42))

    wind_forecasts = [
        generate_forecast(
            GeneratorProfile("WIND_1", 25, 150.0, sample_wind_actual.hourly_mw.copy()),
            wind_fit,
            config,
            rng1,
        )
    ]
    solar_forecasts = [
        generate_forecast(
            GeneratorProfile("SOLAR_1", 18, 100.0, sample_solar_actual.hourly_mw.copy()),
            solar_fit,
            config,
            np.random.Generator(np.random.PCG64(43)),
        )
    ]

    corr = CorrelationResult(
        matrix=np.eye(2).tolist(),
        generator_order=["WIND_1", "SOLAR_1"],
        is_psd=True,
        psd_projected=False,
    )

    scenario_set = generate_scenario_multipliers(
        wind_forecasts, solar_forecasts, wind_fit, solar_fit, corr, config
    )

    # All multipliers must be >= 0
    assert np.all(scenario_set.multipliers >= 0.0)

    # Solar nighttime multipliers should be 1.0
    for h in range(24):
        hour_ending = h + 1
        if hour_ending in SOLAR_NIGHTTIME_HOURS:
            # Solar is the second generator (index 1)
            solar_idx = 1
            np.testing.assert_array_equal(scenario_set.multipliers[:, solar_idx, h], 1.0)


def test_write_scenario_multipliers_csv_format(tmp_path: Path) -> None:
    """Test 15: Scenario multipliers CSV has correct format."""
    n_scenarios = 5
    n_gens = 3
    multipliers = np.ones((n_scenarios, n_gens, 24)) * 1.05
    gen_order = ["WIND_1", "WIND_2", "SOLAR_1"]

    scenario_set = ScenarioMultiplierSet(
        multipliers=multipliers,
        generator_order=gen_order,
        num_scenarios=n_scenarios,
        seed_used=42,
    )

    csv_path = tmp_path / "scenarios" / "scenario_multipliers_50x24.csv"
    write_scenario_multipliers_csv(scenario_set, csv_path)

    assert csv_path.exists()

    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        headers = next(reader)

    # Check header: scenario, gen_uid, HR_1..HR_24
    assert headers[0] == "scenario"
    assert headers[1] == "gen_uid"
    assert headers[2:] == HOUR_COLUMNS

    # Count rows: should be n_scenarios * n_gens
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        next(reader)  # skip header
        rows = list(reader)
    assert len(rows) == n_scenarios * n_gens


def test_write_forecast_actual_csvs_columns(tmp_path: Path) -> None:
    """Test 16: Forecast/actual CSVs have correct columns."""
    wind_f = [
        GeneratorProfile("WIND_1", 25, 150.0, np.ones(24) * 50.0),
    ]
    wind_a = [
        GeneratorProfile("WIND_1", 25, 150.0, np.ones(24) * 48.0),
    ]
    solar_f = [
        GeneratorProfile("SOLAR_1", 18, 100.0, np.ones(24) * 30.0),
    ]
    solar_a = [
        GeneratorProfile("SOLAR_1", 18, 100.0, np.ones(24) * 28.0),
    ]

    write_forecast_actual_csvs(wind_f, wind_a, solar_f, solar_a, tmp_path)

    for filename in [
        "wind_forecast_24h.csv",
        "wind_actual_24h.csv",
        "solar_forecast_24h.csv",
        "solar_actual_24h.csv",
    ]:
        fpath = tmp_path / filename
        assert fpath.exists(), f"{filename} not found"

        with open(fpath, newline="") as fh:
            reader = csv.reader(fh)
            headers = next(reader)

        assert headers[0] == "gen_uid"
        assert headers[1:] == HOUR_COLUMNS


def test_main_end_to_end_produces_all_files(tmp_path: Path) -> None:
    """Test 17: Full pipeline produces all expected output files."""
    # Set up directory structure
    data_dir = tmp_path / "data"
    ts_dir = data_dir / "timeseries" / "case39"
    ts_dir.mkdir(parents=True)

    # Create synthetic actual profiles that D4 would have produced
    wind_path = ts_dir / "wind_24h.csv"
    with open(wind_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid"] + HOUR_COLUMNS)
        for i in range(3):
            values = [f"{50.0 + j * 2.0:.4f}" for j in range(24)]
            writer.writerow([f"WIND_{i + 1}"] + values)

    solar_path = ts_dir / "solar_24h.csv"
    with open(solar_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid"] + HOUR_COLUMNS)
        for i in range(2):
            values = []
            for h in range(24):
                hour_ending = h + 1
                if hour_ending in SOLAR_NIGHTTIME_HOURS:
                    values.append("0.0000")
                else:
                    values.append(f"{30.0 + h * 1.5:.4f}")
            writer.writerow([f"SOLAR_{i + 1}"] + values)

    # Create renewable_units.csv
    units_path = ts_dir / "renewable_units.csv"
    with open(units_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid", "bus_id", "type", "pmax_mw", "area"])
        for i in range(3):
            writer.writerow([f"WIND_{i + 1}", 25 + i, "wind", 200.0, 1])
        for i in range(2):
            writer.writerow([f"SOLAR_{i + 1}", 18 + i, "solar", 150.0, 2])

    # Run main (with nonexistent RTS-GMLC dir to use synthetic fallback)
    config = ForecastConfig(master_seed=42, num_scenarios=10)
    output = main(
        data_dir=data_dir,
        rts_gmlc_dir=tmp_path / "nonexistent_rts_gmlc",
        config=config,
    )

    # Check output structure
    assert output.script_version == "0.1.0"
    assert output.wind_fit.resource_type == ResourceType.WIND
    assert output.solar_fit.resource_type == ResourceType.SOLAR
    assert len(output.wind_forecasts) == 3
    assert len(output.solar_forecasts) == 2
    assert len(output.wind_actuals) == 3
    assert len(output.solar_actuals) == 2

    # Check files exist
    expected_files = [
        ts_dir / "wind_forecast_24h.csv",
        ts_dir / "wind_actual_24h.csv",
        ts_dir / "solar_forecast_24h.csv",
        ts_dir / "solar_actual_24h.csv",
        ts_dir / "scenarios" / "scenario_multipliers_50x24.csv",
        ts_dir / "scenarios" / "stochastic_metadata.json",
    ]
    for fpath in expected_files:
        assert fpath.exists(), f"Missing output file: {fpath}"

    # Verify metadata JSON is valid
    with open(ts_dir / "scenarios" / "stochastic_metadata.json") as fh:
        metadata = json.load(fh)
    assert "wind_student_t" in metadata
    assert "solar_student_t" in metadata
    assert "correlation" in metadata
    assert "scenario_multipliers" in metadata
    assert metadata["forecast_config"]["master_seed"] == 42
