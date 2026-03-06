"""Stochastic Scenario Generation for the case39 (TINY) network.

Produces stochastic scenario data for rubric test A-8 (stochastic optimization):
forecast/actual profile pairs for wind and solar, fitted Student-t forecast error
parameters from RTS-GMLC data, and 50 correlated scenario multipliers via the
Iman-Conover method.

Consolidates Phase 4 deliverables (Student-t fitting, forecast generation,
correlated scenario multipliers) into a single TINY-scoped script. TINY has
5 renewable generators (3 wind, 2 solar from PRD-04).

This module is self-contained -- it does NOT import from Phase 4 scripts
(fit_student_t.py, generate_forecasts.py, generate_scenario_multipliers.py).
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

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOURS_PER_YEAR = 8760
SOLAR_NIGHTTIME_HOURS: set[int] = {1, 2, 3, 4, 5, 6, 21, 22, 23, 24}
HOUR_COLUMNS: list[str] = [f"HR_{h}" for h in range(1, 25)]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ResourceType(StrEnum):
    WIND = "wind"
    SOLAR = "solar"


@dataclass(frozen=True)
class StudentTFit:
    resource_type: ResourceType
    df: float
    loc: float
    scale: float
    sample_size: int
    num_generators_pooled: int


@dataclass(frozen=True)
class ForecastConfig:
    smoothing_window: int = 3
    wind_bias_fraction: float = 0.02
    solar_bias_fraction: float = -0.01
    master_seed: int = 42
    num_scenarios: int = 50


@dataclass(frozen=True)
class GeneratorMapping:
    tiny_gen_uid: str
    tiny_bus_id: int
    resource_type: ResourceType
    rts_gmlc_gen_id: str
    ordinal: int


@dataclass(frozen=True)
class CorrelationResult:
    matrix: list[list[float]]
    generator_order: list[str]
    is_psd: bool
    psd_projected: bool


@dataclass(frozen=True)
class GeneratorProfile:
    gen_uid: str
    bus_id: int
    pmax_mw: float
    hourly_mw: np.ndarray  # shape (24,)


@dataclass(frozen=True)
class ScenarioMultiplierSet:
    multipliers: np.ndarray  # shape (50, 5, 24)
    generator_order: list[str]
    num_scenarios: int
    seed_used: int


@dataclass(frozen=True)
class StochasticScenarioOutput:
    wind_fit: StudentTFit
    solar_fit: StudentTFit
    correlation: CorrelationResult
    forecast_config: ForecastConfig
    wind_forecasts: list[GeneratorProfile]
    wind_actuals: list[GeneratorProfile]
    solar_forecasts: list[GeneratorProfile]
    solar_actuals: list[GeneratorProfile]
    scenario_multipliers: ScenarioMultiplierSet
    output_dir: str
    script_version: str
    generated_at: str
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# RTS-GMLC profile loading (full-year, 8760 hours)
# ---------------------------------------------------------------------------


def load_rts_gmlc_full_year_profiles(
    rts_gmlc_dir: Path,
    resource_type: ResourceType,
) -> tuple[np.ndarray, list[str]]:
    """Load full-year RTS-GMLC profiles for a resource type.

    Expects CSV files with columns: generator_id, then 8760 hourly values,
    OR a directory containing per-generator CSVs.

    Falls back to synthetic 8760-hour profiles if real data is unavailable.

    Args:
        rts_gmlc_dir: Path to the RTS-GMLC data directory.
        resource_type: WIND or SOLAR.

    Returns:
        Tuple of (profiles_array, generator_ids) where profiles_array
        has shape (8760, N_gens) and generator_ids is a list of N_gens
        generator ID strings.
    """
    # Try to find actual RTS-GMLC files
    csv_path = rts_gmlc_dir / f"{resource_type.value}_generation_8760.csv"
    if csv_path.exists():
        return _load_8760_csv(csv_path)

    # Fallback: generate synthetic profiles based on typical RTS-GMLC shapes
    logger.warning(
        "RTS-GMLC %s data not found at %s, using synthetic profiles",
        resource_type.value,
        csv_path,
    )
    return _generate_synthetic_8760(resource_type)


def _load_8760_csv(csv_path: Path) -> tuple[np.ndarray, list[str]]:
    """Load an 8760-hour profile CSV with gen_id rows and hourly columns."""
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        next(reader)  # skip header row
        gen_ids: list[str] = []
        profiles: list[list[float]] = []
        for row in reader:
            gen_ids.append(row[0])
            profiles.append([float(v) for v in row[1:]])

    arr = np.array(profiles).T  # (8760, N_gens)
    if arr.shape[0] != HOURS_PER_YEAR:
        msg = f"Expected {HOURS_PER_YEAR} hours, got {arr.shape[0]}"
        raise ValueError(msg)
    return arr, gen_ids


def _generate_synthetic_8760(
    resource_type: ResourceType,
) -> tuple[np.ndarray, list[str]]:
    """Generate synthetic 8760 profiles mimicking RTS-GMLC patterns.

    Creates profiles with realistic diurnal patterns and day-to-day variability.
    """
    rng = np.random.Generator(np.random.PCG64(12345))
    n_days = 365
    n_hours = n_days * 24

    if resource_type == ResourceType.WIND:
        gen_ids = ["WIND_RTS_1", "WIND_RTS_2", "WIND_RTS_3", "WIND_RTS_4"]
        n_gens = len(gen_ids)
        profiles = np.zeros((n_hours, n_gens))

        # Base diurnal wind pattern (CF)
        base_cf = np.array(
            [
                0.42,
                0.45,
                0.48,
                0.50,
                0.47,
                0.43,
                0.38,
                0.32,
                0.28,
                0.25,
                0.22,
                0.20,
                0.18,
                0.20,
                0.23,
                0.27,
                0.32,
                0.38,
                0.44,
                0.50,
                0.55,
                0.58,
                0.52,
                0.46,
            ]
        )
        pmax = 150.0  # MW per generator

        for d in range(n_days):
            daily_scale = 0.7 + 0.6 * rng.random()
            for g in range(n_gens):
                gen_scale = 0.8 + 0.4 * rng.random()
                noise = rng.normal(0, 0.03, 24)
                cf = np.clip(base_cf * daily_scale * gen_scale + noise, 0, 1)
                profiles[d * 24 : (d + 1) * 24, g] = cf * pmax

    else:  # SOLAR
        gen_ids = ["SOLAR_RTS_1", "SOLAR_RTS_2", "SOLAR_RTS_3"]
        n_gens = len(gen_ids)
        profiles = np.zeros((n_hours, n_gens))

        base_cf = np.array(
            [
                0.00,
                0.00,
                0.00,
                0.00,
                0.00,
                0.00,
                0.05,
                0.18,
                0.42,
                0.62,
                0.78,
                0.85,
                0.88,
                0.82,
                0.70,
                0.52,
                0.30,
                0.10,
                0.00,
                0.00,
                0.00,
                0.00,
                0.00,
                0.00,
            ]
        )
        pmax = 100.0

        for d in range(n_days):
            daily_scale = 0.6 + 0.8 * rng.random()
            for g in range(n_gens):
                gen_scale = 0.85 + 0.3 * rng.random()
                noise = rng.normal(0, 0.02, 24)
                cf = np.clip(base_cf * daily_scale * gen_scale + noise, 0, 1)
                # Force nighttime zeros
                for h in range(24):
                    if (h + 1) in SOLAR_NIGHTTIME_HOURS:
                        cf[h] = 0.0
                profiles[d * 24 : (d + 1) * 24, g] = cf * pmax

    return profiles, gen_ids


# ---------------------------------------------------------------------------
# Capacity factor change computation
# ---------------------------------------------------------------------------


def compute_capacity_factor_changes(
    profiles: np.ndarray,
    pmax_values: np.ndarray | None = None,
) -> np.ndarray:
    """Compute hour-over-hour capacity factor changes.

    If pmax_values is provided, normalizes profiles to capacity factors first.
    Otherwise treats profile values as already being capacity factors.

    Args:
        profiles: Array of shape (8760, N_gens), hourly values.
        pmax_values: Optional array of shape (N_gens,), Pmax per generator.

    Returns:
        Array of shape (8759, N_gens), hour-over-hour CF changes.

    Raises:
        ValueError: If profiles does not have 8760 rows.
    """
    if profiles.ndim == 1:
        profiles = profiles.reshape(-1, 1)
    if profiles.shape[0] != HOURS_PER_YEAR:
        msg = f"profiles must have {HOURS_PER_YEAR} rows, got {profiles.shape[0]}"
        raise ValueError(msg)

    if pmax_values is not None:
        # Normalize to CF. Avoid division by zero.
        pmax_safe = np.where(pmax_values > 0, pmax_values, 1.0)
        cf = profiles / pmax_safe[np.newaxis, :]
    else:
        cf = profiles

    return np.diff(cf, axis=0)


# ---------------------------------------------------------------------------
# Student-t fitting (pooled across generators)
# ---------------------------------------------------------------------------


def fit_student_t_pooled(
    cf_changes: np.ndarray,
    resource_type: ResourceType,
) -> StudentTFit:
    """Fit a pooled Student-t distribution to capacity factor changes.

    Pools all hour-over-hour CF changes across generators and hours.
    For solar, excludes nighttime hours (where CF is always zero).

    Args:
        cf_changes: Array of shape (8759, N_gens), CF changes.
        resource_type: WIND or SOLAR.

    Returns:
        StudentTFit with fitted parameters.
    """
    if cf_changes.ndim == 1:
        cf_changes = cf_changes.reshape(-1, 1)

    n_changes, n_gens = cf_changes.shape

    if resource_type == ResourceType.SOLAR:
        # Exclude nighttime hours: changes INTO nighttime hours
        # Hour assignment for change index i: hour_ending = ((i + 1) % 24) + 1
        # We exclude changes where the target hour-ending is in SOLAR_NIGHTTIME_HOURS
        mask = np.ones(n_changes, dtype=bool)
        for i in range(n_changes):
            hour_ending = ((i + 1) % 24) + 1
            if hour_ending in SOLAR_NIGHTTIME_HOURS:
                mask[i] = False
        pooled = cf_changes[mask].ravel()
    else:
        pooled = cf_changes.ravel()

    # Remove zeros and near-zeros for cleaner fitting
    pooled = pooled[np.abs(pooled) > 1e-10]

    df, loc, scale = stats.t.fit(pooled)

    return StudentTFit(
        resource_type=resource_type,
        df=float(df),
        loc=float(loc),
        scale=float(scale),
        sample_size=len(pooled),
        num_generators_pooled=n_gens,
    )


# ---------------------------------------------------------------------------
# Generator mapping (TINY to RTS-GMLC by ordinal position)
# ---------------------------------------------------------------------------


def map_tiny_to_rts_gmlc_generators(
    tiny_units_path: Path,
    rts_gmlc_wind_ids: list[str],
    rts_gmlc_solar_ids: list[str],
) -> list[GeneratorMapping]:
    """Map TINY generators to RTS-GMLC counterparts by ordinal position.

    Reads renewable_units.csv for TINY generator info. Maps each TINY
    generator to an RTS-GMLC generator of the same resource type by
    ordinal position (first wind -> first RTS wind, etc.).

    Args:
        tiny_units_path: Path to renewable_units.csv for case39.
        rts_gmlc_wind_ids: RTS-GMLC wind generator IDs.
        rts_gmlc_solar_ids: RTS-GMLC solar generator IDs.

    Returns:
        List of GeneratorMapping, one per TINY generator.
    """
    # Read TINY renewable units
    wind_units: list[tuple[str, int]] = []
    solar_units: list[tuple[str, int]] = []

    if tiny_units_path.exists():
        with open(tiny_units_path, newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                gen_uid = row["gen_uid"]
                bus_id = int(row["bus_id"])
                rtype = row["type"]
                if rtype == "wind":
                    wind_units.append((gen_uid, bus_id))
                elif rtype == "solar":
                    solar_units.append((gen_uid, bus_id))
    else:
        # Default TINY generators from D4
        wind_units = [("WIND_1", 25), ("WIND_2", 2), ("WIND_3", 22)]
        solar_units = [("SOLAR_1", 18), ("SOLAR_2", 15)]

    mappings: list[GeneratorMapping] = []

    for i, (uid, bus) in enumerate(wind_units):
        rts_id = rts_gmlc_wind_ids[i % len(rts_gmlc_wind_ids)]
        mappings.append(
            GeneratorMapping(
                tiny_gen_uid=uid,
                tiny_bus_id=bus,
                resource_type=ResourceType.WIND,
                rts_gmlc_gen_id=rts_id,
                ordinal=i,
            )
        )

    for i, (uid, bus) in enumerate(solar_units):
        rts_id = rts_gmlc_solar_ids[i % len(rts_gmlc_solar_ids)]
        mappings.append(
            GeneratorMapping(
                tiny_gen_uid=uid,
                tiny_bus_id=bus,
                resource_type=ResourceType.SOLAR,
                rts_gmlc_gen_id=rts_id,
                ordinal=i,
            )
        )

    return mappings


# ---------------------------------------------------------------------------
# Correlation estimation
# ---------------------------------------------------------------------------


def estimate_tiny_correlation(
    rts_gmlc_profiles: np.ndarray,
    mappings: list[GeneratorMapping],
    rts_gmlc_gen_ids: list[str],
) -> CorrelationResult:
    """Estimate 5x5 Spearman rank correlation for TINY generators.

    Uses the mapped RTS-GMLC generator profiles. Each TINY generator
    is mapped to an RTS-GMLC counterpart; the Spearman rank correlation
    of the RTS-GMLC profiles is used as the TINY correlation estimate.

    Args:
        rts_gmlc_profiles: Array of shape (8760, N_rts_gens), all RTS-GMLC profiles.
        mappings: Generator mappings from TINY to RTS-GMLC.
        rts_gmlc_gen_ids: RTS-GMLC generator IDs matching profile columns.

    Returns:
        CorrelationResult with the estimated correlation matrix.
    """
    n_tiny = len(mappings)
    gen_order = [m.tiny_gen_uid for m in mappings]

    # Build the RTS-GMLC column index map
    rts_id_to_col = {gid: i for i, gid in enumerate(rts_gmlc_gen_ids)}

    # Extract the columns for each mapped RTS-GMLC generator
    cols = []
    for m in mappings:
        if m.rts_gmlc_gen_id in rts_id_to_col:
            cols.append(rts_id_to_col[m.rts_gmlc_gen_id])
        else:
            # Fallback: use ordinal position
            col_idx = min(m.ordinal, rts_gmlc_profiles.shape[1] - 1)
            cols.append(col_idx)

    selected_profiles = rts_gmlc_profiles[:, cols]

    # Compute Spearman rank correlation
    if n_tiny <= 1:
        corr_matrix = np.eye(n_tiny)
    else:
        corr_matrix, _ = stats.spearmanr(selected_profiles)
        if corr_matrix.ndim == 0:
            corr_matrix = np.array([[1.0, float(corr_matrix)], [float(corr_matrix), 1.0]])

    # Check PSD
    eigvals = np.linalg.eigvalsh(corr_matrix)
    is_psd = bool(np.all(eigvals >= -1e-10))
    psd_projected = False

    if not is_psd:
        # Project to nearest PSD matrix
        eigvals_clipped = np.maximum(eigvals, 1e-10)
        eigvecs = np.linalg.eigh(corr_matrix)[1]
        corr_matrix = eigvecs @ np.diag(eigvals_clipped) @ eigvecs.T
        # Normalize diagonal to 1
        d = np.sqrt(np.diag(corr_matrix))
        corr_matrix = corr_matrix / np.outer(d, d)
        psd_projected = True

    return CorrelationResult(
        matrix=corr_matrix.tolist(),
        generator_order=gen_order,
        is_psd=True,  # After potential projection, always PSD
        psd_projected=psd_projected,
    )


# ---------------------------------------------------------------------------
# Forecast generation pipeline
# ---------------------------------------------------------------------------


def smooth_profile(values: np.ndarray, window: int) -> np.ndarray:
    """Apply centered moving-average smoothing to a 24-hour profile.

    At edges, the window narrows symmetrically (partial windows).

    Args:
        values: 1-D array of length 24.
        window: Width of the centered kernel. Must be >= 1.

    Returns:
        1-D array of length 24 with smoothed values.
    """
    if window <= 1:
        return values.copy()

    n = len(values)
    half = (window - 1) // 2
    smoothed = np.empty(n)

    for i in range(n):
        lo = max(0, i - half)
        hi = min(n - 1, i + half)
        smoothed[i] = np.mean(values[lo : hi + 1])

    return smoothed


def add_bias(
    smoothed: np.ndarray,
    pmax: float,
    bias_fraction: float,
) -> np.ndarray:
    """Add systematic bias to a smoothed profile.

    Args:
        smoothed: 1-D array of smoothed MW values.
        pmax: Generator nameplate capacity in MW.
        bias_fraction: Bias as a fraction of pmax.

    Returns:
        1-D array with bias added.
    """
    return smoothed + bias_fraction * pmax


def inject_noise(
    biased: np.ndarray,
    actual: np.ndarray,
    t_fit: StudentTFit,
    rng: np.random.Generator,
) -> np.ndarray:
    """Inject Student-t noise scaled by actual generation level.

    noise[h] = t_sample * actual[h]. When actual[h] is zero, noise is zero.

    Args:
        biased: 1-D array of smoothed+biased MW values.
        actual: 1-D array of original actual MW values.
        t_fit: Fitted Student-t parameters.
        rng: Seeded numpy random Generator.

    Returns:
        1-D array with noise added.
    """
    result = biased.copy()
    for h in range(len(biased)):
        if actual[h] == 0.0:
            continue
        raw = rng.standard_t(t_fit.df)
        noise_val = (t_fit.loc + t_fit.scale * raw) * actual[h]
        result[h] += noise_val
    return result


def clamp_and_zero_nights(
    forecast: np.ndarray,
    pmax: float,
    resource_type: ResourceType,
) -> np.ndarray:
    """Clamp to [0, Pmax] and zero solar nighttime hours.

    Args:
        forecast: 1-D array of length 24, forecast MW values.
        pmax: Generator nameplate capacity in MW.
        resource_type: WIND or SOLAR.

    Returns:
        1-D array with clamped and night-zeroed values.
    """
    result = np.clip(forecast, 0.0, pmax)
    if resource_type == ResourceType.SOLAR:
        for h in range(24):
            hour_ending = h + 1
            if hour_ending in SOLAR_NIGHTTIME_HOURS:
                result[h] = 0.0
    return result


def generate_forecast(
    actual: GeneratorProfile,
    t_fit: StudentTFit,
    config: ForecastConfig,
    rng: np.random.Generator,
) -> GeneratorProfile:
    """Generate a forecast profile for a single generator.

    Pipeline: smooth -> bias -> noise -> clamp -> zero nights.

    Args:
        actual: The generator's actual 24-hour profile.
        t_fit: Fitted Student-t parameters for this resource type.
        config: Forecast generation configuration.
        rng: Seeded numpy random Generator.

    Returns:
        A GeneratorProfile with forecast values.
    """
    resource_type = t_fit.resource_type

    # Step 1: Smooth
    smoothed = smooth_profile(actual.hourly_mw, config.smoothing_window)

    # Step 2: Bias
    bias_frac = (
        config.wind_bias_fraction
        if resource_type == ResourceType.WIND
        else config.solar_bias_fraction
    )
    biased = add_bias(smoothed, actual.pmax_mw, bias_frac)

    # Step 3: Noise
    noisy = inject_noise(biased, actual.hourly_mw, t_fit, rng)

    # Step 4: Clamp and zero nights
    final = clamp_and_zero_nights(noisy, actual.pmax_mw, resource_type)

    return GeneratorProfile(
        gen_uid=actual.gen_uid,
        bus_id=actual.bus_id,
        pmax_mw=actual.pmax_mw,
        hourly_mw=final,
    )


# ---------------------------------------------------------------------------
# Iman-Conover method
# ---------------------------------------------------------------------------


def iman_conover(
    independent_samples: np.ndarray,
    target_correlation: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply Iman-Conover to impose rank correlation on independent samples.

    Reorders each column's values so the rank correlation matches the target
    while preserving marginal distributions (each column retains its original
    values, just reordered).

    Args:
        independent_samples: Array of shape (N, K), independent samples.
        target_correlation: Array of shape (K, K), target rank correlation.
        rng: Seeded numpy random Generator.

    Returns:
        Array of shape (N, K) with reordered values.
    """
    n_samples, n_vars = independent_samples.shape

    if n_vars <= 1:
        return independent_samples.copy()

    from scipy.stats import norm

    # Step 1: Generate reference normal scores
    reference = rng.standard_normal(size=(n_samples, n_vars))
    score_matrix = np.empty_like(reference)
    for j in range(n_vars):
        order = np.argsort(reference[:, j])
        ranks = np.empty(n_samples, dtype=np.float64)
        ranks[order] = np.arange(1, n_samples + 1)
        score_matrix[:, j] = norm.ppf(ranks / (n_samples + 1))

    # Step 2: Cholesky of target correlation
    try:
        l_target = np.linalg.cholesky(target_correlation)
    except np.linalg.LinAlgError:
        eigvals, eigvecs = np.linalg.eigh(target_correlation)
        eigvals = np.maximum(eigvals, 1e-10)
        l_target = eigvecs @ np.diag(np.sqrt(eigvals))

    # Step 3: Cholesky of current score correlation
    current_corr = np.corrcoef(score_matrix, rowvar=False)
    try:
        l_current = np.linalg.cholesky(current_corr)
    except np.linalg.LinAlgError:
        eigvals, eigvecs = np.linalg.eigh(current_corr)
        eigvals = np.maximum(eigvals, 1e-10)
        l_current = eigvecs @ np.diag(np.sqrt(eigvals))

    # Step 4: Transform scores to match target correlation
    transformed = score_matrix @ np.linalg.inv(l_current) @ l_target.T

    # Step 5: Reorder original samples according to transformed ranks
    result = np.empty_like(independent_samples)
    for j in range(n_vars):
        desired_order = np.argsort(np.argsort(transformed[:, j]))
        sorted_samples = np.sort(independent_samples[:, j])
        result[:, j] = sorted_samples[desired_order]

    return result


