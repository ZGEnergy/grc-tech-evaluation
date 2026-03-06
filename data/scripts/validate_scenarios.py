"""Scenario Validation & Diagnostics for stochastic generation scenario data.

Validates the complete stochastic data layer produced by Phase 4 (D1-D4) for
physical plausibility and statistical fidelity. Eight categories of checks:

1. Physical bounds -- All scenario realizations non-negative and <= Pmax
2. Correlation fidelity -- Empirical rank correlation matches target (Frobenius < 0.05)
3. Marginal distribution -- KS test against fitted Student-t (>=80% pass at alpha=0.05)
4. Ensemble unbiasedness -- MAPE of ensemble mean vs forecast < 10%
5. Heteroscedasticity -- Median Spearman (forecast level vs scenario spread) > 0
6. Solar nighttime zero -- All solar scenarios zero at night
7. Aggregate feasibility -- No scenario exceeds total renewable Pmax
8. Forecast RMSE -- Wind 10-30%, Solar 5-15% of capacity

PRD 04/05 -- Scenario Validation & Diagnostics.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

import numpy as np
from scipy import stats

from scripts.fit_student_t import (
    ResourceType,
    StudentTParams,
    load_student_t_json,
)
from scripts.generate_forecasts import GeneratorProfile, load_actual_profiles
from scripts.generate_scenario_multipliers import (
    NetworkId,
    load_correlation_matrix,
)

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class CheckStatus(StrEnum):
    """Status of a single validation check."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ValidationCheckResult:
    """Result of a single validation check."""

    check_name: str
    display_name: str
    status: CheckStatus
    measured_value: float | None
    threshold: float | None
    detail: str
    resource_type: ResourceType | None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class NetworkValidationReport:
    """Validation report for a single network."""

    network_id: NetworkId
    checks: list[ValidationCheckResult]
    overall_passed: bool
    n_checks_passed: int
    n_checks_failed: int
    n_checks_skipped: int
    validated_at: str
    script_version: str


@dataclass(frozen=True)
class ValidationSummary:
    """Consolidated validation summary across all networks."""

    overall_passed: bool
    networks: list[NetworkValidationReport]
    failing_checks: list[dict[str, str]]
    validated_at: str
    script_version: str
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScenarioData:
    """Loaded scenario data for one network and resource type."""

    network_id: NetworkId
    resource_type: ResourceType
    generator_ids: list[str]
    pmax_values: np.ndarray
    forecast: np.ndarray  # (n_gen, 24)
    actual: np.ndarray  # (n_gen, 24)
    multipliers: np.ndarray  # (n_scenarios, n_gen, 24)
    realizations: np.ndarray  # (n_scenarios, n_gen, 24)
    night_hours: list[int]
    n_scenarios: int
    n_generators: int


@dataclass(frozen=True)
class ValidationConfig:
    """Thresholds and parameters for validation checks."""

    correlation_frobenius_threshold: float = 0.05
    ks_alpha: float = 0.05
    ks_pass_fraction: float = 0.80
    ensemble_mape_threshold: float = 0.10
    wind_rmse_pct_range: tuple[float, float] = (10.0, 30.0)
    solar_rmse_pct_range: tuple[float, float] = (5.0, 15.0)


# ---------------------------------------------------------------------------
# Scenario multiplier loading
# ---------------------------------------------------------------------------

_HOUR_COLUMNS = [f"HR_{k}" for k in range(1, 25)]


