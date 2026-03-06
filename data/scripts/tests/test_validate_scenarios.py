"""Tests for validate_scenarios.py -- Scenario Validation & Diagnostics.

All tests are self-contained with synthetic data. No external files needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.fit_student_t import ResourceType
from scripts.generate_scenario_multipliers import NetworkId
from scripts.validate_scenarios import (
    CheckStatus,
    NetworkValidationReport,
    ScenarioData,
    ValidationCheckResult,
    ValidationConfig,
    ValidationSummary,
    check_aggregate_feasibility,
    check_correlation_fidelity,
    check_ensemble_unbiasedness,
    check_forecast_rmse,
    check_physical_bounds,
    check_solar_nighttime_zero,
    load_scenario_multipliers,
    write_network_report,
    write_validation_summary,
)

# ---------------------------------------------------------------------------
# Helpers for building synthetic data
# ---------------------------------------------------------------------------


def _make_scenario_data(
    *,
    n_scenarios: int = 10,
    n_gen: int = 3,
    resource_type: ResourceType = ResourceType.WIND,
    pmax: float = 100.0,
    forecast_level: float = 50.0,
    multiplier_mean: float = 1.0,
    multiplier_std: float = 0.05,
    night_hours: list[int] | None = None,
    seed: int = 42,
) -> ScenarioData:
    """Build a synthetic ScenarioData for testing."""
    rng = np.random.Generator(np.random.PCG64(seed))
    if night_hours is None:
        night_hours = []

    generator_ids = [f"gen_{i}" for i in range(n_gen)]
    pmax_values = np.full(n_gen, pmax)

    forecast = np.full((n_gen, 24), forecast_level)
    actual = np.full((n_gen, 24), forecast_level * 0.95)

    # Zero out night hours for solar
    if resource_type == ResourceType.SOLAR:
        for h in night_hours:
            forecast[:, h] = 0.0
            actual[:, h] = 0.0

    multipliers = rng.normal(multiplier_mean, multiplier_std, (n_scenarios, n_gen, 24))
    # Clamp multipliers to keep realizations in [0, pmax]
    multipliers = np.clip(multipliers, 0.0, pmax / np.maximum(forecast_level, 1e-9))

    # Night hours: multipliers = 1.0 for solar
    if resource_type == ResourceType.SOLAR:
        for h in night_hours:
            multipliers[:, :, h] = 1.0

    realizations = forecast[np.newaxis, :, :] * multipliers

    return ScenarioData(
        network_id=NetworkId.TINY,
        resource_type=resource_type,
        generator_ids=generator_ids,
        pmax_values=pmax_values,
        forecast=forecast,
        actual=actual,
        multipliers=multipliers,
        realizations=realizations,
        night_hours=night_hours,
        n_scenarios=n_scenarios,
        n_generators=n_gen,
    )


def _write_multiplier_csv(
    path: Path,
    gen_ids: list[str],
    multipliers: np.ndarray,
) -> None:
    """Write a scenario multipliers CSV for testing load_scenario_multipliers."""
    n_scenarios, n_gen, _ = multipliers.shape
    hr_cols = [f"HR_{k}" for k in range(1, 25)]

    with open(path, "w", newline="") as fh:
        fh.write("gen_uid,scenario," + ",".join(hr_cols) + "\n")
        for g in range(n_gen):
            for s in range(n_scenarios):
                vals = ",".join(f"{v:.6f}" for v in multipliers[s, g, :])
                fh.write(f"{gen_ids[g]},{s + 1},{vals}\n")


# ---------------------------------------------------------------------------
# Test 1: test_load_scenario_multipliers_shape
# ---------------------------------------------------------------------------


def test_load_scenario_multipliers_shape(tmp_path: Path) -> None:
    """Loaded multipliers array has correct (n_scenarios, n_gen, 24) shape."""
    gen_ids = ["gen_0", "gen_1"]
    n_scenarios = 5
    mults = np.ones((n_scenarios, 2, 24))

    csv_path = tmp_path / "scenario_multipliers.csv"
    _write_multiplier_csv(csv_path, gen_ids, mults)

    result = load_scenario_multipliers(csv_path, gen_ids)
    assert result.shape == (n_scenarios, 2, 24)


# ---------------------------------------------------------------------------
# Test 2: test_load_scenario_multipliers_generator_ordering
# ---------------------------------------------------------------------------


def test_load_scenario_multipliers_generator_ordering(tmp_path: Path) -> None:
    """Multiplier values are assigned to the correct generator index."""
    gen_ids = ["alpha", "beta"]
    n_scenarios = 3
    mults = np.zeros((n_scenarios, 2, 24))
    # Set distinct values per generator
    mults[:, 0, :] = 1.0  # alpha
    mults[:, 1, :] = 2.0  # beta

    csv_path = tmp_path / "scenario_multipliers.csv"
    _write_multiplier_csv(csv_path, gen_ids, mults)

    result = load_scenario_multipliers(csv_path, gen_ids)
    np.testing.assert_allclose(result[:, 0, :], 1.0)
    np.testing.assert_allclose(result[:, 1, :], 2.0)


# ---------------------------------------------------------------------------
# Test 3: test_load_scenario_multipliers_mismatched_ids_raises
# ---------------------------------------------------------------------------


def test_load_scenario_multipliers_mismatched_ids_raises(tmp_path: Path) -> None:
    """Raises ValueError when CSV generator IDs do not match expected IDs."""
    csv_gen_ids = ["gen_a", "gen_b"]
    expected_gen_ids = ["gen_b", "gen_a"]  # different ordering
    mults = np.ones((3, 2, 24))

    csv_path = tmp_path / "scenario_multipliers.csv"
    _write_multiplier_csv(csv_path, csv_gen_ids, mults)

    with pytest.raises(ValueError, match="Generator ID mismatch"):
        load_scenario_multipliers(csv_path, expected_gen_ids)


# ---------------------------------------------------------------------------
# Test 4: test_check_physical_bounds_passes
# ---------------------------------------------------------------------------


def test_check_physical_bounds_passes() -> None:
    """Physical bounds check passes when all realizations are in [0, Pmax]."""
    data = _make_scenario_data(pmax=100.0, forecast_level=50.0, multiplier_std=0.01)
    result = check_physical_bounds(data)
    assert result.status == CheckStatus.PASSED


# ---------------------------------------------------------------------------
# Test 5: test_check_physical_bounds_fails_negative
# ---------------------------------------------------------------------------


def test_check_physical_bounds_fails_negative() -> None:
    """Physical bounds check fails when some realizations are negative."""
    data = _make_scenario_data(pmax=100.0, forecast_level=50.0)

    # Inject negative realizations
    bad_realizations = data.realizations.copy()
    bad_realizations[0, 0, 0] = -5.0
    data = ScenarioData(
        network_id=data.network_id,
        resource_type=data.resource_type,
        generator_ids=data.generator_ids,
        pmax_values=data.pmax_values,
        forecast=data.forecast,
        actual=data.actual,
        multipliers=data.multipliers,
        realizations=bad_realizations,
        night_hours=data.night_hours,
        n_scenarios=data.n_scenarios,
        n_generators=data.n_generators,
    )

    result = check_physical_bounds(data)
    assert result.status == CheckStatus.FAILED
    assert "negative" in result.detail.lower() or "min realization" in result.detail.lower()


# ---------------------------------------------------------------------------
# Test 6: test_check_physical_bounds_fails_exceeds_pmax
# ---------------------------------------------------------------------------


def test_check_physical_bounds_fails_exceeds_pmax() -> None:
    """Physical bounds check fails when some realizations exceed Pmax."""
    data = _make_scenario_data(pmax=100.0, forecast_level=50.0)

    bad_realizations = data.realizations.copy()
    bad_realizations[0, 0, 0] = 150.0  # exceeds pmax=100
    data = ScenarioData(
        network_id=data.network_id,
        resource_type=data.resource_type,
        generator_ids=data.generator_ids,
        pmax_values=data.pmax_values,
        forecast=data.forecast,
        actual=data.actual,
        multipliers=data.multipliers,
        realizations=bad_realizations,
        night_hours=data.night_hours,
        n_scenarios=data.n_scenarios,
        n_generators=data.n_generators,
    )

    result = check_physical_bounds(data)
    assert result.status == CheckStatus.FAILED
    assert "excess" in result.detail.lower() or "Pmax" in result.detail


# ---------------------------------------------------------------------------
# Test 7: test_check_correlation_fidelity_passes_identity
# ---------------------------------------------------------------------------


def test_check_correlation_fidelity_passes_identity() -> None:
    """Correlation fidelity passes when target is identity and scenarios are independent."""
    data = _make_scenario_data(n_scenarios=200, n_gen=3, seed=123)
    target_corr = np.eye(3)
    config = ValidationConfig(correlation_frobenius_threshold=1.0)  # loose threshold

    result = check_correlation_fidelity(data, target_corr, config)
    assert result.status == CheckStatus.PASSED


# ---------------------------------------------------------------------------
# Test 8: test_check_correlation_fidelity_skips_single_generator
# ---------------------------------------------------------------------------


def test_check_correlation_fidelity_skips_single_generator() -> None:
    """Correlation fidelity is skipped when only one generator exists."""
    data = _make_scenario_data(n_gen=1)
    target_corr = np.eye(1)
    config = ValidationConfig()

    result = check_correlation_fidelity(data, target_corr, config)
    assert result.status == CheckStatus.SKIPPED


# ---------------------------------------------------------------------------
# Test 9: test_check_ensemble_unbiasedness_passes
# ---------------------------------------------------------------------------


def test_check_ensemble_unbiasedness_passes() -> None:
    """Ensemble unbiasedness passes when multiplier mean is close to 1.0."""
    data = _make_scenario_data(n_scenarios=500, multiplier_mean=1.0, multiplier_std=0.01, seed=99)
    config = ValidationConfig(ensemble_mape_threshold=0.10)

    result = check_ensemble_unbiasedness(data, config)
    assert result.status == CheckStatus.PASSED


# ---------------------------------------------------------------------------
# Test 10: test_check_ensemble_unbiasedness_fails_biased
# ---------------------------------------------------------------------------


def test_check_ensemble_unbiasedness_fails_biased() -> None:
    """Ensemble unbiasedness fails when multiplier mean is far from 1.0."""
    # Multiplier mean of 1.5 means ensemble mean is 50% above forecast
    data = _make_scenario_data(
        n_scenarios=100, multiplier_mean=1.5, multiplier_std=0.01, pmax=200.0
    )
    config = ValidationConfig(ensemble_mape_threshold=0.10)

    result = check_ensemble_unbiasedness(data, config)
    assert result.status == CheckStatus.FAILED


# ---------------------------------------------------------------------------
# Test 11: test_check_solar_nighttime_zero_passes
# ---------------------------------------------------------------------------


def test_check_solar_nighttime_zero_passes() -> None:
    """Solar nighttime zero passes when all solar scenarios are zero at night."""
    data = _make_scenario_data(
        resource_type=ResourceType.SOLAR,
        night_hours=[0, 1, 2, 3, 4, 22, 23],
    )
    result = check_solar_nighttime_zero(data)
    assert result.status == CheckStatus.PASSED


# ---------------------------------------------------------------------------
# Test 12: test_check_solar_nighttime_zero_fails
# ---------------------------------------------------------------------------


def test_check_solar_nighttime_zero_fails() -> None:
    """Solar nighttime zero fails when solar scenarios have non-zero values at night."""
    data = _make_scenario_data(
        resource_type=ResourceType.SOLAR,
        night_hours=[0, 1, 2, 3, 4, 22, 23],
    )

    # Inject non-zero night values
    bad_realizations = data.realizations.copy()
    bad_realizations[0, 0, 0] = 10.0  # hour 0 is night
    data = ScenarioData(
        network_id=data.network_id,
        resource_type=data.resource_type,
        generator_ids=data.generator_ids,
        pmax_values=data.pmax_values,
        forecast=data.forecast,
        actual=data.actual,
        multipliers=data.multipliers,
        realizations=bad_realizations,
        night_hours=data.night_hours,
        n_scenarios=data.n_scenarios,
        n_generators=data.n_generators,
    )

    result = check_solar_nighttime_zero(data)
    assert result.status == CheckStatus.FAILED


# ---------------------------------------------------------------------------
# Test 13: test_check_solar_nighttime_zero_skips_wind
# ---------------------------------------------------------------------------


def test_check_solar_nighttime_zero_skips_wind() -> None:
    """Solar nighttime zero is skipped for wind resources."""
    data = _make_scenario_data(resource_type=ResourceType.WIND)
    result = check_solar_nighttime_zero(data)
    assert result.status == CheckStatus.SKIPPED


# ---------------------------------------------------------------------------
# Test 14: test_check_aggregate_feasibility_passes
# ---------------------------------------------------------------------------


def test_check_aggregate_feasibility_passes() -> None:
    """Aggregate feasibility passes when no scenario exceeds total Pmax."""
    data = _make_scenario_data(n_gen=3, pmax=100.0, forecast_level=50.0, multiplier_std=0.01)
    result = check_aggregate_feasibility(data)
    assert result.status == CheckStatus.PASSED


# ---------------------------------------------------------------------------
# Test 15: test_check_forecast_rmse_passes_wind
# ---------------------------------------------------------------------------


def test_check_forecast_rmse_passes_wind() -> None:
    """Forecast RMSE passes for wind when RMSE is within 10-30% of capacity."""
    rng = np.random.Generator(np.random.PCG64(42))
    n_gen = 3
    pmax = 100.0

    forecast = np.full((n_gen, 24), 50.0)
    # Create actual so that RMSE is ~20% of pmax (=20 MW)
    actual = forecast + rng.normal(0, 20.0, (n_gen, 24))
    actual = np.clip(actual, 0, pmax)

    data = ScenarioData(
        network_id=NetworkId.TINY,
        resource_type=ResourceType.WIND,
        generator_ids=[f"gen_{i}" for i in range(n_gen)],
        pmax_values=np.full(n_gen, pmax),
        forecast=forecast,
        actual=actual,
        multipliers=np.ones((10, n_gen, 24)),
        realizations=np.ones((10, n_gen, 24)) * 50.0,
        night_hours=[],
        n_scenarios=10,
        n_generators=n_gen,
    )

    config = ValidationConfig(wind_rmse_pct_range=(10.0, 30.0))
    result = check_forecast_rmse(data, config)
    assert result.status == CheckStatus.PASSED


# ---------------------------------------------------------------------------
# Test 16: test_check_forecast_rmse_fails_too_low
# ---------------------------------------------------------------------------


def test_check_forecast_rmse_fails_too_low() -> None:
    """Forecast RMSE fails when RMSE is below the expected range."""
    n_gen = 3
    pmax = 100.0

    forecast = np.full((n_gen, 24), 50.0)
    # Actual almost identical to forecast -> RMSE ~ 0% of pmax
    actual = forecast + 0.01

    data = ScenarioData(
        network_id=NetworkId.TINY,
        resource_type=ResourceType.WIND,
        generator_ids=[f"gen_{i}" for i in range(n_gen)],
        pmax_values=np.full(n_gen, pmax),
        forecast=forecast,
        actual=actual,
        multipliers=np.ones((10, n_gen, 24)),
        realizations=np.ones((10, n_gen, 24)) * 50.0,
        night_hours=[],
        n_scenarios=10,
        n_generators=n_gen,
    )

    config = ValidationConfig(wind_rmse_pct_range=(10.0, 30.0))
    result = check_forecast_rmse(data, config)
    assert result.status == CheckStatus.FAILED


# ---------------------------------------------------------------------------
# Test 17: test_write_network_report_roundtrip
# ---------------------------------------------------------------------------


def test_write_network_report_roundtrip(tmp_path: Path) -> None:
    """NetworkValidationReport serializes to JSON and fields are preserved."""
    checks = [
        ValidationCheckResult(
            check_name="physical_bounds",
            display_name="Physical Bounds",
            status=CheckStatus.PASSED,
            measured_value=0.0,
            threshold=0.0,
            detail="All good",
            resource_type=ResourceType.WIND,
        ),
    ]
    report = NetworkValidationReport(
        network_id=NetworkId.TINY,
        checks=checks,
        overall_passed=True,
        n_checks_passed=1,
        n_checks_failed=0,
        n_checks_skipped=0,
        validated_at="2025-01-01T00:00:00+00:00",
        script_version="0.1.0",
    )

    dest = tmp_path / "validation_report.json"
    write_network_report(report, dest)

    assert dest.exists()
    with open(dest) as fh:
        data = json.load(fh)

    assert data["network_id"] == "case39"
    assert data["overall_passed"] is True
    assert data["n_checks_passed"] == 1
    assert data["n_checks_failed"] == 0
    assert len(data["checks"]) == 1
    assert data["checks"][0]["check_name"] == "physical_bounds"
    assert data["checks"][0]["status"] == "passed"


# ---------------------------------------------------------------------------
# Test 18: test_write_validation_summary_overall_pass
# ---------------------------------------------------------------------------


def test_write_validation_summary_overall_pass(tmp_path: Path) -> None:
    """ValidationSummary serializes with overall_passed=True when no failures."""
    report = NetworkValidationReport(
        network_id=NetworkId.TINY,
        checks=[
            ValidationCheckResult(
                check_name="physical_bounds",
                display_name="Physical Bounds",
                status=CheckStatus.PASSED,
                measured_value=0.0,
                threshold=0.0,
                detail="OK",
                resource_type=ResourceType.WIND,
            ),
        ],
        overall_passed=True,
        n_checks_passed=1,
        n_checks_failed=0,
        n_checks_skipped=0,
        validated_at="2025-01-01T00:00:00+00:00",
        script_version="0.1.0",
    )

    summary = ValidationSummary(
        overall_passed=True,
        networks=[report],
        failing_checks=[],
        validated_at="2025-01-01T00:00:00+00:00",
        script_version="0.1.0",
        notes=["Test run"],
    )

    dest = tmp_path / "validation_summary.json"
    write_validation_summary(summary, dest)

    assert dest.exists()
    with open(dest) as fh:
        data = json.load(fh)

    assert data["overall_passed"] is True
    assert len(data["networks"]) == 1
    assert data["failing_checks"] == []
    assert data["notes"] == ["Test run"]
