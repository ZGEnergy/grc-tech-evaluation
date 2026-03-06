"""Student-t Distribution Fitting for ACTIVSg renewable generation variability.

Fits Student-t distributions to the hour-over-hour changes in ACTIVSg companion
renewable generation profiles. Outputs per-generator-type, per-hour-of-day
df/loc/scale parameters plus pooled (all-hours) parameters and KS goodness-of-fit
diagnostics.

Uses scipy.stats.t.fit() for MLE and scipy.stats.kstest for validation.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

import numpy as np
from scipy import stats

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ResourceType(StrEnum):
    """Renewable resource types for separate distribution fitting."""

    WIND = "wind"
    SOLAR = "solar"


class HourClassification(StrEnum):
    """Classification of an hour-of-day for solar fitting purposes."""

    DAYTIME = "daytime"
    NIGHTTIME = "nighttime"


@dataclass(frozen=True)
class HourFitResult:
    """Fitted Student-t parameters and diagnostics for one hour-of-day.

    For nighttime solar hours, df is set to float('inf'), loc and scale
    to 0.0, and ks_pvalue to 1.0, indicating no variability and no fit
    attempted. The is_fitted flag distinguishes actual fits from sentinel
    entries.
    """

    hour: int  # 0-23, hour-of-day
    classification: HourClassification  # daytime or nighttime (solar only; always daytime for wind)
    is_fitted: bool  # False for nighttime solar hours (sentinel values)
    df: float  # Student-t degrees of freedom
    loc: float  # Student-t location parameter
    scale: float  # Student-t scale parameter
    ks_statistic: float  # Kolmogorov-Smirnov test statistic
    ks_pvalue: float  # KS test p-value
    sample_size: int  # number of change values used in fitting
    ks_rejected_at_05: bool  # True if p-value < 0.05


@dataclass(frozen=True)
class PooledFitResult:
    """Fitted Student-t parameters from all hours pooled together.

    Provides a single df/loc/scale estimate per resource type for
    downstream consumers that prefer a global parameter over per-hour.
    For solar, nighttime hours are excluded from the pooled sample.
    """

    df: float
    loc: float
    scale: float
    ks_statistic: float
    ks_pvalue: float
    sample_size: int
    ks_rejected_at_05: bool
    hours_excluded: list[int]  # nighttime hours excluded from pooling (solar only)


@dataclass(frozen=True)
class ResourceFitResult:
    """Complete fitting results for one resource type (wind or solar)."""

    resource_type: ResourceType
    per_hour: list[HourFitResult]  # exactly 24 entries, indexed by hour-of-day
    pooled: PooledFitResult
    night_hours: list[int]  # hours classified as nighttime (empty for wind)
    total_generators_pooled: int  # number of generators in the pooled sample
    total_days_in_source: int  # number of days in the full-year source data (365)


@dataclass(frozen=True)
class StudentTParams:
    """Top-level container for all Student-t fitting results.

    Serialized to JSON as the output artifact.
    """

    network_source: str  # "ACTIVSg2000" -- the network used for fitting
    wind: ResourceFitResult
    solar: ResourceFitResult
    representative_day_date: str  # ISO 8601 date used for night-hour classification
    script_version: str
    generated_at: str  # ISO 8601 timestamp
    fitting_method: str  # "scipy.stats.t.fit MLE"
    validation_method: str  # "scipy.stats.kstest two-sided"
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Change series computation
# ---------------------------------------------------------------------------

HOURS_PER_YEAR = 8760


def compute_hourly_changes(
    generation: np.ndarray,
) -> np.ndarray:
    """Compute hour-over-hour generation changes from a full-year profile.

    For a (8760, N_gens) array, computes the first difference along the
    time axis: changes[h] = generation[h] - generation[h-1] for
    h = 1..8759. The result has shape (8759, N_gens).

    Day boundaries are not treated specially -- the change from the last
    hour of day d to the first hour of day d+1 is included.

    Args:
        generation: Array of shape (8760, N_gens), hourly generation
            values in MW.

    Returns:
        Array of shape (8759, N_gens), hour-over-hour changes in MW.

    Raises:
        ValueError: If generation does not have exactly 8760 rows.
    """
    if generation.ndim == 1:
        generation = generation.reshape(-1, 1)

    if generation.shape[0] != HOURS_PER_YEAR:
        msg = f"generation must have {HOURS_PER_YEAR} rows, got {generation.shape[0]}"
        raise ValueError(msg)

    return np.diff(generation, axis=0)


def pool_changes_by_hour(
    changes: np.ndarray,
) -> dict[int, np.ndarray]:
    """Group hourly changes by hour-of-day and pool across generators.

    Given a (8759, N_gens) change array, assigns each row to an
    hour-of-day (0-23) based on its position in the year. The change
    at index i corresponds to the transition *into* hour (i+1) % 24.

    The hour assignment for change index i is: hour = (i + 1) % 24.

    Args:
        changes: Array of shape (8759, N_gens).

    Returns:
        A dict mapping hour-of-day (0-23) to a 1-D numpy array of
        pooled change values.
    """
    if changes.ndim == 1:
        changes = changes.reshape(-1, 1)

    n_changes = changes.shape[0]
    result: dict[int, np.ndarray] = {}

    # Compute hour assignments for all change indices
    hours = np.array([(i + 1) % 24 for i in range(n_changes)])

    for h in range(24):
        mask = hours == h
        hour_changes = changes[mask]  # (N_days_for_hour, N_gens)
        result[h] = hour_changes.ravel()

    return result


# ---------------------------------------------------------------------------
# Night-hour classification
# ---------------------------------------------------------------------------


def classify_night_hours(
    solar_actual_24h_path: Path,
) -> list[int]:
    """Identify nighttime hours from the representative day's solar profile.

    Reads the representative day's canonical solar CSV (produced by
    Phase 1 D5) and identifies hours where aggregate solar generation
    across all generators is zero. These hours are classified as night.

    The solar CSV follows the canonical format: rows are generators,
    columns are HR_1 through HR_24 (hour-ending convention). HR_k
    maps to hour-of-day k-1 (HR_1 = hour 0, HR_24 = hour 23).

    Args:
        solar_actual_24h_path: Path to the representative day's
            ``solar_actual_24h.csv`` file in canonical format.

    Returns:
        A sorted list of hour-of-day integers (0-23) classified as
        nighttime.

    Raises:
        FileNotFoundError: If solar_actual_24h_path does not exist.
        ValueError: If the CSV does not contain HR_1 through HR_24 columns.
    """
    if not solar_actual_24h_path.exists():
        msg = f"Solar actual CSV not found: {solar_actual_24h_path}"
        raise FileNotFoundError(msg)

    with open(solar_actual_24h_path, newline="") as fh:
        reader = csv.reader(fh)
        headers = next(reader)

        # Validate HR_1 through HR_24 columns exist
        hr_cols: dict[int, int] = {}  # hour-of-day -> column index
        for col_idx, col_name in enumerate(headers):
            col_stripped = col_name.strip()
            if col_stripped.startswith("HR_"):
                try:
                    hr_num = int(col_stripped[3:])
                    if 1 <= hr_num <= 24:
                        hr_cols[hr_num - 1] = col_idx  # HR_k -> hour k-1
                except ValueError:
                    continue

        if len(hr_cols) != 24:
            msg = (
                f"Expected HR_1 through HR_24 columns, "
                f"found {len(hr_cols)} HR columns in {solar_actual_24h_path}"
            )
            raise ValueError(msg)

        # Sum generation across all generators for each hour
        hour_totals = np.zeros(24)
        for row in reader:
            for hour, col_idx in hr_cols.items():
                val_str = row[col_idx].strip()
                try:
                    hour_totals[hour] += float(val_str)
                except ValueError:
                    pass

    # Hours with zero aggregate generation are nighttime
    night_hours = sorted(h for h in range(24) if hour_totals[h] == 0.0)
    return night_hours


# ---------------------------------------------------------------------------
# Distribution fitting
# ---------------------------------------------------------------------------

_MIN_SAMPLE_SIZE = 10


def fit_student_t_single(
    sample: np.ndarray,
) -> tuple[float, float, float]:
    """Fit a Student-t distribution to a 1-D sample via MLE.

    Uses scipy.stats.t.fit() to estimate the three parameters
    (df, loc, scale) by maximum likelihood.

    Args:
        sample: 1-D array of change values. Must have at least 10
            observations for a meaningful fit.

    Returns:
        A tuple of (df, loc, scale).

    Raises:
        ValueError: If sample has fewer than 10 observations.
        RuntimeError: If the MLE optimizer fails to converge.
    """
    if len(sample) < _MIN_SAMPLE_SIZE:
        msg = f"Sample has {len(sample)} observations, need at least {_MIN_SAMPLE_SIZE}"
        raise ValueError(msg)

    try:
        df, loc, scale = stats.t.fit(sample)
    except Exception as exc:
        msg = f"MLE optimizer failed: {exc}"
        raise RuntimeError(msg) from exc

    return float(df), float(loc), float(scale)


def validate_fit_ks(
    sample: np.ndarray,
    df: float,
    loc: float,
    scale: float,
) -> tuple[float, float]:
    """Validate a Student-t fit using the Kolmogorov-Smirnov test.

    Performs a two-sided KS test comparing the empirical distribution
    of the sample against the fitted Student-t CDF.

    Args:
        sample: 1-D array of change values (same sample used for fitting).
        df: Fitted degrees of freedom.
        loc: Fitted location parameter.
        scale: Fitted scale parameter.

    Returns:
        A tuple of (ks_statistic, p_value).
    """
    ks_stat, p_value = stats.kstest(sample, "t", args=(df, loc, scale))
    return float(ks_stat), float(p_value)


def fit_resource_type(
    changes: np.ndarray,
    night_hours: list[int],
    resource_type: ResourceType,
    total_generators: int,
) -> ResourceFitResult:
    """Fit Student-t distributions for one resource type across all hours.

    For each hour-of-day (0-23):
    - If the hour is in night_hours (solar only), record sentinel
      parameters (df=inf, loc=0, scale=0) without fitting.
    - Otherwise, pool the change values for that hour across all
      generators, fit a Student-t via fit_student_t_single, and
      validate via validate_fit_ks.

    Also computes the pooled (all daytime hours) fit.

    Args:
        changes: Array of shape (8759, N_gens), hour-over-hour changes.
        night_hours: List of hour-of-day integers to exclude (solar only;
            empty list for wind).
        resource_type: WIND or SOLAR.
        total_generators: Number of generators in the change array.

    Returns:
        A ResourceFitResult with per-hour and pooled fitting results.
    """
    pooled_by_hour = pool_changes_by_hour(changes)

    per_hour_results: list[HourFitResult] = []
    pooled_samples: list[np.ndarray] = []

    for h in range(24):
        if h in night_hours:
            per_hour_results.append(
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
            sample = pooled_by_hour[h]
            pooled_samples.append(sample)

            df, loc, scale = fit_student_t_single(sample)
            ks_stat, ks_pval = validate_fit_ks(sample, df, loc, scale)

            per_hour_results.append(
                HourFitResult(
                    hour=h,
                    classification=HourClassification.DAYTIME,
                    is_fitted=True,
                    df=df,
                    loc=loc,
                    scale=scale,
                    ks_statistic=ks_stat,
                    ks_pvalue=ks_pval,
                    sample_size=len(sample),
                    ks_rejected_at_05=ks_pval < 0.05,
                )
            )

    # Pooled fit across all daytime hours
    all_daytime_changes = np.concatenate(pooled_samples)
    pooled_df, pooled_loc, pooled_scale = fit_student_t_single(all_daytime_changes)
    pooled_ks_stat, pooled_ks_pval = validate_fit_ks(
        all_daytime_changes, pooled_df, pooled_loc, pooled_scale
    )

    pooled_result = PooledFitResult(
        df=pooled_df,
        loc=pooled_loc,
        scale=pooled_scale,
        ks_statistic=pooled_ks_stat,
        ks_pvalue=pooled_ks_pval,
        sample_size=len(all_daytime_changes),
        ks_rejected_at_05=pooled_ks_pval < 0.05,
        hours_excluded=sorted(night_hours),
    )

    return ResourceFitResult(
        resource_type=resource_type,
        per_hour=per_hour_results,
        pooled=pooled_result,
        night_hours=sorted(night_hours),
        total_generators_pooled=total_generators,
        total_days_in_source=365,
    )


# ---------------------------------------------------------------------------
# Output serialization
# ---------------------------------------------------------------------------


def build_student_t_params(
    wind_result: ResourceFitResult,
    solar_result: ResourceFitResult,
    representative_day_date: str,
    *,
    script_version: str = "0.1.0",
) -> StudentTParams:
    """Assemble the top-level StudentTParams output container.

    Args:
        wind_result: Fitting results for wind.
        solar_result: Fitting results for solar.
        representative_day_date: ISO 8601 date string of the
            representative day used for night-hour classification.
        script_version: Version string for the fitting script.

    Returns:
        A StudentTParams with all fitting results and metadata.
    """
    return StudentTParams(
        network_source="ACTIVSg2000",
        wind=wind_result,
        solar=solar_result,
        representative_day_date=representative_day_date,
        script_version=script_version,
        generated_at=datetime.now(timezone.utc).isoformat(),
        fitting_method="scipy.stats.t.fit MLE",
        validation_method="scipy.stats.kstest two-sided",
    )


def _round_floats(obj: object, decimals: int = 6) -> object:
    """Recursively round float values in a nested dict/list structure.

    Handles the special case of infinity (preserved as-is).
    """
    if isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return obj
        return round(obj, decimals)
    if isinstance(obj, dict):
        return {k: _round_floats(v, decimals) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(item, decimals) for item in obj]
    return obj


class _InfinityEncoder(json.JSONEncoder):
    """JSON encoder that serializes float('inf') as the string "Infinity"."""

    def default(self, o: object) -> object:
        if isinstance(o, StrEnum):
            return o.value
        return super().default(o)

    def encode(self, o: object) -> str:
        # Let the parent encode, then we handle inf in iterencode
        return super().encode(o)

    def iterencode(self, o: object, _one_shot: bool = False) -> str:  # type: ignore[override]
        """Override to handle inf/nan in nested structures."""
        # Pre-process the object to replace inf with "Infinity" string
        processed = self._process_infinity(o)
        return super().iterencode(processed, _one_shot)

    def _process_infinity(self, obj: object) -> object:
        if isinstance(obj, float):
            if math.isinf(obj):
                return "Infinity" if obj > 0 else "-Infinity"
            if math.isnan(obj):
                return "NaN"
            return obj
        if isinstance(obj, dict):
            return {k: self._process_infinity(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._process_infinity(item) for item in obj]
        if isinstance(obj, StrEnum):
            return obj.value
        return obj


def write_student_t_json(
    params: StudentTParams,
    dest_path: Path,
) -> None:
    """Serialize StudentTParams to a human-readable JSON file.

    Writes indented JSON with snake_case keys matching the dataclass
    field names. Float values are rounded to 6 decimal places. The
    special float value inf is serialized as the string "Infinity".

    Args:
        params: The fitting results to serialize.
        dest_path: Path to write the JSON file. Parent directory is
            created if it does not exist.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(params)
    data = _round_floats(data)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2, cls=_InfinityEncoder)
        fh.write("\n")