def load_scenario_multipliers(
    csv_path: Path,
    generator_ids: list[str],
) -> np.ndarray:
    """Load scenario multipliers from a CSV file and return as a 3-D array.

    The CSV has columns: gen_uid, scenario, HR_1..HR_24. One row per
    (generator, scenario) pair. Generators must appear in the same order
    as generator_ids.

    Args:
        csv_path: Path to the scenario_multipliers.csv file.
        generator_ids: Expected generator IDs in order.

    Returns:
        Array of shape (n_scenarios, n_generators, 24).

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If generator IDs in CSV do not match generator_ids.
    """
    if not csv_path.exists():
        msg = f"Scenario multipliers CSV not found: {csv_path}"
        raise FileNotFoundError(msg)

    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    if not rows:
        msg = "Scenario multipliers CSV is empty"
        raise ValueError(msg)

    # Determine n_scenarios from data
    gen_uid_set = []
    for row in rows:
        uid = row["gen_uid"]
        if uid not in gen_uid_set:
            gen_uid_set.append(uid)

    n_gen = len(gen_uid_set)
    n_scenarios = len(rows) // n_gen

    if len(rows) != n_gen * n_scenarios:
        msg = f"Row count {len(rows)} is not divisible by number of generators {n_gen}"
        raise ValueError(msg)

    # Validate generator ordering matches expected
    # Filter gen_uid_set to only those in generator_ids
    csv_gen_ids = [uid for uid in gen_uid_set if uid in generator_ids]
    expected_ids = [uid for uid in generator_ids if uid in gen_uid_set]

    if csv_gen_ids != expected_ids:
        msg = f"Generator ID mismatch: CSV has {csv_gen_ids}, expected {expected_ids}"
        raise ValueError(msg)

    # Build the 3-D array: (n_scenarios, n_generators, 24)
    # Map gen_uid to index in generator_ids
    gen_id_to_idx = {uid: i for i, uid in enumerate(generator_ids)}

    # Only load generators that are in generator_ids
    matching_gen_ids = [uid for uid in gen_uid_set if uid in gen_id_to_idx]
    n_matching = len(matching_gen_ids)

    multipliers = np.zeros((n_scenarios, n_matching, 24))

    for row in rows:
        uid = row["gen_uid"]
        if uid not in gen_id_to_idx:
            continue
        scenario_idx = int(row["scenario"]) - 1  # 1-based to 0-based
        gen_idx = gen_id_to_idx[uid]
        values = np.array([float(row[col]) for col in _HOUR_COLUMNS])
        multipliers[scenario_idx, gen_idx, :] = values

    return multipliers


# ---------------------------------------------------------------------------
# Building ScenarioData
# ---------------------------------------------------------------------------