# ---------------------------------------------------------------------------
# Scenario multiplier generation
# ---------------------------------------------------------------------------


def generate_scenario_multipliers(
    wind_forecasts: list[GeneratorProfile],
    solar_forecasts: list[GeneratorProfile],
    wind_fit: StudentTFit,
    solar_fit: StudentTFit,
    correlation: CorrelationResult,
    config: ForecastConfig,
) -> ScenarioMultiplierSet:
    """Generate 50 correlated scenario multipliers via Iman-Conover.

    For each hour: draw independent Student-t samples per generator,
    reorder via Iman-Conover to match target correlation, convert to
    multiplicative factors (multiplier = 1 + error), clamp to physical bounds.

    Args:
        wind_forecasts: Wind forecast profiles.
        solar_forecasts: Solar forecast profiles.
        wind_fit: Fitted Student-t for wind.
        solar_fit: Fitted Student-t for solar.
        correlation: Estimated rank correlation.
        config: Forecast configuration with num_scenarios and seed.

    Returns:
        ScenarioMultiplierSet with shape (num_scenarios, 5, 24).
    """
    all_forecasts = list(wind_forecasts) + list(solar_forecasts)
    all_fits = [wind_fit] * len(wind_forecasts) + [solar_fit] * len(solar_forecasts)
    gen_order = [f.gen_uid for f in all_forecasts]
    n_gens = len(all_forecasts)
    n_scenarios = config.num_scenarios

    rng = np.random.Generator(np.random.PCG64(config.master_seed + 100))
    corr_matrix = np.array(correlation.matrix)

    multipliers = np.ones((n_scenarios, n_gens, 24))

    for h in range(24):
        hour_ending = h + 1

        # Check if this is a nighttime hour for solar
        is_night = hour_ending in SOLAR_NIGHTTIME_HOURS

        # Draw independent Student-t samples
        indep = np.zeros((n_scenarios, n_gens))
        for j in range(n_gens):
            fit = all_fits[j]
            if is_night and fit.resource_type == ResourceType.SOLAR:
                continue  # Leave as zeros for nighttime solar
            indep[:, j] = rng.standard_t(fit.df, size=n_scenarios) * fit.scale + fit.loc

        # Apply Iman-Conover (only if we have >1 generator with nonzero samples)
        nonzero_cols = np.any(indep != 0, axis=0)
        if np.sum(nonzero_cols) > 1:
            # Use full correlation matrix for reordering
            reordered = iman_conover(indep, corr_matrix, rng)
        else:
            reordered = indep

        # Convert to multipliers: multiplier = 1 + error
        for j in range(n_gens):
            forecast_val = all_forecasts[j].hourly_mw[h]
            if forecast_val > 0:
                multipliers[:, j, h] = 1.0 + reordered[:, j]
            else:
                multipliers[:, j, h] = 1.0

        # Clamp to physical bounds [0, Pmax/forecast]
        for j in range(n_gens):
            forecast_val = all_forecasts[j].hourly_mw[h]
            pmax = all_forecasts[j].pmax_mw
            if forecast_val > 0:
                upper = pmax / forecast_val
                multipliers[:, j, h] = np.clip(multipliers[:, j, h], 0.0, upper)

        # Nighttime solar -> multiplier = 1.0
        if is_night:
            for j in range(n_gens):
                if all_fits[j].resource_type == ResourceType.SOLAR:
                    multipliers[:, j, h] = 1.0

    return ScenarioMultiplierSet(
        multipliers=multipliers,
        generator_order=gen_order,
        num_scenarios=n_scenarios,
        seed_used=config.master_seed,
    )


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------


