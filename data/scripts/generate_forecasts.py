"""Forecast Generation from Actuals for renewable generation profiles.

Generates day-ahead forecast profiles from actual generation profiles for each
network (TINY, SMALL, MEDIUM) and resource type (wind, solar). The forecast
pipeline smooths the actual profile (centered moving average), adds systematic
bias, and injects calibrated Student-t noise to produce realistic forecast/actual
pairs with heavy-tailed error distributions.

Consumes fitted Student-t parameters from PRD-01 (fit_student_t.py) and actual
profiles from Phase 1 D5 / Phase 2b.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

import numpy as np

from scripts.fit_student_t import (
    ResourceType,
    StudentTParams,
    load_student_t_json,
)

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Network identifiers for forecast generation."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


@dataclass(frozen=True)
class ForecastConfig:
    """Configuration parameters for the forecast generation pipeline.

    Controls the smoothing kernel width, systematic bias per resource type,
    noise scaling, and RNG seed. All bias values are expressed as fractions
    of Pmax (e.g., 0.02 = +2% of capacity).
    """

    smoothing_window: int = 3
    wind_bias_fraction: float = 0.02
    solar_bias_fraction: float = -0.01
    master_seed: int = 42
    noise_scale_factor: float = 1.0


NETWORK_SEED_OFFSETS: dict[NetworkId, int] = {
    NetworkId.TINY: 0,
    NetworkId.SMALL: 1,
    NetworkId.MEDIUM: 2,
}


@dataclass(frozen=True)
class GeneratorProfile:
    """24-hour actual or forecast profile for a single generator.

    Values are in MW, indexed HR_1 through HR_24 (hour-ending convention).
    HR_k corresponds to array index k-1.
    """

    gen_uid: str
    resource_type: ResourceType
    pmax: float
    values: np.ndarray  # shape (24,)


@dataclass(frozen=True)
class NetworkActuals:
    """Loaded actual profiles for one network and one resource type."""

    network_id: NetworkId
    resource_type: ResourceType
    generators: list[GeneratorProfile]
    night_hours: list[int]
    source_path: Path


@dataclass(frozen=True)
class ForecastResult:
    """Generated forecast profiles for one network and one resource type."""

    network_id: NetworkId
    resource_type: ResourceType
    forecast_profiles: list[GeneratorProfile]
    actual_profiles: list[GeneratorProfile]
    config: ForecastConfig
    seed_used: int
    night_hours: list[int]


@dataclass(frozen=True)
class ForecastGenerationOutput:
    """Top-level container for all forecast generation results."""

    results: list[ForecastResult]
    student_t_source: str
    script_version: str
    generated_at: str
    config: ForecastConfig
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Actual profile loading
# ---------------------------------------------------------------------------

_HOUR_COLUMNS = [f"HR_{k}" for k in range(1, 25)]


def load_actual_profiles(
    csv_path: Path,
    resource_type: ResourceType,
) -> list[GeneratorProfile]:
    """Load actual generation profiles from a canonical CSV file.

    Reads a wind_actual_24h.csv or solar_actual_24h.csv file in the
    canonical format: one row per generator, columns gen_uid plus
    HR_1 through HR_24. Constructs a GeneratorProfile per row with
    pmax set to the maximum observed value across the 24 hours.

    Args:
        csv_path: Path to the canonical actual CSV file.
        resource_type: WIND or SOLAR.

    Returns:
        A list of GeneratorProfile, one per row in the CSV.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If the CSV does not contain gen_uid and HR_1..HR_24 columns.
    """
    if not csv_path.exists():
        msg = f"Actual CSV not found: {csv_path}"
        raise FileNotFoundError(msg)

    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []

        # Validate required columns
        if "gen_uid" not in headers:
            msg = f"Missing 'gen_uid' column in {csv_path}"
            raise ValueError(msg)

        for col in _HOUR_COLUMNS:
            if col not in headers:
                msg = f"Missing '{col}' column in {csv_path}"
                raise ValueError(msg)

        profiles: list[GeneratorProfile] = []
        for row in reader:
            gen_uid = row["gen_uid"]
            values = np.array([float(row[col]) for col in _HOUR_COLUMNS])
            pmax = float(np.max(values)) if np.any(values > 0) else 0.0
            profiles.append(
                GeneratorProfile(
                    gen_uid=gen_uid,
                    resource_type=resource_type,
                    pmax=pmax,
                    values=values,
                )
            )

    return profiles


def _classify_night_hours_from_profiles(
    generators: list[GeneratorProfile],
) -> list[int]:
    """Identify nighttime hours from loaded solar generator profiles.

    Hours where aggregate solar generation across all generators is zero
    are classified as nighttime.

    Returns:
        A sorted list of hour-of-day integers (0-23).
    """
    hour_totals = np.zeros(24)
    for gen in generators:
        hour_totals += gen.values
    return sorted(h for h in range(24) if hour_totals[h] == 0.0)


def load_network_actuals(
    network_dir: Path,
    network_id: NetworkId,
    resource_type: ResourceType,
) -> NetworkActuals:
    """Load actual profiles and classify night hours for one network.

    Args:
        network_dir: Path to the network's timeseries directory.
        network_id: Which network is being loaded.
        resource_type: WIND or SOLAR.

    Returns:
        A NetworkActuals with generator profiles and night-hour classification.

    Raises:
        FileNotFoundError: If the expected actual CSV does not exist.
    """
    csv_name = f"{resource_type.value}_actual_24h.csv"
    csv_path = network_dir / csv_name

    generators = load_actual_profiles(csv_path, resource_type)

    if resource_type == ResourceType.SOLAR:
        night_hours = _classify_night_hours_from_profiles(generators)
    else:
        night_hours = []

    return NetworkActuals(
        network_id=network_id,
        resource_type=resource_type,
        generators=generators,
        night_hours=night_hours,
        source_path=csv_path,
    )


# ---------------------------------------------------------------------------
# Smoothing
# ---------------------------------------------------------------------------


def smooth_profile(
    values: np.ndarray,
    window: int,
) -> np.ndarray:
    """Apply a centered moving-average smoothing kernel to a 24-hour profile.

    At edges, the window narrows symmetrically (partial windows) rather
    than padding with zeros or wrapping around. A window of 1 returns the
    input unchanged.

    Args:
        values: 1-D array of length 24 (MW values for HR_1..HR_24).
        window: Width of the centered moving-average kernel. Must be >= 1.

    Returns:
        A 1-D array of length 24 with smoothed values.

    Raises:
        ValueError: If values does not have length 24 or window < 1.
    """
    if len(values) != 24:
        msg = f"values must have length 24, got {len(values)}"
        raise ValueError(msg)
    if window < 1:
        msg = f"window must be >= 1, got {window}"
        raise ValueError(msg)
    if window == 1:
        return values.copy()

    half = (window - 1) // 2
    n = len(values)
    smoothed = np.empty(n)

    for i in range(n):
        lo = max(0, i - half)
        hi = min(n - 1, i + half)
        smoothed[i] = np.mean(values[lo : hi + 1])

    return smoothed


# ---------------------------------------------------------------------------
# Bias injection
# ---------------------------------------------------------------------------


def add_bias(
    smoothed: np.ndarray,
    pmax: float,
    bias_fraction: float,
) -> np.ndarray:
    """Add systematic bias to a smoothed profile.

    Adds a constant offset equal to bias_fraction * pmax to every hour.

    Args:
        smoothed: 1-D array of length 24 (smoothed MW values).
        pmax: Generator nameplate capacity in MW.
        bias_fraction: Bias as a fraction of pmax.

    Returns:
        A 1-D array of length 24 with bias added.
    """
    return smoothed + bias_fraction * pmax


# ---------------------------------------------------------------------------
# Noise injection
# ---------------------------------------------------------------------------


def inject_noise(
    biased: np.ndarray,
    actual: np.ndarray,
    student_t_params: StudentTParams,
    resource_type: ResourceType,
    rng: np.random.Generator,
    *,
    noise_scale_factor: float = 1.0,
) -> np.ndarray:
    """Inject Student-t noise into a biased profile.

    For each hour h, draws noise from t(df_h, loc_h, scale_h) scaled by
    the actual generation level: noise[h] = sample * actual[h] * noise_scale_factor.

    When actual[h] is zero, noise is zero regardless of the drawn sample.

    Args:
        biased: 1-D array of length 24 (smoothed + biased MW values).
        actual: 1-D array of length 24 (original actual MW values).
        student_t_params: Fitted Student-t parameters from D1.
        resource_type: WIND or SOLAR.
        rng: Seeded numpy random Generator.
        noise_scale_factor: Multiplier on the noise magnitude.

    Returns:
        A 1-D array of length 24 with noise added.
    """
    resource_fit = (
        student_t_params.wind if resource_type == ResourceType.WIND else student_t_params.solar
    )

    result = biased.copy()
    for h in range(24):
        hour_fit = resource_fit.per_hour[h]

        # Skip if actual is zero (no noise needed) or scale is zero (nighttime sentinel)
        if actual[h] == 0.0 or hour_fit.scale == 0.0:
            continue

        # Draw from standard t with fitted df, then apply loc and scale manually
        df = hour_fit.df
        loc = hour_fit.loc
        scale = hour_fit.scale

        if math.isinf(df):
            # Infinite df means normal distribution (sentinel for nighttime)
            continue

        raw_sample = rng.standard_t(df)
        t_sample = loc + scale * raw_sample

        result[h] += t_sample * actual[h] * noise_scale_factor

    return result


# ---------------------------------------------------------------------------
# Clamping and night zeroing
# ---------------------------------------------------------------------------


def clamp_forecast(
    forecast: np.ndarray,
    pmax: float,
) -> np.ndarray:
    """Clamp forecast values to [0, Pmax].

    Args:
        forecast: 1-D array of length 24.
        pmax: Generator nameplate capacity in MW. Must be >= 0.

    Returns:
        A 1-D array of length 24 with values clamped to [0, pmax].
    """
    return np.clip(forecast, 0.0, pmax)


def zero_night_hours(
    forecast: np.ndarray,
    night_hours: list[int],
) -> np.ndarray:
    """Force forecast values to zero during nighttime hours.

    Args:
        forecast: 1-D array of length 24.
        night_hours: List of hour-of-day integers (0-23) classified as nighttime.

    Returns:
        A 1-D array of length 24 with night hours zeroed.
    """
    result = forecast.copy()
    for h in night_hours:
        result[h] = 0.0
    return result


# ---------------------------------------------------------------------------
# Per-generator forecast pipeline
# ---------------------------------------------------------------------------


def generate_forecast_single(
    actual_profile: GeneratorProfile,
    student_t_params: StudentTParams,
    config: ForecastConfig,
    night_hours: list[int],
    rng: np.random.Generator,
) -> GeneratorProfile:
    """Generate a forecast profile for a single generator.

    Applies: smooth -> bias -> noise -> clamp -> zero nights.

    If pmax == 0, returns a zero forecast without noise injection.

    Args:
        actual_profile: The generator's 24-hour actual profile.
        student_t_params: Fitted Student-t parameters from D1.
        config: Forecast generation configuration.
        night_hours: Hours to zero for solar (empty for wind).
        rng: Seeded numpy random Generator.

    Returns:
        A GeneratorProfile with the generated forecast values.
    """
    if actual_profile.pmax == 0.0:
        return GeneratorProfile(
            gen_uid=actual_profile.gen_uid,
            resource_type=actual_profile.resource_type,
            pmax=actual_profile.pmax,
            values=np.zeros(24),
        )

    # Step 1: Smooth
    smoothed = smooth_profile(actual_profile.values, config.smoothing_window)

    # Step 2: Bias
    bias_fraction = (
        config.wind_bias_fraction
        if actual_profile.resource_type == ResourceType.WIND
        else config.solar_bias_fraction
    )
    biased = add_bias(smoothed, actual_profile.pmax, bias_fraction)

    # Step 3: Noise
    noisy = inject_noise(
        biased,
        actual_profile.values,
        student_t_params,
        actual_profile.resource_type,
        rng,
        noise_scale_factor=config.noise_scale_factor,
    )

    # Step 4: Clamp
    clamped = clamp_forecast(noisy, actual_profile.pmax)

    # Step 5: Zero night hours
    final = zero_night_hours(clamped, night_hours)

    return GeneratorProfile(
        gen_uid=actual_profile.gen_uid,
        resource_type=actual_profile.resource_type,
        pmax=actual_profile.pmax,
        values=final,
    )


# ---------------------------------------------------------------------------
# Per-network forecast pipeline
# ---------------------------------------------------------------------------


def generate_forecasts_network(
    network_actuals: NetworkActuals,
    student_t_params: StudentTParams,
    config: ForecastConfig,
) -> ForecastResult:
    """Generate forecast profiles for all generators in one network.

    Creates a per-network seeded RNG from master_seed + network offset.

    Args:
        network_actuals: Loaded actual profiles for one network/resource type.
        student_t_params: Fitted Student-t parameters from D1.
        config: Forecast generation configuration.

    Returns:
        A ForecastResult with forecast and actual profiles.
    """
    offset = NETWORK_SEED_OFFSETS[network_actuals.network_id]
    seed = config.master_seed + offset
    rng = np.random.Generator(np.random.PCG64(seed))

    forecast_profiles: list[GeneratorProfile] = []
    for gen in network_actuals.generators:
        forecast = generate_forecast_single(
            gen, student_t_params, config, network_actuals.night_hours, rng
        )
        forecast_profiles.append(forecast)

    return ForecastResult(
        network_id=network_actuals.network_id,
        resource_type=network_actuals.resource_type,
        forecast_profiles=forecast_profiles,
        actual_profiles=list(network_actuals.generators),
        config=config,
        seed_used=seed,
        night_hours=network_actuals.night_hours,
    )


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def write_forecast_csv(
    profiles: list[GeneratorProfile],
    dest_path: Path,
) -> None:
    """Write generator profiles to a canonical CSV file.

    One row per generator, columns gen_uid, HR_1..HR_24. Values rounded
    to 4 decimal places.

    Args:
        profiles: List of GeneratorProfile to write.
        dest_path: Path to the output CSV file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gen_uid"] + _HOUR_COLUMNS)

        for prof in profiles:
            row = [prof.gen_uid] + [f"{v:.4f}" for v in prof.values]
            writer.writerow(row)