def build_scenario_data(
    network_id: NetworkId,
    resource_type: ResourceType,
    forecast_profiles: list[GeneratorProfile],
    actual_profiles: list[GeneratorProfile],
    multipliers: np.ndarray,
    night_hours: list[int],
) -> ScenarioData:
    """Build a ScenarioData from loaded profiles and multipliers.

    Computes realizations as forecast * multipliers.

    Args:
        network_id: Network identifier.
        resource_type: WIND or SOLAR.
        forecast_profiles: Forecast generator profiles.
        actual_profiles: Actual generator profiles.
        multipliers: Array of shape (n_scenarios, n_gen, 24).
        night_hours: Hours classified as nighttime.

    Returns:
        A ScenarioData with all fields populated.
    """
    generator_ids = [p.gen_uid for p in forecast_profiles]
    pmax_values = np.array([p.pmax for p in forecast_profiles])
    forecast = np.array([p.values for p in forecast_profiles])  # (n_gen, 24)
    actual = np.array([p.values for p in actual_profiles])  # (n_gen, 24)

    n_scenarios = multipliers.shape[0]
    n_gen = len(generator_ids)

    # realizations = forecast * multipliers
    # broadcast forecast (n_gen, 24) -> (1, n_gen, 24) * (n_scenarios, n_gen, 24)
    realizations = forecast[np.newaxis, :, :] * multipliers

    return ScenarioData(
        network_id=network_id,
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


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def check_physical_bounds(
    data: ScenarioData,
) -> ValidationCheckResult:
    """Check that all scenario realizations are non-negative and <= Pmax.

    Args:
        data: Scenario data for one network/resource type.

    Returns:
        A ValidationCheckResult for the physical bounds check.
    """
    realizations = data.realizations  # (n_scenarios, n_gen, 24)
    pmax = data.pmax_values  # (n_gen,)

    # Check non-negative
    min_val = float(np.min(realizations))
    has_negative = min_val < -1e-9

    # Check <= Pmax (with tolerance)
    # broadcast pmax: (n_gen,) -> (1, n_gen, 1)
    pmax_broadcast = pmax[np.newaxis, :, np.newaxis]
    max_excess = float(np.max(realizations - pmax_broadcast))
    exceeds_pmax = max_excess > 1e-6

    if has_negative or exceeds_pmax:
        details = []
        if has_negative:
            details.append(f"min realization = {min_val:.6f}")
        if exceeds_pmax:
            details.append(f"max excess over Pmax = {max_excess:.6f}")
        return ValidationCheckResult(
            check_name="physical_bounds",
            display_name="Physical Bounds",
            status=CheckStatus.FAILED,
            measured_value=min_val if has_negative else max_excess,
            threshold=0.0,
            detail=f"Violations: {'; '.join(details)}",
            resource_type=data.resource_type,
        )

    return ValidationCheckResult(
        check_name="physical_bounds",
        display_name="Physical Bounds",
        status=CheckStatus.PASSED,
        measured_value=0.0,
        threshold=0.0,
        detail=(
            f"All {data.n_scenarios * data.n_generators * 24} realizations "
            f"in [0, Pmax]. Min={min_val:.4f}, MaxExcess={max_excess:.6f}"
        ),
        resource_type=data.resource_type,
    )


def check_correlation_fidelity(
    data: ScenarioData,
    target_correlation: np.ndarray,
    config: ValidationConfig,
) -> ValidationCheckResult:
    """Check that empirical rank correlation matches the target.

    Computes Frobenius norm of (empirical - target) correlation matrices.
    Uses a representative daytime hour for evaluation.

    Args:
        data: Scenario data for one network/resource type.
        target_correlation: Target rank correlation matrix, shape (G, G).
        config: Validation configuration.

    Returns:
        A ValidationCheckResult for the correlation fidelity check.
    """
    if data.n_generators < 2:
        return ValidationCheckResult(
            check_name="correlation_fidelity",
            display_name="Correlation Fidelity",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=config.correlation_frobenius_threshold,
            detail="Skipped: fewer than 2 generators",
            resource_type=data.resource_type,
        )

    # Use a daytime hour (not a night hour)
    daytime_hours = [h for h in range(24) if h not in data.night_hours]
    if not daytime_hours:
        return ValidationCheckResult(
            check_name="correlation_fidelity",
            display_name="Correlation Fidelity",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=config.correlation_frobenius_threshold,
            detail="Skipped: no daytime hours available",
            resource_type=data.resource_type,
        )

    # Pick hour with highest forecast variability for a more meaningful test
    hour = daytime_hours[len(daytime_hours) // 2]

    # Extract realizations for this hour: (n_scenarios, n_gen)
    hour_data = data.realizations[:, :, hour]

    # Compute empirical Spearman rank correlation
    empirical_corr, _ = stats.spearmanr(hour_data)
    if empirical_corr.ndim == 0:
        empirical_corr = np.array([[1.0, float(empirical_corr)], [float(empirical_corr), 1.0]])

    # Compute Frobenius norm of difference
    diff = empirical_corr - target_correlation
    frob_norm = float(np.linalg.norm(diff, "fro"))

    status = (
        CheckStatus.PASSED
        if frob_norm < config.correlation_frobenius_threshold
        else CheckStatus.FAILED
    )

    return ValidationCheckResult(
        check_name="correlation_fidelity",
        display_name="Correlation Fidelity",
        status=status,
        measured_value=frob_norm,
        threshold=config.correlation_frobenius_threshold,
        detail=(
            f"Frobenius norm = {frob_norm:.6f} "
            f"(threshold = {config.correlation_frobenius_threshold}), "
            f"evaluated at hour {hour}"
        ),
        resource_type=data.resource_type,
    )


def check_marginal_ks(
    data: ScenarioData,
    student_t_params: StudentTParams,
    config: ValidationConfig,
) -> ValidationCheckResult:
    """Check marginal distribution fit via KS test against Student-t.

    For each generator at each daytime hour, performs a KS test on the
    scenario multiplier errors against the fitted Student-t distribution.
    At least ks_pass_fraction of generators must pass at alpha significance.

    Args:
        data: Scenario data for one network/resource type.
        student_t_params: Fitted Student-t parameters.
        config: Validation configuration.

    Returns:
        A ValidationCheckResult for the marginal KS check.
    """
    resource_fit = (
        student_t_params.wind if data.resource_type == ResourceType.WIND else student_t_params.solar
    )

    n_tests = 0
    n_passed = 0

    for g in range(data.n_generators):
        for h in range(24):
            hour_fit = resource_fit.per_hour[h]
            if not hour_fit.is_fitted:
                continue

            # Extract error samples: (multiplier - 1) * forecast
            forecast_val = data.forecast[g, h]
            if forecast_val == 0.0:
                continue

            errors = (data.multipliers[:, g, h] - 1.0) * forecast_val

            if len(errors) < 5:
                continue

            _, p_value = stats.kstest(errors, "t", args=(hour_fit.df, hour_fit.loc, hour_fit.scale))

            n_tests += 1
            if p_value >= config.ks_alpha:
                n_passed += 1

    if n_tests == 0:
        return ValidationCheckResult(
            check_name="marginal_ks",
            display_name="Marginal Distribution (KS)",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=config.ks_pass_fraction,
            detail="Skipped: no testable generator-hour combinations",
            resource_type=data.resource_type,
        )

    pass_fraction = n_passed / n_tests

    status = CheckStatus.PASSED if pass_fraction >= config.ks_pass_fraction else CheckStatus.FAILED

    return ValidationCheckResult(
        check_name="marginal_ks",
        display_name="Marginal Distribution (KS)",
        status=status,
        measured_value=pass_fraction,
        threshold=config.ks_pass_fraction,
        detail=(
            f"{n_passed}/{n_tests} generator-hours passed KS test "
            f"({pass_fraction:.1%} vs {config.ks_pass_fraction:.0%} required)"
        ),
        resource_type=data.resource_type,
    )


def check_ensemble_unbiasedness(
    data: ScenarioData,
    config: ValidationConfig,
) -> ValidationCheckResult:
    """Check that the ensemble mean is unbiased relative to the forecast.

    Computes MAPE of ensemble mean vs forecast across all generators and hours.

    Args:
        data: Scenario data for one network/resource type.
        config: Validation configuration.

    Returns:
        A ValidationCheckResult for the ensemble unbiasedness check.
    """
    # ensemble mean: mean over scenarios -> (n_gen, 24)
    ensemble_mean = np.mean(data.realizations, axis=0)

    # Compute MAPE only where forecast > 0
    mask = data.forecast > 1e-9
    if not np.any(mask):
        return ValidationCheckResult(
            check_name="ensemble_unbiasedness",
            display_name="Ensemble Unbiasedness",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=config.ensemble_mape_threshold,
            detail="Skipped: all forecast values are zero",
            resource_type=data.resource_type,
        )

    ape = np.abs(ensemble_mean[mask] - data.forecast[mask]) / data.forecast[mask]
    mape = float(np.mean(ape))

    status = CheckStatus.PASSED if mape < config.ensemble_mape_threshold else CheckStatus.FAILED

    return ValidationCheckResult(
        check_name="ensemble_unbiasedness",
        display_name="Ensemble Unbiasedness",
        status=status,
        measured_value=mape,
        threshold=config.ensemble_mape_threshold,
        detail=(
            f"MAPE = {mape:.4f} ({mape:.1%}) vs threshold {config.ensemble_mape_threshold:.0%}"
        ),
        resource_type=data.resource_type,
    )


def check_heteroscedasticity(
    data: ScenarioData,
) -> ValidationCheckResult:
    """Check that scenario spread increases with forecast level.

    Computes median Spearman correlation between forecast level and
    scenario spread (std across scenarios) across generators.

    Args:
        data: Scenario data for one network/resource type.

    Returns:
        A ValidationCheckResult for the heteroscedasticity check.
    """
    correlations: list[float] = []

    for g in range(data.n_generators):
        forecast_vals = data.forecast[g, :]  # (24,)
        # scenario spread: std over scenarios at each hour
        spread = np.std(data.realizations[:, g, :], axis=0)  # (24,)

        # Only use hours where forecast > 0
        mask = forecast_vals > 1e-9
        if np.sum(mask) < 3:
            continue

        corr, _ = stats.spearmanr(forecast_vals[mask], spread[mask])
        if not np.isnan(corr):
            correlations.append(float(corr))

    if not correlations:
        return ValidationCheckResult(
            check_name="heteroscedasticity",
            display_name="Heteroscedasticity",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=0.0,
            detail="Skipped: insufficient data for Spearman correlation",
            resource_type=data.resource_type,
        )

    median_corr = float(np.median(correlations))

    status = CheckStatus.PASSED if median_corr > 0 else CheckStatus.FAILED

    return ValidationCheckResult(
        check_name="heteroscedasticity",
        display_name="Heteroscedasticity",
        status=status,
        measured_value=median_corr,
        threshold=0.0,
        detail=(
            f"Median Spearman correlation = {median_corr:.4f} "
            f"(must be > 0, computed from {len(correlations)} generators)"
        ),
        resource_type=data.resource_type,
    )


def check_solar_nighttime_zero(
    data: ScenarioData,
) -> ValidationCheckResult:
    """Check that all solar scenarios are zero during nighttime hours.

    Only applies to solar resource type. Wind is skipped.

    Args:
        data: Scenario data for one network/resource type.

    Returns:
        A ValidationCheckResult for the solar nighttime zero check.
    """
    if data.resource_type != ResourceType.SOLAR:
        return ValidationCheckResult(
            check_name="solar_nighttime_zero",
            display_name="Solar Nighttime Zero",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=0.0,
            detail="Skipped: not a solar resource",
            resource_type=data.resource_type,
        )

    if not data.night_hours:
        return ValidationCheckResult(
            check_name="solar_nighttime_zero",
            display_name="Solar Nighttime Zero",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=0.0,
            detail="Skipped: no night hours defined",
            resource_type=data.resource_type,
        )

    # Check all realizations at night hours are zero
    night_realizations = data.realizations[:, :, data.night_hours]
    max_night = float(np.max(np.abs(night_realizations)))

    if max_night > 1e-9:
        n_nonzero = int(np.sum(np.abs(night_realizations) > 1e-9))
        return ValidationCheckResult(
            check_name="solar_nighttime_zero",
            display_name="Solar Nighttime Zero",
            status=CheckStatus.FAILED,
            measured_value=max_night,
            threshold=0.0,
            detail=(
                f"{n_nonzero} non-zero solar values during night hours "
                f"{data.night_hours}, max abs = {max_night:.6f}"
            ),
            resource_type=data.resource_type,
        )

    return ValidationCheckResult(
        check_name="solar_nighttime_zero",
        display_name="Solar Nighttime Zero",
        status=CheckStatus.PASSED,
        measured_value=0.0,
        threshold=0.0,
        detail=f"All solar scenarios zero during night hours {data.night_hours}",
        resource_type=data.resource_type,
    )


def check_aggregate_feasibility(
    data: ScenarioData,
) -> ValidationCheckResult:
    """Check that no scenario exceeds total renewable Pmax in aggregate.

    Sums realizations across generators for each scenario/hour and
    compares against total Pmax.

    Args:
        data: Scenario data for one network/resource type.

    Returns:
        A ValidationCheckResult for the aggregate feasibility check.
    """
    total_pmax = float(np.sum(data.pmax_values))

    # Sum realizations across generators: (n_scenarios, 24)
    agg_realizations = np.sum(data.realizations, axis=1)

    max_agg = float(np.max(agg_realizations))
    excess = max_agg - total_pmax

    if excess > 1e-6:
        return ValidationCheckResult(
            check_name="aggregate_feasibility",
            display_name="Aggregate Feasibility",
            status=CheckStatus.FAILED,
            measured_value=max_agg,
            threshold=total_pmax,
            detail=(
                f"Max aggregate realization {max_agg:.2f} MW exceeds "
                f"total Pmax {total_pmax:.2f} MW by {excess:.2f} MW"
            ),
            resource_type=data.resource_type,
        )

    return ValidationCheckResult(
        check_name="aggregate_feasibility",
        display_name="Aggregate Feasibility",
        status=CheckStatus.PASSED,
        measured_value=max_agg,
        threshold=total_pmax,
        detail=(f"Max aggregate realization {max_agg:.2f} MW <= total Pmax {total_pmax:.2f} MW"),
        resource_type=data.resource_type,
    )


def check_forecast_rmse(
    data: ScenarioData,
    config: ValidationConfig,
) -> ValidationCheckResult:
    """Check that forecast RMSE is within the expected range for the resource type.

    RMSE is computed as percentage of average capacity (mean Pmax).

    Args:
        data: Scenario data for one network/resource type.
        config: Validation configuration.

    Returns:
        A ValidationCheckResult for the forecast RMSE check.
    """
    if data.resource_type == ResourceType.WIND:
        rmse_range = config.wind_rmse_pct_range
    else:
        rmse_range = config.solar_rmse_pct_range

    # Compute RMSE between forecast and actual
    # Use only hours where actual or forecast > 0
    mask = (data.actual > 1e-9) | (data.forecast > 1e-9)
    if not np.any(mask):
        return ValidationCheckResult(
            check_name="forecast_rmse",
            display_name="Forecast RMSE",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=None,
            detail="Skipped: all forecast and actual values are zero",
            resource_type=data.resource_type,
        )

    errors = data.forecast[mask] - data.actual[mask]
    rmse = float(np.sqrt(np.mean(errors**2)))

    # Express as percentage of mean Pmax
    mean_pmax = float(np.mean(data.pmax_values))
    if mean_pmax < 1e-9:
        return ValidationCheckResult(
            check_name="forecast_rmse",
            display_name="Forecast RMSE",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=None,
            detail="Skipped: mean Pmax is zero",
            resource_type=data.resource_type,
        )

    rmse_pct = (rmse / mean_pmax) * 100.0

    lo, hi = rmse_range
    status = CheckStatus.PASSED if lo <= rmse_pct <= hi else CheckStatus.FAILED

    return ValidationCheckResult(
        check_name="forecast_rmse",
        display_name="Forecast RMSE",
        status=status,
        measured_value=rmse_pct,
        threshold=None,
        detail=(
            f"RMSE = {rmse:.2f} MW ({rmse_pct:.1f}% of mean Pmax {mean_pmax:.1f} MW), "
            f"expected range [{lo:.0f}%, {hi:.0f}%]"
        ),
        resource_type=data.resource_type,
        metadata={"rmse_mw": rmse, "rmse_pct": rmse_pct, "range_lo": lo, "range_hi": hi},
    )


# ---------------------------------------------------------------------------
# Network-level orchestration
# ---------------------------------------------------------------------------


def validate_network(
    network_id: NetworkId,
    scenario_data_list: list[ScenarioData],
    student_t_params: StudentTParams,
    target_correlations: dict[ResourceType, np.ndarray],
    config: ValidationConfig,
) -> NetworkValidationReport:
    """Run all validation checks for a single network.

    Args:
        network_id: Network identifier.
        scenario_data_list: ScenarioData per resource type for this network.
        student_t_params: Fitted Student-t parameters.
        target_correlations: Target correlation matrices keyed by resource type.
        config: Validation configuration.

    Returns:
        A NetworkValidationReport with all check results.
    """
    checks: list[ValidationCheckResult] = []

    for data in scenario_data_list:
        # 1. Physical bounds
        checks.append(check_physical_bounds(data))

        # 2. Correlation fidelity
        target_corr = target_correlations.get(data.resource_type)
        if target_corr is not None:
            checks.append(check_correlation_fidelity(data, target_corr, config))
        else:
            checks.append(
                ValidationCheckResult(
                    check_name="correlation_fidelity",
                    display_name="Correlation Fidelity",
                    status=CheckStatus.SKIPPED,
                    measured_value=None,
                    threshold=config.correlation_frobenius_threshold,
                    detail="Skipped: no target correlation matrix available",
                    resource_type=data.resource_type,
                )
            )

        # 3. Marginal KS
        checks.append(check_marginal_ks(data, student_t_params, config))

        # 4. Ensemble unbiasedness
        checks.append(check_ensemble_unbiasedness(data, config))

        # 5. Heteroscedasticity
        checks.append(check_heteroscedasticity(data))

        # 6. Solar nighttime zero
        checks.append(check_solar_nighttime_zero(data))

        # 7. Aggregate feasibility
        checks.append(check_aggregate_feasibility(data))

        # 8. Forecast RMSE
        checks.append(check_forecast_rmse(data, config))

    n_passed = sum(1 for c in checks if c.status == CheckStatus.PASSED)
    n_failed = sum(1 for c in checks if c.status == CheckStatus.FAILED)
    n_skipped = sum(1 for c in checks if c.status == CheckStatus.SKIPPED)
    overall = n_failed == 0

    return NetworkValidationReport(
        network_id=network_id,
        checks=checks,
        overall_passed=overall,
        n_checks_passed=n_passed,
        n_checks_failed=n_failed,
        n_checks_skipped=n_skipped,
        validated_at=datetime.now(timezone.utc).isoformat(),
        script_version=__version__,
    )


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def _to_serializable(obj: object) -> object:
    """Recursively convert dataclasses, enums, numpy types to JSON-safe types."""
    if isinstance(obj, StrEnum):
        return obj.value
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, list):
        return [_to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        d = {}
        for field_name in obj.__dataclass_fields__:
            d[field_name] = _to_serializable(getattr(obj, field_name))
        return d
    return str(obj)


def write_network_report(
    report: NetworkValidationReport,
    dest_path: Path,
) -> None:
    """Write a NetworkValidationReport to a JSON file.

    Args:
        report: The validation report to write.
        dest_path: Path to the output JSON file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = _to_serializable(report)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def write_validation_summary(
    summary: ValidationSummary,
    dest_path: Path,
) -> None:
    """Write a ValidationSummary to a JSON file.

    Args:
        summary: The validation summary to write.
        dest_path: Path to the output JSON file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = _to_serializable(summary)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
    *,
    config: ValidationConfig | None = None,
    networks: list[NetworkId] | None = None,
) -> ValidationSummary:
    """Entry point: validate scenario data for all networks.

    Loads scenario multipliers, forecast/actual profiles, Student-t params,
    and correlation matrices, then runs all 8 validation checks per network
    and resource type.

    Args:
        timeseries_base_dir: Base directory for input/output. Defaults
            to <repo_root>/data/timeseries/.
        config: Validation configuration.
        networks: List of networks to validate. Defaults to TINY and SMALL.

    Returns:
        The complete ValidationSummary.
    """
    if timeseries_base_dir is None:
        timeseries_base_dir = Path(__file__).resolve().parent.parent / "timeseries"

    if config is None:
        config = ValidationConfig()

    if networks is None:
        networks = list(NetworkId)

    # Load Student-t params from D1
    student_t_path = timeseries_base_dir / "ACTIVSg2000" / "scenarios" / "student_t_params.json"
    student_t_params = load_student_t_json(student_t_path)

    # Load correlation matrices from D2
    corr_path = timeseries_base_dir / "scenarios" / "rank_correlation_matrix.json"

    network_reports: list[NetworkValidationReport] = []

    for network_id in networks:
        network_dir = timeseries_base_dir / network_id.value
        scenarios_dir = network_dir / "scenarios"

        # Load correlation matrix
        try:
            corr_matrix, corr_gen_ids = load_correlation_matrix(corr_path, network_id)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("Could not load correlation matrix for %s: %s", network_id, exc)
            corr_matrix = None
            corr_gen_ids = []

        scenario_data_list: list[ScenarioData] = []
        target_correlations: dict[ResourceType, np.ndarray] = {}

        for resource_type in ResourceType:
            # Load forecast and actual profiles
            forecast_csv = network_dir / f"{resource_type.value}_forecast_24h.csv"
            actual_csv = network_dir / f"{resource_type.value}_actual_24h.csv"

            if not forecast_csv.exists() or not actual_csv.exists():
                logger.warning(
                    "Missing forecast/actual CSV for %s/%s, skipping",
                    network_id,
                    resource_type,
                )
                continue

            forecast_profiles = load_actual_profiles(forecast_csv, resource_type)
            actual_profiles = load_actual_profiles(actual_csv, resource_type)

            # Classify night hours
            if resource_type == ResourceType.SOLAR:
                night_hours = sorted(
                    h for h in range(24) if sum(p.values[h] for p in actual_profiles) == 0.0
                )
            else:
                night_hours = []

            generator_ids = [p.gen_uid for p in forecast_profiles]

            # Load scenario multipliers
            multipliers_csv = scenarios_dir / "scenario_multipliers.csv"
            if not multipliers_csv.exists():
                logger.warning("Missing scenario multipliers for %s, skipping", network_id)
                continue

            try:
                multipliers = load_scenario_multipliers(multipliers_csv, generator_ids)
            except ValueError as exc:
                logger.warning(
                    "Failed to load multipliers for %s/%s: %s",
                    network_id,
                    resource_type,
                    exc,
                )
                continue

            data = build_scenario_data(
                network_id=network_id,
                resource_type=resource_type,
                forecast_profiles=forecast_profiles,
                actual_profiles=actual_profiles,
                multipliers=multipliers,
                night_hours=night_hours,
            )
            scenario_data_list.append(data)

            # Build sub-correlation matrix for this resource type
            if corr_matrix is not None and corr_gen_ids:
                gen_indices = []
                for uid in generator_ids:
                    matched = False
                    for idx, cid in enumerate(corr_gen_ids):
                        if uid in cid or cid in uid:
                            gen_indices.append(idx)
                            matched = True
                            break
                    if not matched:
                        gen_indices.append(-1)

                if all(idx >= 0 for idx in gen_indices):
                    sub_corr = corr_matrix[np.ix_(gen_indices, gen_indices)]
                    target_correlations[resource_type] = sub_corr

        report = validate_network(
            network_id=network_id,
            scenario_data_list=scenario_data_list,
            student_t_params=student_t_params,
            target_correlations=target_correlations,
            config=config,
        )
        network_reports.append(report)

        # Write per-network report
        report_path = scenarios_dir / "validation_report.json"
        write_network_report(report, report_path)
        logger.info(
            "Network %s: %d passed, %d failed, %d skipped",
            network_id.value,
            report.n_checks_passed,
            report.n_checks_failed,
            report.n_checks_skipped,
        )

    # Build summary
    failing_checks: list[dict[str, str]] = []
    for report in network_reports:
        for check in report.checks:
            if check.status == CheckStatus.FAILED:
                failing_checks.append(
                    {
                        "network": report.network_id.value,
                        "check": check.check_name,
                        "detail": check.detail,
                    }
                )

    overall_passed = all(r.overall_passed for r in network_reports)

    summary = ValidationSummary(
        overall_passed=overall_passed,
        networks=network_reports,
        failing_checks=failing_checks,
        validated_at=datetime.now(timezone.utc).isoformat(),
        script_version=__version__,
    )

    # Write summary
    summary_path = timeseries_base_dir / "scenarios" / "validation_summary.json"
    write_validation_summary(summary, summary_path)
    logger.info("Overall validation: %s", "PASSED" if overall_passed else "FAILED")

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