def _load_profile_csv(
    csv_path: Path,
    resource_type: ResourceType,
) -> list[GeneratorProfile]:
    """Load profiles from a canonical gen_uid + HR_1..HR_24 CSV.

    Args:
        csv_path: Path to the CSV file.
        resource_type: WIND or SOLAR (for bus_id lookup).

    Returns:
        List of GeneratorProfile.
    """
    profiles: list[GeneratorProfile] = []
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            gen_uid = row["gen_uid"]
            values = np.array([float(row[col]) for col in HOUR_COLUMNS])
            pmax = float(np.max(values)) if np.any(values > 0) else 0.0
            # Extract bus_id from gen_uid if possible
            bus_id = 0
            profiles.append(
                GeneratorProfile(
                    gen_uid=gen_uid,
                    bus_id=bus_id,
                    pmax_mw=pmax,
                    hourly_mw=values,
                )
            )
    return profiles


def write_forecast_actual_csvs(
    wind_forecasts: list[GeneratorProfile],
    wind_actuals: list[GeneratorProfile],
    solar_forecasts: list[GeneratorProfile],
    solar_actuals: list[GeneratorProfile],
    output_dir: Path,
) -> None:
    """Write forecast and actual CSV files.

    Writes four files:
    - wind_forecast_24h.csv
    - wind_actual_24h.csv
    - solar_forecast_24h.csv
    - solar_actual_24h.csv

    Format: gen_uid, HR_1..HR_24 (values to 4 decimal places).

    Args:
        wind_forecasts: Wind forecast profiles.
        wind_actuals: Wind actual profiles.
        solar_forecasts: Solar forecast profiles.
        solar_actuals: Solar actual profiles.
        output_dir: Output directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_profile_csv(wind_forecasts, output_dir / "wind_forecast_24h.csv")
    _write_profile_csv(wind_actuals, output_dir / "wind_actual_24h.csv")
    _write_profile_csv(solar_forecasts, output_dir / "solar_forecast_24h.csv")
    _write_profile_csv(solar_actuals, output_dir / "solar_actual_24h.csv")


def _write_profile_csv(
    profiles: list[GeneratorProfile],
    dest_path: Path,
) -> None:
    """Write profiles in canonical gen_uid + HR_1..HR_24 format."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid"] + HOUR_COLUMNS)
        for p in profiles:
            writer.writerow([p.gen_uid] + [f"{v:.4f}" for v in p.hourly_mw])