def _restore_infinity(obj: object) -> object:
    """Recursively restore "Infinity" strings to float('inf')."""
    if isinstance(obj, str):
        if obj == "Infinity":
            return float("inf")
        if obj == "-Infinity":
            return float("-inf")
        if obj == "NaN":
            return float("nan")
        return obj
    if isinstance(obj, dict):
        return {k: _restore_infinity(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_restore_infinity(item) for item in obj]
    return obj


def load_student_t_json(
    src_path: Path,
) -> StudentTParams:
    """Deserialize StudentTParams from a JSON file.

    Reads the JSON file produced by write_student_t_json and
    reconstructs the StudentTParams dataclass hierarchy.

    Args:
        src_path: Path to the student_t_params.json file.

    Returns:
        A StudentTParams with all fitting results.

    Raises:
        FileNotFoundError: If src_path does not exist.
        ValueError: If the JSON structure does not match the expected schema.
    """
    if not src_path.exists():
        msg = f"Student-t params file not found: {src_path}"
        raise FileNotFoundError(msg)

    with open(src_path) as fh:
        raw = json.load(fh)

    raw = _restore_infinity(raw)

    try:
        wind = _parse_resource_fit_result(raw["wind"])
        solar = _parse_resource_fit_result(raw["solar"])

        return StudentTParams(
            network_source=raw["network_source"],
            wind=wind,
            solar=solar,
            representative_day_date=raw["representative_day_date"],
            script_version=raw["script_version"],
            generated_at=raw["generated_at"],
            fitting_method=raw["fitting_method"],
            validation_method=raw["validation_method"],
            notes=raw.get("notes", []),
        )
    except (KeyError, TypeError) as exc:
        msg = f"Invalid Student-t params JSON structure: {exc}"
        raise ValueError(msg) from exc


def _parse_resource_fit_result(data: dict) -> ResourceFitResult:
    """Parse a ResourceFitResult from a dict."""
    per_hour = [_parse_hour_fit_result(h) for h in data["per_hour"]]
    pooled = _parse_pooled_fit_result(data["pooled"])

    return ResourceFitResult(
        resource_type=ResourceType(data["resource_type"]),
        per_hour=per_hour,
        pooled=pooled,
        night_hours=data["night_hours"],
        total_generators_pooled=data["total_generators_pooled"],
        total_days_in_source=data["total_days_in_source"],
    )


def _parse_hour_fit_result(data: dict) -> HourFitResult:
    """Parse an HourFitResult from a dict."""
    return HourFitResult(
        hour=data["hour"],
        classification=HourClassification(data["classification"]),
        is_fitted=data["is_fitted"],
        df=float(data["df"]),
        loc=float(data["loc"]),
        scale=float(data["scale"]),
        ks_statistic=float(data["ks_statistic"]),
        ks_pvalue=float(data["ks_pvalue"]),
        sample_size=data["sample_size"],
        ks_rejected_at_05=data["ks_rejected_at_05"],
    )


def _parse_pooled_fit_result(data: dict) -> PooledFitResult:
    """Parse a PooledFitResult from a dict."""
    return PooledFitResult(
        df=float(data["df"]),
        loc=float(data["loc"]),
        scale=float(data["scale"]),
        ks_statistic=float(data["ks_statistic"]),
        ks_pvalue=float(data["ks_pvalue"]),
        sample_size=data["sample_size"],
        ks_rejected_at_05=data["ks_rejected_at_05"],
        hours_excluded=data["hours_excluded"],
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
) -> StudentTParams:
    """Entry point: fit Student-t distributions and write output JSON.

    Loads full-year wind and solar profiles for ACTIVSg2000, computes
    change series, classifies night hours from the representative day's
    solar profile, fits per-hour and pooled Student-t distributions for
    each resource type, and writes the results to
    ``<timeseries_base_dir>/ACTIVSg2000/scenarios/student_t_params.json``.

    Args:
        timeseries_base_dir: Base directory for input/output. Defaults
            to <repo_root>/data/timeseries/.

    Returns:
        The complete StudentTParams with all fitting results.

    Raises:
        FileNotFoundError: If raw companion data or representative day
            solar CSV is not found.
    """
    # Import loading functions from D5
    from scripts.select_representative_day import (
        load_full_year_solar,
        load_full_year_wind,
    )

    if timeseries_base_dir is None:
        timeseries_base_dir = Path(__file__).resolve().parent.parent / "timeseries"

    network = "ACTIVSg2000"
    raw_dir = timeseries_base_dir / network / "raw"
    solar_actual_path = timeseries_base_dir / network / "solar_actual_24h.csv"
    output_path = timeseries_base_dir / network / "scenarios" / "student_t_params.json"

    # Load full-year profiles
    wind_arr, wind_gen_ids = load_full_year_wind(raw_dir)
    solar_arr, solar_gen_ids = load_full_year_solar(raw_dir)

    # Compute change series
    wind_changes = compute_hourly_changes(wind_arr)
    solar_changes = compute_hourly_changes(solar_arr)

    # Classify night hours from the representative day's solar profile
    night_hours = classify_night_hours(solar_actual_path)

    # Read the representative day date from the selection rationale
    rationale_path = timeseries_base_dir / network / "selection_rationale.json"
    if rationale_path.exists():
        with open(rationale_path) as fh:
            rationale = json.load(fh)
        representative_day_date = rationale.get("selected_date", "unknown")
    else:
        representative_day_date = "unknown"

    # Fit distributions
    wind_result = fit_resource_type(
        wind_changes,
        night_hours=[],
        resource_type=ResourceType.WIND,
        total_generators=wind_arr.shape[1],
    )
    solar_result = fit_resource_type(
        solar_changes,
        night_hours=night_hours,
        resource_type=ResourceType.SOLAR,
        total_generators=solar_arr.shape[1],
    )

    # Build and write output
    params = build_student_t_params(
        wind_result=wind_result,
        solar_result=solar_result,
        representative_day_date=representative_day_date,
        script_version=__version__,
    )
    write_student_t_json(params, output_path)

    return params


if __name__ == "__main__":
    main()
