"""Correlated Scenario Multiplier Generation for renewable generation profiles.

Generates 50 correlated scenario multiplier sets for TINY and SMALL networks.
Multipliers preserve heavy-tailed marginals (Student-t from D1) and spatial
dependence (rank correlation from D2, via Iman-Conover method). Applied to
forecast profiles from D3.

Pipeline per hour: (1) draw independent Student-t samples, (2) apply
Iman-Conover rank reordering, (3) convert errors to multipliers
(1 + error/forecast), (4) clamp to [0, Pmax/forecast], (5) nighttime
solar -> 1.0.

PRD 04/04 -- Correlated Scenario Multiplier Generation.
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

from scripts.fit_student_t import (
    HourFitResult,
    ResourceType,
    StudentTParams,
    load_student_t_json,
)
from scripts.generate_forecasts import load_actual_profiles

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Network identifiers for scenario generation."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"


@dataclass(frozen=True)
class ScenarioConfig:
    """Configuration for scenario generation."""

    n_scenarios: int = 50
    master_seed: int = 42


SCENARIO_SEED_OFFSETS: dict[NetworkId, int] = {
    NetworkId.TINY: 100,
    NetworkId.SMALL: 200,
}


@dataclass(frozen=True)
class GeneratorScenarioInput:
    """Input data for scenario generation for a single generator."""

    gen_uid: str
    resource_type: ResourceType
    pmax: float
    forecast_values: np.ndarray  # shape (24,)
    night_hours: list[int]


@dataclass(frozen=True)
class ClampingDiagnostics:
    """Diagnostics from the clamping step."""

    n_clamped_lower: int  # number of values clamped to 0
    n_clamped_upper: int  # number of values clamped to Pmax/forecast
    fraction_clamped: float  # fraction of total values that were clamped


@dataclass(frozen=True)
class CorrelationDiagnostics:
    """Diagnostics comparing target vs achieved rank correlation."""

    target_mean_abs_off_diag: float
    achieved_mean_abs_off_diag: float
    max_abs_difference: float


@dataclass(frozen=True)
class MarginalDiagnostics:
    """Diagnostics for marginal distribution preservation."""

    gen_uid: str
    hour: int
    ks_statistic: float
    ks_pvalue: float


@dataclass(frozen=True)
class ScenarioDiagnostics:
    """Aggregated diagnostics for a single network's scenario generation."""

    network_id: NetworkId
    n_generators: int
    n_scenarios: int
    n_hours: int
    clamping: ClampingDiagnostics
    correlation: CorrelationDiagnostics | None
    marginals: list[MarginalDiagnostics]


@dataclass(frozen=True)
class ScenarioMultiplierResult:
    """Scenario multipliers for one generator across all scenarios and hours.

    multipliers has shape (n_scenarios, 24).
    """

    gen_uid: str
    resource_type: ResourceType
    multipliers: np.ndarray  # shape (n_scenarios, 24)


@dataclass(frozen=True)
class ScenarioGenerationOutput:
    """Top-level container for all scenario generation results."""

    network_id: NetworkId
    results: list[ScenarioMultiplierResult]
    diagnostics: ScenarioDiagnostics
    config: ScenarioConfig
    script_version: str
    generated_at: str
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Correlation matrix loading
# ---------------------------------------------------------------------------