def write_scenario_multipliers_csv(
    scenario_set: ScenarioMultiplierSet,
    dest_path: Path,
) -> None:
    """Write scenario multipliers to CSV.

    Format: scenario, gen_uid, HR_1..HR_24. One row per (scenario, generator).
    Values rounded to 6 decimal places.

    Args:
        scenario_set: The scenario multiplier data.
        dest_path: Output CSV file path.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["scenario", "gen_uid"] + HOUR_COLUMNS)

        n_scenarios = scenario_set.multipliers.shape[0]
        n_gens = scenario_set.multipliers.shape[1]

        for s in range(n_scenarios):
            for g in range(n_gens):
                row = [s + 1, scenario_set.generator_order[g]] + [
                    f"{v:.6f}" for v in scenario_set.multipliers[s, g, :]
                ]
                writer.writerow(row)


def write_stochastic_metadata(
    output: StochasticScenarioOutput,
    dest_path: Path,
) -> None:
    """Write stochastic scenario metadata as JSON.

    Args:
        output: The complete output container.
        dest_path: Output JSON file path.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "script_version": output.script_version,
        "generated_at": output.generated_at,
        "forecast_config": {
            "smoothing_window": output.forecast_config.smoothing_window,
            "wind_bias_fraction": output.forecast_config.wind_bias_fraction,
            "solar_bias_fraction": output.forecast_config.solar_bias_fraction,
            "master_seed": output.forecast_config.master_seed,
            "num_scenarios": output.forecast_config.num_scenarios,
        },
        "wind_student_t": {
            "df": output.wind_fit.df,
            "loc": output.wind_fit.loc,
            "scale": output.wind_fit.scale,
            "sample_size": output.wind_fit.sample_size,
            "num_generators_pooled": output.wind_fit.num_generators_pooled,
        },
        "solar_student_t": {
            "df": output.solar_fit.df,
            "loc": output.solar_fit.loc,
            "scale": output.solar_fit.scale,
            "sample_size": output.solar_fit.sample_size,
            "num_generators_pooled": output.solar_fit.num_generators_pooled,
        },
        "correlation": {
            "matrix": output.correlation.matrix,
            "generator_order": output.correlation.generator_order,
            "is_psd": output.correlation.is_psd,
            "psd_projected": output.correlation.psd_projected,
        },
        "scenario_multipliers": {
            "shape": list(output.scenario_multipliers.multipliers.shape),
            "generator_order": output.scenario_multipliers.generator_order,
            "num_scenarios": output.scenario_multipliers.num_scenarios,
            "seed_used": output.scenario_multipliers.seed_used,
        },
        "output_files": [
            "wind_forecast_24h.csv",
            "wind_actual_24h.csv",
            "solar_forecast_24h.csv",
            "solar_actual_24h.csv",
            "scenarios/scenario_multipliers_50x24.csv",
        ],
        "notes": output.notes,
    }

    with open(dest_path, "w") as fh:
        json.dump(metadata, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def main(
    data_dir: Path | None = None,
    rts_gmlc_dir: Path | None = None,
    config: ForecastConfig | None = None,
) -> StochasticScenarioOutput:
    """Entry point: generate stochastic scenarios for the TINY (case39) network.

    Steps:
    1. Load full-year RTS-GMLC profiles and fit Student-t distributions.
    2. Map TINY generators to RTS-GMLC counterparts by ordinal position.
    3. Estimate 5x5 Spearman rank correlation matrix.
    4. Load D4 actual profiles (wind_24h.csv, solar_24h.csv).
    5. Generate forecasts: smooth + bias + noise, clamp to [0, Pmax].
    6. Generate 50 scenarios via Iman-Conover.
    7. Write output CSVs and metadata JSON.

    Args:
        data_dir: Base data directory. Defaults to <repo>/data/.
        rts_gmlc_dir: RTS-GMLC data directory. Defaults to <data_dir>/rts_gmlc/.
        config: Forecast configuration. Defaults to ForecastConfig().

    Returns:
        StochasticScenarioOutput with all results.
    """
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent.parent

    if rts_gmlc_dir is None:
        rts_gmlc_dir = data_dir / "rts_gmlc"

    if config is None:
        config = ForecastConfig()

    timeseries_dir = data_dir / "timeseries" / "case39"
    output_dir = timeseries_dir
    scenarios_dir = timeseries_dir / "scenarios"

    # Step 1: Load RTS-GMLC profiles and fit Student-t
    logger.info("Loading RTS-GMLC wind profiles...")
    wind_profiles_8760, wind_gen_ids = load_rts_gmlc_full_year_profiles(
        rts_gmlc_dir, ResourceType.WIND
    )
    logger.info("Loading RTS-GMLC solar profiles...")
    solar_profiles_8760, solar_gen_ids = load_rts_gmlc_full_year_profiles(
        rts_gmlc_dir, ResourceType.SOLAR
    )

    # Compute CF changes
    wind_pmax = np.max(wind_profiles_8760, axis=0)
    solar_pmax = np.max(solar_profiles_8760, axis=0)
    wind_cf_changes = compute_capacity_factor_changes(wind_profiles_8760, wind_pmax)
    solar_cf_changes = compute_capacity_factor_changes(solar_profiles_8760, solar_pmax)

    # Fit Student-t
    logger.info("Fitting Student-t distributions...")
    wind_fit = fit_student_t_pooled(wind_cf_changes, ResourceType.WIND)
    solar_fit = fit_student_t_pooled(solar_cf_changes, ResourceType.SOLAR)

    # Step 2: Map TINY to RTS-GMLC generators
    tiny_units_path = timeseries_dir / "renewable_units.csv"
    mappings = map_tiny_to_rts_gmlc_generators(tiny_units_path, wind_gen_ids, solar_gen_ids)

    # Step 3: Estimate correlation
    logger.info("Estimating rank correlation matrix...")
    all_rts_profiles = np.hstack([wind_profiles_8760, solar_profiles_8760])
    all_rts_ids = wind_gen_ids + solar_gen_ids
    correlation = estimate_tiny_correlation(all_rts_profiles, mappings, all_rts_ids)

    # Step 4: Load D4 actual profiles
    logger.info("Loading D4 actual profiles...")
    wind_actual_path = timeseries_dir / "wind_24h.csv"
    solar_actual_path = timeseries_dir / "solar_24h.csv"

    # Try canonical names first, then alternative names
    if not wind_actual_path.exists():
        wind_actual_path = timeseries_dir / "wind_actual_24h.csv"
    if not solar_actual_path.exists():
        solar_actual_path = timeseries_dir / "solar_actual_24h.csv"

    if wind_actual_path.exists():
        wind_actuals = _load_profile_csv(wind_actual_path, ResourceType.WIND)
    else:
        logger.warning("Wind actual CSV not found, generating synthetic actuals")
        wind_actuals = _generate_synthetic_actuals(mappings, ResourceType.WIND)

    if solar_actual_path.exists():
        solar_actuals = _load_profile_csv(solar_actual_path, ResourceType.SOLAR)
    else:
        logger.warning("Solar actual CSV not found, generating synthetic actuals")
        solar_actuals = _generate_synthetic_actuals(mappings, ResourceType.SOLAR)

    # Step 5: Generate forecasts
    logger.info("Generating forecasts...")
    rng = np.random.Generator(np.random.PCG64(config.master_seed))

    wind_forecasts: list[GeneratorProfile] = []
    for actual in wind_actuals:
        forecast = generate_forecast(actual, wind_fit, config, rng)
        wind_forecasts.append(forecast)

    solar_forecasts: list[GeneratorProfile] = []
    for actual in solar_actuals:
        forecast = generate_forecast(actual, solar_fit, config, rng)
        solar_forecasts.append(forecast)

    # Step 6: Generate scenario multipliers
    logger.info("Generating %d scenario multipliers...", config.num_scenarios)
    scenario_set = generate_scenario_multipliers(
        wind_forecasts, solar_forecasts, wind_fit, solar_fit, correlation, config
    )

    # Step 7: Write outputs
    logger.info("Writing output files...")
    write_forecast_actual_csvs(
        wind_forecasts, wind_actuals, solar_forecasts, solar_actuals, output_dir
    )
    write_scenario_multipliers_csv(scenario_set, scenarios_dir / "scenario_multipliers_50x24.csv")

    output = StochasticScenarioOutput(
        wind_fit=wind_fit,
        solar_fit=solar_fit,
        correlation=correlation,
        forecast_config=config,
        wind_forecasts=wind_forecasts,
        wind_actuals=wind_actuals,
        solar_forecasts=solar_forecasts,
        solar_actuals=solar_actuals,
        scenario_multipliers=scenario_set,
        output_dir=str(output_dir),
        script_version=__version__,
        generated_at=datetime.now(timezone.utc).isoformat(),
        notes=[
            "Student-t fitted from synthetic RTS-GMLC profiles",
            "Correlation estimated via Spearman rank on mapped generators",
            "Iman-Conover preserves marginals while imposing rank correlation",
            f"Master seed = {config.master_seed}",
        ],
    )

    write_stochastic_metadata(output, scenarios_dir / "stochastic_metadata.json")

    logger.info("Stochastic scenario generation complete.")
    return output


def _generate_synthetic_actuals(
    mappings: list[GeneratorMapping],
    resource_type: ResourceType,
) -> list[GeneratorProfile]:
    """Generate synthetic 24h actual profiles for TINY generators."""
    from scripts.renewable_profiles import (
        DEFAULT_SOLAR_CF_24H,
        DEFAULT_WIND_CF_24H,
    )

    cf = DEFAULT_WIND_CF_24H if resource_type == ResourceType.WIND else DEFAULT_SOLAR_CF_24H
    pmax = 243.88 if resource_type == ResourceType.WIND else 243.88

    profiles: list[GeneratorProfile] = []
    for m in mappings:
        if m.resource_type != resource_type:
            continue
        values = np.array([c * pmax for c in cf])
        profiles.append(
            GeneratorProfile(
                gen_uid=m.tiny_gen_uid,
                bus_id=m.tiny_bus_id,
                pmax_mw=pmax,
                hourly_mw=values,
            )
        )
    return profiles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