def write_forecast_result(
    result: ForecastResult,
    network_dir: Path,
) -> None:
    """Write a ForecastResult to canonical forecast and actual CSVs.

    Writes two files:
    - <resource_type>_forecast_24h.csv
    - <resource_type>_actual_24h.csv

    Args:
        result: The forecast result to write.
        network_dir: Path to the network's timeseries directory.
    """
    rt = result.resource_type.value
    write_forecast_csv(result.forecast_profiles, network_dir / f"{rt}_forecast_24h.csv")
    write_forecast_csv(result.actual_profiles, network_dir / f"{rt}_actual_24h.csv")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
    *,
    config: ForecastConfig | None = None,
    networks: list[NetworkId] | None = None,
) -> ForecastGenerationOutput:
    """Entry point: generate forecasts for all networks and resource types.

    Args:
        timeseries_base_dir: Base directory for input/output. Defaults
            to <repo_root>/data/timeseries/.
        config: Forecast generation configuration.
        networks: List of networks to process. Defaults to all three.

    Returns:
        The complete ForecastGenerationOutput.
    """
    if timeseries_base_dir is None:
        timeseries_base_dir = Path(__file__).resolve().parent.parent / "timeseries"

    if config is None:
        config = ForecastConfig()

    if networks is None:
        networks = list(NetworkId)

    # Load Student-t params from D1
    student_t_path = timeseries_base_dir / "ACTIVSg2000" / "scenarios" / "student_t_params.json"
    student_t_params = load_student_t_json(student_t_path)

    results: list[ForecastResult] = []

    for network_id in networks:
        network_dir = timeseries_base_dir / network_id.value

        for resource_type in ResourceType:
            actuals = load_network_actuals(network_dir, network_id, resource_type)
            result = generate_forecasts_network(actuals, student_t_params, config)
            write_forecast_result(result, network_dir)
            results.append(result)

    return ForecastGenerationOutput(
        results=results,
        student_t_source=str(student_t_path),
        script_version=__version__,
        generated_at=datetime.now(timezone.utc).isoformat(),
        config=config,
    )


if __name__ == "__main__":
    main()