def load_correlation_matrix(
    json_path: Path,
    network_id: NetworkId,
) -> tuple[np.ndarray, list[str]]:
    """Load a rank correlation matrix for a network from the D2 JSON output.

    Reads the rank_correlation_matrix.json produced by estimate_correlation.py
    and extracts the correlation matrix and generator IDs for the specified
    network.

    Args:
        json_path: Path to rank_correlation_matrix.json.
        network_id: Which network's correlation matrix to load.

    Returns:
        A tuple of (correlation_matrix, generator_ids) where correlation_matrix
        is an (G, G) numpy array and generator_ids is a list of G generator ID
        strings.

    Raises:
        FileNotFoundError: If json_path does not exist.
        ValueError: If the network is not found in the JSON.
    """
    if not json_path.exists():
        msg = f"Correlation matrix JSON not found: {json_path}"
        raise FileNotFoundError(msg)

    with open(json_path) as fh:
        data = json.load(fh)

    # Map network_id to the correlation JSON's network_id convention
    # TINY -> "TINY", SMALL -> "ACTIVSg2000"
    network_key_map: dict[NetworkId, str] = {
        NetworkId.TINY: "TINY",
        NetworkId.SMALL: "ACTIVSg2000",
    }
    target_key = network_key_map[network_id]

    for net_result in data["networks"]:
        if net_result["network_id"] == target_key:
            matrix = np.array(net_result["correlation_matrix"], dtype=np.float64)
            gen_ids = [g["generator_id"] for g in net_result["generators"]]
            return matrix, gen_ids

    msg = f"Network '{target_key}' not found in correlation JSON"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Core pipeline functions
# ---------------------------------------------------------------------------


def draw_independent_samples(
    n_scenarios: int,
    n_generators: int,
    hour_fits: list[HourFitResult],
    hour: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw independent Student-t samples for one hour across all generators.

    For nighttime hours (is_fitted=False), returns zeros (sentinel) since
    multipliers will be set to 1.0 anyway.

    Args:
        n_scenarios: Number of scenarios to generate.
        n_generators: Number of generators.
        hour_fits: List of 24 HourFitResult entries (one per hour-of-day).
        hour: Hour-of-day (0-23) to draw samples for.
        rng: Seeded numpy random Generator.

    Returns:
        Array of shape (n_scenarios, n_generators) with independent samples.
    """
    fit = hour_fits[hour]

    if not fit.is_fitted:
        # Nighttime sentinel: return zeros
        return np.zeros((n_scenarios, n_generators))

    df = fit.df
    # Draw from Student-t with fitted df, then apply loc and scale
    raw = rng.standard_t(df, size=(n_scenarios, n_generators))
    samples = fit.loc + fit.scale * raw
    return samples


def iman_conover_reorder(
    independent_samples: np.ndarray,
    target_correlation: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply the Iman-Conover method to impose rank correlation structure.

    Reorders the rows of each column so that the rank correlation of the
    output matches the target correlation matrix while preserving the
    marginal distributions (each column retains its original values, just
    reordered).

    For a single generator (1 column), returns the input unchanged since
    correlation is undefined for a single variable.

    Args:
        independent_samples: Array of shape (n_scenarios, n_generators).
        target_correlation: Array of shape (n_generators, n_generators),
            a PSD rank correlation matrix.
        rng: Seeded numpy random Generator.

    Returns:
        Array of shape (n_scenarios, n_generators) with reordered values.
    """
    n_scenarios, n_generators = independent_samples.shape

    if n_generators <= 1:
        return independent_samples.copy()

    # Step 1: Generate a "score" matrix from standard normal quantiles
    # Use van der Waerden scores: normal quantile of rank/(n+1)
    from scipy.stats import norm

    # Create score matrix from ranks of a random reference
    # Generate reference uniform random samples and compute their normal scores
    reference = rng.standard_normal(size=(n_scenarios, n_generators))

    # Compute ranks of the reference
    score_matrix = np.empty_like(reference)
    for j in range(n_generators):
        order = np.argsort(reference[:, j])
        ranks = np.empty(n_scenarios, dtype=np.float64)
        ranks[order] = np.arange(1, n_scenarios + 1)
        score_matrix[:, j] = norm.ppf(ranks / (n_scenarios + 1))

    # Step 2: Compute Cholesky of the target correlation
    try:
        L_target = np.linalg.cholesky(target_correlation)
    except np.linalg.LinAlgError:
        # If not PSD, use eigenvalue decomposition fallback
        eigvals, eigvecs = np.linalg.eigh(target_correlation)
        eigvals = np.maximum(eigvals, 1e-10)
        L_target = eigvecs @ np.diag(np.sqrt(eigvals))

    # Step 3: Compute current correlation of score_matrix and its Cholesky
    current_corr = np.corrcoef(score_matrix, rowvar=False)
    try:
        L_current = np.linalg.cholesky(current_corr)
    except np.linalg.LinAlgError:
        eigvals, eigvecs = np.linalg.eigh(current_corr)
        eigvals = np.maximum(eigvals, 1e-10)
        L_current = eigvecs @ np.diag(np.sqrt(eigvals))

    # Step 4: Transform score matrix to have the target correlation
    # T = S @ L_current^{-1} @ L_target^T
    T = score_matrix @ np.linalg.inv(L_current) @ L_target.T

    # Step 5: Use the rank ordering from T to reorder the original samples
    result = np.empty_like(independent_samples)
    for j in range(n_generators):
        # Get the desired order from T's column j
        desired_order = np.argsort(np.argsort(T[:, j]))
        # Sort the original samples and place them in the desired order
        sorted_samples = np.sort(independent_samples[:, j])
        result[:, j] = sorted_samples[desired_order]

    return result


def errors_to_multipliers(
    errors: np.ndarray,
    forecasts: np.ndarray,
) -> np.ndarray:
    """Convert error samples to scenario multipliers.

    multiplier = 1 + error / forecast

    For zero-forecast entries, the multiplier is set to 1.0 (no scaling
    possible when forecast is zero).

    Args:
        errors: Array of shape (n_scenarios, n_generators) with error samples.
        forecasts: Array of shape (n_generators,) with forecast values for
            the current hour.

    Returns:
        Array of shape (n_scenarios, n_generators) with multipliers.
    """
    multipliers = np.ones_like(errors)
    for j in range(errors.shape[1]):
        if forecasts[j] != 0.0:
            multipliers[:, j] = 1.0 + errors[:, j] / forecasts[j]
    return multipliers


def clamp_multipliers(
    multipliers: np.ndarray,
    forecasts: np.ndarray,
    pmaxes: np.ndarray,
) -> np.ndarray:
    """Clamp multipliers to [0, Pmax/forecast] per generator.

    For zero-forecast generators, multipliers remain unchanged (already 1.0).

    Args:
        multipliers: Array of shape (n_scenarios, n_generators).
        forecasts: Array of shape (n_generators,) with forecast values.
        pmaxes: Array of shape (n_generators,) with Pmax values.

    Returns:
        Array of shape (n_scenarios, n_generators) with clamped multipliers.
    """
    result = multipliers.copy()
    for j in range(multipliers.shape[1]):
        if forecasts[j] != 0.0:
            upper = pmaxes[j] / forecasts[j]
            result[:, j] = np.clip(result[:, j], 0.0, upper)
        # If forecast is zero, leave multiplier as-is (should be 1.0)
    return result


def apply_night_mask(
    multipliers: np.ndarray,
    resource_types: list[ResourceType],
    hour: int,
    night_hours: list[int],
) -> np.ndarray:
    """Set multipliers to 1.0 for solar generators during nighttime hours.

    Wind generators are never affected by the night mask.

    Args:
        multipliers: Array of shape (n_scenarios, n_generators).
        resource_types: List of n_generators ResourceType values.
        hour: Current hour-of-day (0-23).
        night_hours: List of nighttime hour-of-day integers.

    Returns:
        Array of shape (n_scenarios, n_generators) with night mask applied.
    """
    if hour not in night_hours:
        return multipliers.copy()

    result = multipliers.copy()
    for j, rt in enumerate(resource_types):
        if rt == ResourceType.SOLAR:
            result[:, j] = 1.0
    return result


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def compute_clamping_diagnostics(
    original: np.ndarray,
    clamped: np.ndarray,
) -> ClampingDiagnostics:
    """Compute diagnostics from the clamping step.

    Args:
        original: Pre-clamping multipliers, shape (n_scenarios, n_generators).
        clamped: Post-clamping multipliers, same shape.

    Returns:
        ClampingDiagnostics with counts and fraction of clamped values.
    """
    total = original.size
    n_clamped_lower = int(np.sum((original < 0.0) & (clamped == 0.0)))
    diff = original - clamped
    n_clamped_upper = int(np.sum((diff > 1e-12) & ~(original < 0.0)))

    n_total_clamped = n_clamped_lower + n_clamped_upper
    fraction = n_total_clamped / total if total > 0 else 0.0

    return ClampingDiagnostics(
        n_clamped_lower=n_clamped_lower,
        n_clamped_upper=n_clamped_upper,
        fraction_clamped=fraction,
    )


def compute_correlation_diagnostics(
    target_corr: np.ndarray,
    achieved_samples: np.ndarray,
) -> CorrelationDiagnostics | None:
    """Compute diagnostics comparing target vs achieved rank correlation.

    Args:
        target_corr: Target correlation matrix, shape (G, G).
        achieved_samples: Reordered samples, shape (n_scenarios, G).

    Returns:
        CorrelationDiagnostics, or None if fewer than 2 generators.
    """
    n_gen = achieved_samples.shape[1]
    if n_gen < 2:
        return None

    from scipy.stats import spearmanr

    achieved_corr, _ = spearmanr(achieved_samples)
    if achieved_corr.ndim == 0:
        # Only 2 variables returns a scalar
        achieved_corr = np.array([[1.0, float(achieved_corr)], [float(achieved_corr), 1.0]])

    mask = ~np.eye(n_gen, dtype=bool)
    target_off = target_corr[mask]
    achieved_off = achieved_corr[mask]

    return CorrelationDiagnostics(
        target_mean_abs_off_diag=float(np.mean(np.abs(target_off))),
        achieved_mean_abs_off_diag=float(np.mean(np.abs(achieved_off))),
        max_abs_difference=float(np.max(np.abs(target_off - achieved_off))),
    )


def compute_marginal_diagnostics(
    samples: np.ndarray,
    hour_fit: HourFitResult,
    gen_uid: str,
    hour: int,
) -> MarginalDiagnostics | None:
    """Compute KS test diagnostics for marginal distribution preservation.

    Args:
        samples: 1-D array of samples for one generator at one hour.
        hour_fit: The HourFitResult for this hour.
        gen_uid: Generator identifier.
        hour: Hour-of-day (0-23).

    Returns:
        MarginalDiagnostics, or None if the hour is not fitted.
    """
    if not hour_fit.is_fitted:
        return None

    from scipy.stats import kstest

    ks_stat, ks_pval = kstest(samples, "t", args=(hour_fit.df, hour_fit.loc, hour_fit.scale))

    return MarginalDiagnostics(
        gen_uid=gen_uid,
        hour=hour,
        ks_statistic=float(ks_stat),
        ks_pvalue=float(ks_pval),
    )


# ---------------------------------------------------------------------------
# Per-hour and per-resource scenario generation
# ---------------------------------------------------------------------------


def generate_scenarios_single_hour(
    inputs: list[GeneratorScenarioInput],
    hour: int,
    hour_fits: list[HourFitResult],
    correlation_matrix: np.ndarray,
    config: ScenarioConfig,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate scenario multipliers for a single hour across all generators.

    Implements the per-hour pipeline:
    1. Draw independent Student-t samples
    2. Apply Iman-Conover rank reordering
    3. Convert errors to multipliers
    4. Clamp multipliers
    5. Apply night mask

    Args:
        inputs: List of GeneratorScenarioInput, one per generator.
        hour: Hour-of-day (0-23).
        hour_fits: List of 24 HourFitResult entries.
        correlation_matrix: Target rank correlation matrix, shape (G, G).
        config: Scenario configuration.
        rng: Seeded numpy random Generator.

    Returns:
        A tuple of (multipliers, pre_clamp_multipliers, errors) where:
        - multipliers: shape (n_scenarios, n_generators), final multipliers
        - pre_clamp_multipliers: shape (n_scenarios, n_generators), before clamping
        - errors: shape (n_scenarios, n_generators), correlated error samples
    """
    n_gen = len(inputs)
    n_scenarios = config.n_scenarios

    # Step 1: Draw independent samples
    errors = draw_independent_samples(n_scenarios, n_gen, hour_fits, hour, rng)

    # Step 2: Iman-Conover reorder (only if daytime and >1 generator)
    if hour_fits[hour].is_fitted and n_gen > 1:
        errors = iman_conover_reorder(errors, correlation_matrix, rng)

    # Step 3: Convert to multipliers
    forecasts = np.array([inp.forecast_values[hour] for inp in inputs])
    multipliers = errors_to_multipliers(errors, forecasts)

    # Step 4: Clamp
    pmaxes = np.array([inp.pmax for inp in inputs])
    pre_clamp = multipliers.copy()
    multipliers = clamp_multipliers(multipliers, forecasts, pmaxes)

    # Step 5: Night mask
    resource_types = [inp.resource_type for inp in inputs]
    night_hours = inputs[0].night_hours if inputs else []
    multipliers = apply_night_mask(multipliers, resource_types, hour, night_hours)

    return multipliers, pre_clamp, errors


def generate_scenarios_resource(
    inputs: list[GeneratorScenarioInput],
    student_t_params: StudentTParams,
    correlation_matrix: np.ndarray,
    config: ScenarioConfig,
    rng: np.random.Generator,
) -> tuple[list[ScenarioMultiplierResult], ScenarioDiagnostics]:
    """Generate scenario multipliers for all generators across all hours.

    Args:
        inputs: List of GeneratorScenarioInput, one per generator.
        student_t_params: Fitted Student-t parameters from D1.
        correlation_matrix: Target rank correlation matrix, shape (G, G).
        config: Scenario configuration.
        rng: Seeded numpy random Generator.

    Returns:
        A tuple of (results, diagnostics).
    """
    n_gen = len(inputs)
    n_scenarios = config.n_scenarios

    # Initialize per-generator multiplier arrays: (n_scenarios, 24)
    all_multipliers = np.ones((n_gen, n_scenarios, 24))

    # Determine which resource fit to use. We use the first generator's type
    # to decide, but in practice we use per-hour fits which are shared.
    # For mixed wind/solar, we use wind fits for wind and solar fits for solar.
    # However the PRD says we use a single set of hour_fits per resource call,
    # so let's handle the common case where all gens are the same type.

    # Accumulate diagnostics
    total_clamped_lower = 0
    total_clamped_upper = 0
    total_values = 0
    corr_diag: CorrelationDiagnostics | None = None
    marginal_diags: list[MarginalDiagnostics] = []

    # Collect a representative hour's errors for correlation diagnostics
    representative_errors: np.ndarray | None = None

    for hour in range(24):
        # Get the appropriate hour fit for each generator's resource type
        # Use the first generator's resource type to determine fits
        # (in practice all generators in one call share the same resource type)
        rt = inputs[0].resource_type
        resource_fit = student_t_params.wind if rt == ResourceType.WIND else student_t_params.solar
        hour_fits = resource_fit.per_hour

        multipliers, pre_clamp, errors = generate_scenarios_single_hour(
            inputs, hour, hour_fits, correlation_matrix, config, rng
        )

        # Store multipliers
        for j in range(n_gen):
            all_multipliers[j, :, hour] = multipliers[:, j]

        # Accumulate clamping diagnostics
        clamp_diag = compute_clamping_diagnostics(pre_clamp, multipliers)
        total_clamped_lower += clamp_diag.n_clamped_lower
        total_clamped_upper += clamp_diag.n_clamped_upper
        total_values += pre_clamp.size

        # Save representative daytime hour errors for correlation diagnostics
        if hour_fits[hour].is_fitted and representative_errors is None:
            representative_errors = errors

        # Marginal diagnostics: check first generator at each fitted hour
        if hour_fits[hour].is_fitted and n_gen > 0:
            md = compute_marginal_diagnostics(
                errors[:, 0], hour_fits[hour], inputs[0].gen_uid, hour
            )
            if md is not None:
                marginal_diags.append(md)

    # Correlation diagnostics from representative hour
    if representative_errors is not None and n_gen >= 2:
        corr_diag = compute_correlation_diagnostics(correlation_matrix, representative_errors)

    # Build results
    results: list[ScenarioMultiplierResult] = []
    for j in range(n_gen):
        results.append(
            ScenarioMultiplierResult(
                gen_uid=inputs[j].gen_uid,
                resource_type=inputs[j].resource_type,
                multipliers=all_multipliers[j],
            )
        )

    fraction = (total_clamped_lower + total_clamped_upper) / total_values if total_values else 0.0
    overall_clamping = ClampingDiagnostics(
        n_clamped_lower=total_clamped_lower,
        n_clamped_upper=total_clamped_upper,
        fraction_clamped=fraction,
    )

    # Use the network_id from the PRD -- we'll set it in the caller
    diagnostics = ScenarioDiagnostics(
        network_id=NetworkId.TINY,  # placeholder, overridden by caller
        n_generators=n_gen,
        n_scenarios=n_scenarios,
        n_hours=24,
        clamping=overall_clamping,
        correlation=corr_diag,
        marginals=marginal_diags,
    )

    return results, diagnostics


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

_HOUR_COLUMNS = [f"HR_{k}" for k in range(1, 25)]


def write_scenario_csv(
    results: list[ScenarioMultiplierResult],
    dest_path: Path,
) -> None:
    """Write scenario multipliers to a CSV file.

    Format: one row per (generator, scenario) pair, columns are
    gen_uid, scenario, HR_1..HR_24. Values rounded to 6 decimal places.

    Args:
        results: List of ScenarioMultiplierResult.
        dest_path: Path to the output CSV file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid", "scenario"] + _HOUR_COLUMNS)

        for res in results:
            n_scenarios = res.multipliers.shape[0]
            for s in range(n_scenarios):
                row = [res.gen_uid, s + 1] + [f"{v:.6f}" for v in res.multipliers[s]]
                writer.writerow(row)


def write_diagnostics_json(
    diagnostics: ScenarioDiagnostics,
    dest_path: Path,
) -> None:
    """Write scenario diagnostics to a JSON file.

    Args:
        diagnostics: ScenarioDiagnostics to serialize.
        dest_path: Path to the output JSON file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    data = _to_serializable(diagnostics)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


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


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
    *,
    config: ScenarioConfig | None = None,
    networks: list[NetworkId] | None = None,
) -> list[ScenarioGenerationOutput]:
    """Entry point: generate correlated scenario multipliers.

    Loads Student-t params (D1), correlation matrices (D2), and forecast
    profiles (D3), then generates correlated scenario multipliers for
    each network and resource type.

    Args:
        timeseries_base_dir: Base directory for input/output. Defaults
            to <repo_root>/data/timeseries/.
        config: Scenario generation configuration.
        networks: List of networks to process. Defaults to TINY and SMALL.

    Returns:
        List of ScenarioGenerationOutput, one per network.
    """
    if timeseries_base_dir is None:
        timeseries_base_dir = Path(__file__).resolve().parent.parent / "timeseries"

    if config is None:
        config = ScenarioConfig()

    if networks is None:
        networks = list(NetworkId)

    # Load Student-t params from D1
    student_t_path = timeseries_base_dir / "ACTIVSg2000" / "scenarios" / "student_t_params.json"
    student_t_params = load_student_t_json(student_t_path)

    # Load correlation matrix from D2
    corr_path = timeseries_base_dir / "scenarios" / "rank_correlation_matrix.json"

    outputs: list[ScenarioGenerationOutput] = []

    for network_id in networks:
        network_dir = timeseries_base_dir / network_id.value
        seed = config.master_seed + SCENARIO_SEED_OFFSETS[network_id]
        rng = np.random.Generator(np.random.PCG64(seed))

        # Load correlation matrix for this network
        corr_matrix, corr_gen_ids = load_correlation_matrix(corr_path, network_id)

        all_results: list[ScenarioMultiplierResult] = []
        all_diags: list[ScenarioDiagnostics] = []

        for resource_type in ResourceType:
            # Load forecast profiles from D3
            forecast_csv = network_dir / f"{resource_type.value}_forecast_24h.csv"
            if not forecast_csv.exists():
                logger.warning("Forecast CSV not found: %s, skipping", forecast_csv)
                continue

            forecast_profiles = load_actual_profiles(forecast_csv, resource_type)

            # Load actual profiles for night hour classification
            actual_csv = network_dir / f"{resource_type.value}_actual_24h.csv"
            if actual_csv.exists():
                actual_profiles = load_actual_profiles(actual_csv, resource_type)
                if resource_type == ResourceType.SOLAR:
                    night_hours = sorted(
                        h for h in range(24) if sum(p.values[h] for p in actual_profiles) == 0.0
                    )
                else:
                    night_hours = []
            else:
                night_hours = []

            # Build generator scenario inputs
            inputs = [
                GeneratorScenarioInput(
                    gen_uid=fp.gen_uid,
                    resource_type=resource_type,
                    pmax=fp.pmax,
                    forecast_values=fp.values,
                    night_hours=night_hours,
                )
                for fp in forecast_profiles
            ]

            if not inputs:
                continue

            # Extract sub-correlation matrix for this resource type's generators
            # Match generator IDs between correlation matrix and forecast profiles
            gen_indices = []
            for inp in inputs:
                # Try to find matching generator in correlation matrix (exact match)
                matched = False
                for idx, cid in enumerate(corr_gen_ids):
                    if inp.gen_uid == cid:
                        gen_indices.append(idx)
                        matched = True
                        break
                if not matched:
                    # Use identity correlation for unmatched generators
                    gen_indices.append(-1)

            # Build sub-correlation matrix
            n_inputs = len(inputs)
            if all(idx >= 0 for idx in gen_indices):
                sub_corr = corr_matrix[np.ix_(gen_indices, gen_indices)]
            else:
                # Fallback: use identity if some generators don't match
                sub_corr = np.eye(n_inputs)

            results, diagnostics = generate_scenarios_resource(
                inputs, student_t_params, sub_corr, config, rng
            )

            # Fix the network_id in diagnostics
            diagnostics = ScenarioDiagnostics(
                network_id=network_id,
                n_generators=diagnostics.n_generators,
                n_scenarios=diagnostics.n_scenarios,
                n_hours=diagnostics.n_hours,
                clamping=diagnostics.clamping,
                correlation=diagnostics.correlation,
                marginals=diagnostics.marginals,
            )

            all_results.extend(results)
            all_diags.append(diagnostics)

        # Write output CSVs
        scenarios_dir = network_dir / "scenarios"
        write_scenario_csv(all_results, scenarios_dir / "scenario_multipliers.csv")

        # Write diagnostics
        if all_diags:
            write_diagnostics_json(all_diags[0], scenarios_dir / "scenario_diagnostics.json")

        # Aggregate diagnostics
        if all_diags:
            total_lower = sum(d.clamping.n_clamped_lower for d in all_diags)
            total_upper = sum(d.clamping.n_clamped_upper for d in all_diags)
            total_gens = sum(d.n_generators for d in all_diags)
            total_vals = sum(d.n_generators * d.n_scenarios * d.n_hours for d in all_diags)
            agg_clamping = ClampingDiagnostics(
                n_clamped_lower=total_lower,
                n_clamped_upper=total_upper,
                fraction_clamped=(total_lower + total_upper) / total_vals if total_vals else 0.0,
            )
            agg_diag = ScenarioDiagnostics(
                network_id=network_id,
                n_generators=total_gens,
                n_scenarios=config.n_scenarios,
                n_hours=24,
                clamping=agg_clamping,
                correlation=all_diags[0].correlation,
                marginals=[m for d in all_diags for m in d.marginals],
            )
        else:
            agg_diag = ScenarioDiagnostics(
                network_id=network_id,
                n_generators=0,
                n_scenarios=config.n_scenarios,
                n_hours=24,
                clamping=ClampingDiagnostics(0, 0, 0.0),
                correlation=None,
                marginals=[],
            )

        output = ScenarioGenerationOutput(
            network_id=network_id,
            results=all_results,
            diagnostics=agg_diag,
            config=config,
            script_version=__version__,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        outputs.append(output)

        logger.info(
            "Generated %d scenario multipliers for %s (%d generators)",
            config.n_scenarios,
            network_id.value,
            len(all_results),
        )

    return outputs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
