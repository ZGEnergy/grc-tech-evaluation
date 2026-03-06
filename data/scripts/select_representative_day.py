"""Representative Day Selection & Extraction for ACTIVSg companion time series.

Selects one or more representative 24-hour operating days from full-year ACTIVSg
companion time series and extracts the selected day's profiles into canonical CSV
format defined by D4. Applies only to ACTIVSg2000 (SMALL) and ACTIVSg10k (MEDIUM).

The selection algorithm:
1. Loads full-year companion CSVs and computes per-day summary statistics.
2. Scores each candidate day using a configurable composite metric.
3. Ranks all 365 candidate days and selects the top-scoring day.
4. Extracts the selected day's 24-hour profiles into canonical CSV files.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from enum import StrEnum
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class SelectionNetworkId(StrEnum):
    """Networks eligible for representative day selection.

    Only ACTIVSg networks have companion time series data.
    TINY (case39) is excluded -- it has no companion data.
    """

    ACTIVSG2000 = "ACTIVSg2000"
    ACTIVSG10K = "ACTIVSg10k"


@dataclass(frozen=True)
class DailySummary:
    """Per-day summary statistics computed from full-year companion data.

    All power values are in MW, energy values in MWh. The day is
    identified by its 0-based index (0 = first day in the time series,
    364 = last day) and its calendar date string.
    """

    day_index: int  # 0-based index into the year
    date_str: str  # ISO 8601 date, e.g. "2016-07-19"
    total_load_mwh: float  # sum of all bus loads across all 24 hours
    peak_load_mw: float  # maximum single-hour system load
    total_wind_mwh: float  # sum of all wind generation across all 24 hours
    total_solar_mwh: float  # sum of all solar generation across all 24 hours
    peak_wind_mw: float  # maximum single-hour aggregate wind output
    peak_solar_mw: float  # maximum single-hour aggregate solar output
    max_load_ramp_mw: float  # max abs hour-over-hour change in system load
    renewable_penetration: float  # (wind + solar MWh) / total_load_mwh
    missing_hours: int  # count of hours with any missing/NaN values
    is_weekday: bool


@dataclass(frozen=True)
class ScoringWeights:
    """Configurable weights for the composite day-selection scoring function.

    Each weight controls how much a given metric contributes to the
    composite score. All weights must be non-negative. The composite
    score is the weighted sum of normalized metric values (each metric
    normalized to [0, 1] relative to the annual min/max).

    Default weights emphasize load level and renewable diversity.
    """

    load_level: float = 0.30
    wind_generation: float = 0.20
    solar_generation: float = 0.20
    ramp_magnitude: float = 0.15
    renewable_diversity: float = 0.10
    weekday_bonus: float = 0.05


@dataclass(frozen=True)
class DayScore:
    """Composite score and per-metric breakdown for a single candidate day."""

    day_index: int
    date_str: str
    composite_score: float  # weighted sum of normalized metrics
    load_level_score: float  # normalized [0, 1]
    wind_score: float  # normalized [0, 1]
    solar_score: float  # normalized [0, 1]
    ramp_score: float  # normalized [0, 1]
    diversity_score: float  # normalized [0, 1]
    weekday_score: float  # 1.0 if weekday, 0.0 if weekend
    anomaly_penalty: float  # subtracted from composite (>= 0)


@dataclass(frozen=True)
class AnnualStatistics:
    """Annual min/mean/max for each metric, used for normalization context."""

    load_mwh_min: float
    load_mwh_mean: float
    load_mwh_max: float
    peak_load_mw_min: float
    peak_load_mw_mean: float
    peak_load_mw_max: float
    wind_mwh_min: float
    wind_mwh_mean: float
    wind_mwh_max: float
    solar_mwh_min: float
    solar_mwh_mean: float
    solar_mwh_max: float
    max_ramp_mw_min: float
    max_ramp_mw_mean: float
    max_ramp_mw_max: float
    renewable_penetration_min: float
    renewable_penetration_mean: float
    renewable_penetration_max: float


@dataclass(frozen=True)
class SelectionRationale:
    """Complete rationale for a representative day selection for one network.

    Serialized to JSON as the selection documentation artifact.
    """

    network_id: SelectionNetworkId
    selected_date: str  # ISO 8601 date string
    selected_day_index: int
    rank: int  # 1-based rank among all 365 candidate days
    composite_score: float
    score_breakdown: DayScore
    scoring_weights: ScoringWeights
    annual_statistics: AnnualStatistics
    selected_day_summary: DailySummary
    top_10_candidates: list[DayScore]  # top 10 days by composite score
    total_candidate_days: int
    days_with_anomalies: int  # count of days penalized for anomalous data
    installed_wind_capacity_mw: float  # from cleaned .m file Pmax sum
    installed_solar_capacity_mw: float  # from cleaned .m file Pmax sum


@dataclass(frozen=True)
class ExtractionResult:
    """Result of extracting a selected day's profiles into canonical CSVs."""

    network_id: SelectionNetworkId
    selected_date: str
    load_csv_path: str  # relative to repo root
    wind_csv_path: str  # relative to repo root
    solar_csv_path: str  # relative to repo root
    load_bus_count: int
    wind_generator_count: int
    solar_generator_count: int
    rationale_json_path: str  # relative to repo root


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOURS_PER_DAY = 24
HOURS_PER_YEAR = 8760
DAYS_PER_YEAR = 365

# ACTIVSg companion CSV file name patterns
_LOAD_FILE_PATTERNS = ["load"]
_WIND_FILE_PATTERNS = ["wind"]
_SOLAR_FILE_PATTERNS = ["solar"]

# Known start dates for ACTIVSg companion time series (2016, non-leap year portion)
_DEFAULT_START_DATE = date(2016, 1, 1)


# ---------------------------------------------------------------------------
# Full-year data loading
# ---------------------------------------------------------------------------


def _find_companion_csv(raw_dir: Path, patterns: list[str]) -> Path:
    """Find a companion CSV file matching one of the given patterns.

    Args:
        raw_dir: Directory to search for CSV files.
        patterns: List of substrings to match in the filename (case-insensitive).

    Returns:
        Path to the matching CSV file.

    Raises:
        FileNotFoundError: If no matching CSV is found.
    """
    for csv_file in sorted(raw_dir.glob("*.csv")):
        name_lower = csv_file.name.lower()
        for pattern in patterns:
            if pattern in name_lower:
                return csv_file
    msg = f"No CSV file matching {patterns} found in {raw_dir}"
    raise FileNotFoundError(msg)


def _load_csv_to_array(csv_path: Path) -> tuple[np.ndarray, list[str]]:
    """Load a companion CSV into a numpy array.

    Reads the CSV, skips the timestamp/time column if present, and returns
    a (N_rows, N_data_columns) array of float values plus column header names.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        Tuple of (data_array, column_names) where column_names are the
        data column headers (excluding the timestamp column).
    """
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        headers = next(reader)
        rows = list(reader)

    # Detect and skip time/timestamp column
    time_keywords = {"time", "timestamp", "datetime", "date", "hour", "date_time"}
    skip_col: int | None = None
    for i, h in enumerate(headers):
        if h.strip().lower() in time_keywords:
            skip_col = i
            break

    if skip_col is not None:
        data_headers = [h for j, h in enumerate(headers) if j != skip_col]
        data_rows = []
        for row in rows:
            vals = []
            for j, v in enumerate(row):
                if j == skip_col:
                    continue
                stripped = v.strip()
                if stripped.lower() in ("", "nan", "na", "null", "none"):
                    vals.append(float("nan"))
                else:
                    vals.append(float(stripped))
            data_rows.append(vals)
    else:
        data_headers = list(headers)
        data_rows = []
        for row in rows:
            vals = []
            for v in row:
                stripped = v.strip()
                if stripped.lower() in ("", "nan", "na", "null", "none"):
                    vals.append(float("nan"))
                else:
                    vals.append(float(stripped))
            data_rows.append(vals)

    arr = np.array(data_rows, dtype=np.float64)
    return arr, data_headers


def load_full_year_load(
    raw_dir: Path,
) -> tuple[np.ndarray, list[int]]:
    """Load the full-year hourly load time series from companion CSVs.

    Reads the ACTIVSg companion load CSV(s) from the network's raw
    download directory and returns a (8760, N_buses) numpy array of
    hourly load values in MW, plus the list of bus IDs corresponding
    to the column axis.

    Args:
        raw_dir: Path to ``data/timeseries/<network>/raw/`` containing
            the downloaded companion CSVs.

    Returns:
        A tuple of (load_array, bus_ids) where load_array has shape
        (8760, N_buses) and bus_ids is a list of integer bus IDs
        corresponding to load_array's column axis.

    Raises:
        FileNotFoundError: If no load CSV is found in raw_dir.
        ValueError: If the load data does not have 8760 hourly rows
            after reshaping.
    """
    csv_path = _find_companion_csv(raw_dir, _LOAD_FILE_PATTERNS)
    arr, headers = _load_csv_to_array(csv_path)

    # Handle transposed format: if columns >> rows, transpose
    if arr.shape[0] < HOURS_PER_YEAR and arr.shape[1] >= HOURS_PER_YEAR:
        arr = arr.T

    if arr.shape[0] != HOURS_PER_YEAR:
        msg = f"Load data has {arr.shape[0]} rows, expected {HOURS_PER_YEAR}"
        raise ValueError(msg)

    # Extract bus IDs from headers
    import re

    bus_ids: list[int] = []
    bus_pattern = re.compile(r"(?:bus[_\s]?)(\d+)", re.IGNORECASE)
    for h in headers:
        m = bus_pattern.search(h)
        if m:
            bus_ids.append(int(m.group(1)))
        elif h.strip().isdigit():
            bus_ids.append(int(h.strip()))
        else:
            # Use column index as bus ID if no pattern matches
            bus_ids.append(len(bus_ids) + 1)

    # Ensure bus_ids list matches number of columns
    if len(bus_ids) != arr.shape[1]:
        bus_ids = list(range(1, arr.shape[1] + 1))

    return arr, bus_ids


def load_full_year_wind(
    raw_dir: Path,
) -> tuple[np.ndarray, list[str]]:
    """Load the full-year hourly wind generation time series.

    Reads the ACTIVSg companion wind CSV(s) and returns a
    (8760, N_wind_gens) numpy array of hourly wind generation in MW,
    plus generator identifier strings corresponding to the column axis.

    Args:
        raw_dir: Path to the network's raw download directory.

    Returns:
        A tuple of (wind_array, gen_ids) where wind_array has shape
        (8760, N_wind_gens).

    Raises:
        FileNotFoundError: If no wind CSV is found in raw_dir.
        ValueError: If the data does not have 8760 hourly rows.
    """
    csv_path = _find_companion_csv(raw_dir, _WIND_FILE_PATTERNS)
    arr, headers = _load_csv_to_array(csv_path)

    if arr.shape[0] < HOURS_PER_YEAR and arr.shape[1] >= HOURS_PER_YEAR:
        arr = arr.T

    if arr.shape[0] != HOURS_PER_YEAR:
        msg = f"Wind data has {arr.shape[0]} rows, expected {HOURS_PER_YEAR}"
        raise ValueError(msg)

    return arr, headers


def load_full_year_solar(
    raw_dir: Path,
) -> tuple[np.ndarray, list[str]]:
    """Load the full-year hourly solar generation time series.

    Reads the ACTIVSg companion solar CSV(s) and returns a
    (8760, N_solar_gens) numpy array of hourly solar generation in MW,
    plus generator identifier strings corresponding to the column axis.

    Args:
        raw_dir: Path to the network's raw download directory.

    Returns:
        A tuple of (solar_array, gen_ids) where solar_array has shape
        (8760, N_solar_gens).

    Raises:
        FileNotFoundError: If no solar CSV is found in raw_dir.
        ValueError: If the data does not have 8760 hourly rows.
    """
    csv_path = _find_companion_csv(raw_dir, _SOLAR_FILE_PATTERNS)
    arr, headers = _load_csv_to_array(csv_path)

    if arr.shape[0] < HOURS_PER_YEAR and arr.shape[1] >= HOURS_PER_YEAR:
        arr = arr.T

    if arr.shape[0] != HOURS_PER_YEAR:
        msg = f"Solar data has {arr.shape[0]} rows, expected {HOURS_PER_YEAR}"
        raise ValueError(msg)

    return arr, headers


def load_renewable_capacity(
    cleaned_m_dir: Path,
    network_id: SelectionNetworkId,
) -> tuple[float, float]:
    """Load installed wind and solar capacity from the cleaned .m file.

    Reads the cleaned .m file (D3 output) and sums Pmax for all wind
    generators and all solar generators based on the genfuel field.

    Args:
        cleaned_m_dir: Path to ``data/timeseries/`` where cleaned .m
            files reside.
        network_id: Which network to read.

    Returns:
        A tuple of (total_wind_pmax_mw, total_solar_pmax_mw).

    Raises:
        FileNotFoundError: If the cleaned .m file is not found.
    """
    import re

    # Map network IDs to .m file names
    m_file_names = {
        SelectionNetworkId.ACTIVSG2000: "case_ACTIVSg2000.m",
        SelectionNetworkId.ACTIVSG10K: "case_ACTIVSg10k.m",
    }

    m_file_name = m_file_names[network_id]
    m_path = cleaned_m_dir / network_id.value / m_file_name

    if not m_path.exists():
        msg = f"Cleaned .m file not found: {m_path}"
        raise FileNotFoundError(msg)

    text = m_path.read_text()

    # Parse gen matrix for Pmax values (column index 8, 0-based)
    gen_pattern = re.compile(r"mpc\.gen\s*=\s*\[([^\]]*)\]", re.DOTALL)
    gen_match = gen_pattern.search(text)
    if gen_match is None:
        msg = "Could not locate mpc.gen block in .m file"
        raise ValueError(msg)

    gen_block = gen_match.group(1)
    pmax_values: list[float] = []
    for line in gen_block.split(";"):
        stripped = line.strip()
        if "%" in stripped:
            stripped = stripped[: stripped.index("%")].strip()
        if not stripped:
            continue
        vals = stripped.split()
        try:
            float_vals = [float(v) for v in vals]
        except ValueError:
            continue
        if len(float_vals) > 8:
            pmax_values.append(float_vals[8])

    # Parse genfuel for fuel types
    genfuel_pattern = re.compile(r"mpc\.genfuel\s*=\s*\{([^}]*)\}", re.DOTALL)
    genfuel_match = genfuel_pattern.search(text)

    if genfuel_match is None:
        # No genfuel data available; return zeros
        return 0.0, 0.0

    genfuel_block = genfuel_match.group(1)
    # Extract quoted fuel strings
    fuel_types: list[str] = []
    fuel_str_pattern = re.compile(r"'([^']*)'")
    for m in fuel_str_pattern.finditer(genfuel_block):
        fuel_types.append(m.group(1).strip().lower())

    total_wind = 0.0
    total_solar = 0.0
    for i, fuel in enumerate(fuel_types):
        if i < len(pmax_values):
            if fuel == "wind":
                total_wind += pmax_values[i]
            elif fuel == "solar":
                total_solar += pmax_values[i]

    return total_wind, total_solar


# ---------------------------------------------------------------------------
# Daily summary computation
# ---------------------------------------------------------------------------


def compute_daily_summaries(
    load: np.ndarray,
    wind: np.ndarray,
    solar: np.ndarray,
    *,
    start_date: date = _DEFAULT_START_DATE,
) -> list[DailySummary]:
    """Compute per-day summary statistics from full-year arrays.

    Reshapes the (8760, N) arrays into (365, 24, N) blocks and computes
    summary statistics for each of the 365 days.

    For load: sums across all buses per hour to get system load, then
    computes daily total MWh, peak hourly MW, and max hour-over-hour
    ramp. For wind and solar: sums across all generators per hour.
    Renewable penetration = (wind_mwh + solar_mwh) / load_mwh.

    Args:
        load: Array of shape (8760, N_buses), hourly load in MW.
        wind: Array of shape (8760, N_wind_gens), hourly wind in MW.
        solar: Array of shape (8760, N_solar_gens), hourly solar in MW.
        start_date: Calendar date of the first hour in the time series.

    Returns:
        A list of 365 DailySummary objects, one per day, in
        chronological order.

    Raises:
        ValueError: If any input array does not have exactly 8760 rows.
    """
    for name, arr in [("load", load), ("wind", wind), ("solar", solar)]:
        if arr.shape[0] != HOURS_PER_YEAR:
            msg = f"{name} array has {arr.shape[0]} rows, expected {HOURS_PER_YEAR}"
            raise ValueError(msg)

    # Ensure 2D
    if load.ndim == 1:
        load = load.reshape(-1, 1)
    if wind.ndim == 1:
        wind = wind.reshape(-1, 1)
    if solar.ndim == 1:
        solar = solar.reshape(-1, 1)

    # Reshape to (365, 24, N)
    load_daily = load.reshape(DAYS_PER_YEAR, HOURS_PER_DAY, -1)
    wind_daily = wind.reshape(DAYS_PER_YEAR, HOURS_PER_DAY, -1)
    solar_daily = solar.reshape(DAYS_PER_YEAR, HOURS_PER_DAY, -1)

    # Aggregate across buses/generators per hour -> (365, 24)
    load_system = np.nansum(load_daily, axis=2)  # (365, 24)
    wind_system = np.nansum(wind_daily, axis=2)  # (365, 24)
    solar_system = np.nansum(solar_daily, axis=2)  # (365, 24)

    summaries: list[DailySummary] = []
    for d in range(DAYS_PER_YEAR):
        current_date = start_date + timedelta(days=d)
        date_str = current_date.isoformat()
        is_weekday = current_date.weekday() < 5

        load_hourly = load_system[d]  # (24,)
        wind_hourly = wind_system[d]  # (24,)
        solar_hourly = solar_system[d]  # (24,)

        total_load = float(np.nansum(load_hourly))
        peak_load = float(np.nanmax(load_hourly))
        total_wind = float(np.nansum(wind_hourly))
        total_solar = float(np.nansum(solar_hourly))
        peak_wind = float(np.nanmax(wind_hourly))
        peak_solar = float(np.nanmax(solar_hourly))

        # Max hour-over-hour load ramp (absolute)
        if len(load_hourly) > 1:
            ramps = np.abs(np.diff(load_hourly))
            max_ramp = float(np.nanmax(ramps))
        else:
            max_ramp = 0.0

        # Renewable penetration
        if total_load > 0:
            renewable_penetration = (total_wind + total_solar) / total_load
        else:
            renewable_penetration = 0.0

        # Count hours with any NaN in any of the three arrays for this day
        load_nan = np.any(np.isnan(load_daily[d]), axis=1)  # (24,)
        wind_nan = np.any(np.isnan(wind_daily[d]), axis=1)
        solar_nan = np.any(np.isnan(solar_daily[d]), axis=1)
        any_nan = load_nan | wind_nan | solar_nan
        missing_hours = int(np.sum(any_nan))

        summaries.append(
            DailySummary(
                day_index=d,
                date_str=date_str,
                total_load_mwh=total_load,
                peak_load_mw=peak_load,
                total_wind_mwh=total_wind,
                total_solar_mwh=total_solar,
                peak_wind_mw=peak_wind,
                peak_solar_mw=peak_solar,
                max_load_ramp_mw=max_ramp,
                renewable_penetration=renewable_penetration,
                missing_hours=missing_hours,
                is_weekday=is_weekday,
            )
        )

    return summaries


def compute_annual_statistics(
    summaries: list[DailySummary],
) -> AnnualStatistics:
    """Compute annual min/mean/max for each metric across all 365 days.

    Args:
        summaries: List of 365 DailySummary objects.

    Returns:
        An AnnualStatistics with min/mean/max for each metric.
    """
    loads = np.array([s.total_load_mwh for s in summaries])
    peaks = np.array([s.peak_load_mw for s in summaries])
    winds = np.array([s.total_wind_mwh for s in summaries])
    solars = np.array([s.total_solar_mwh for s in summaries])
    ramps = np.array([s.max_load_ramp_mw for s in summaries])
    rp = np.array([s.renewable_penetration for s in summaries])

    return AnnualStatistics(
        load_mwh_min=float(np.min(loads)),
        load_mwh_mean=float(np.mean(loads)),
        load_mwh_max=float(np.max(loads)),
        peak_load_mw_min=float(np.min(peaks)),
        peak_load_mw_mean=float(np.mean(peaks)),
        peak_load_mw_max=float(np.max(peaks)),
        wind_mwh_min=float(np.min(winds)),
        wind_mwh_mean=float(np.mean(winds)),
        wind_mwh_max=float(np.max(winds)),
        solar_mwh_min=float(np.min(solars)),
        solar_mwh_mean=float(np.mean(solars)),
        solar_mwh_max=float(np.max(solars)),
        max_ramp_mw_min=float(np.min(ramps)),
        max_ramp_mw_mean=float(np.mean(ramps)),
        max_ramp_mw_max=float(np.max(ramps)),
        renewable_penetration_min=float(np.min(rp)),
        renewable_penetration_mean=float(np.mean(rp)),
        renewable_penetration_max=float(np.max(rp)),
    )


# ---------------------------------------------------------------------------
# Day scoring
# ---------------------------------------------------------------------------


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Min-max normalize a value to [0, 1].

    If max_val == min_val (no variation), returns 0.5.
    """
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def score_day(
    summary: DailySummary,
    annual_stats: AnnualStatistics,
    weights: ScoringWeights,
    installed_wind_mw: float,
    installed_solar_mw: float,
) -> DayScore:
    """Score a single candidate day using the composite metric.

    Each metric is normalized to [0, 1] using min-max normalization
    against the annual statistics. The diversity score measures whether
    both wind and solar contribute meaningfully.

    Args:
        summary: The DailySummary for the candidate day.
        annual_stats: Annual statistics for normalization.
        weights: Scoring weights.
        installed_wind_mw: Total installed wind capacity (MW).
        installed_solar_mw: Total installed solar capacity (MW).

    Returns:
        A DayScore with composite score and per-metric breakdown.
    """
    # Normalize metrics to [0, 1]
    load_norm = _normalize(
        summary.total_load_mwh,
        annual_stats.load_mwh_min,
        annual_stats.load_mwh_max,
    )
    wind_norm = _normalize(
        summary.total_wind_mwh,
        annual_stats.wind_mwh_min,
        annual_stats.wind_mwh_max,
    )
    solar_norm = _normalize(
        summary.total_solar_mwh,
        annual_stats.solar_mwh_min,
        annual_stats.solar_mwh_max,
    )
    ramp_norm = _normalize(
        summary.max_load_ramp_mw,
        annual_stats.max_ramp_mw_min,
        annual_stats.max_ramp_mw_max,
    )

    # Diversity score: min(cf) / max(cf) for wind and solar
    if installed_wind_mw > 0 and installed_solar_mw > 0:
        wind_cf = summary.total_wind_mwh / (installed_wind_mw * HOURS_PER_DAY)
        solar_cf = summary.total_solar_mwh / (installed_solar_mw * HOURS_PER_DAY)
        max_cf = max(wind_cf, solar_cf)
        min_cf = min(wind_cf, solar_cf)
        diversity = min_cf / max_cf if max_cf > 0 else 0.0
    else:
        diversity = 0.0

    # Weekday bonus
    weekday = 1.0 if summary.is_weekday else 0.0

    # Anomaly penalty
    anomaly_penalty = 0.0
    if summary.missing_hours > 0:
        anomaly_penalty = 1.0
    # Zero system load in any hour is also anomalous
    # (checked via peak_load: if peak is 0 then all hours are 0)
    if summary.peak_load_mw == 0.0:
        anomaly_penalty = 1.0

    # Composite score
    composite = (
        weights.load_level * load_norm
        + weights.wind_generation * wind_norm
        + weights.solar_generation * solar_norm
        + weights.ramp_magnitude * ramp_norm
        + weights.renewable_diversity * diversity
        + weights.weekday_bonus * weekday
    ) - anomaly_penalty

    return DayScore(
        day_index=summary.day_index,
        date_str=summary.date_str,
        composite_score=composite,
        load_level_score=load_norm,
        wind_score=wind_norm,
        solar_score=solar_norm,
        ramp_score=ramp_norm,
        diversity_score=diversity,
        weekday_score=weekday,
        anomaly_penalty=anomaly_penalty,
    )


def rank_days(
    summaries: list[DailySummary],
    annual_stats: AnnualStatistics,
    weights: ScoringWeights,
    installed_wind_mw: float,
    installed_solar_mw: float,
) -> list[DayScore]:
    """Score and rank all 365 candidate days by composite score.

    Args:
        summaries: List of 365 DailySummary objects.
        annual_stats: Annual statistics for normalization.
        weights: Scoring weights.
        installed_wind_mw: Total installed wind capacity.
        installed_solar_mw: Total installed solar capacity.

    Returns:
        A list of DayScore objects sorted by composite_score descending.
    """
    scores = [
        score_day(s, annual_stats, weights, installed_wind_mw, installed_solar_mw)
        for s in summaries
    ]
    scores.sort(key=lambda s: s.composite_score, reverse=True)
    return scores


def select_day(
    summaries: list[DailySummary],
    annual_stats: AnnualStatistics,
    weights: ScoringWeights,
    installed_wind_mw: float,
    installed_solar_mw: float,
) -> tuple[DayScore, list[DayScore]]:
    """Select the top-scoring representative day.

    Args:
        summaries: List of 365 DailySummary objects.
        annual_stats: Annual statistics for normalization.
        weights: Scoring weights.
        installed_wind_mw: Total installed wind capacity.
        installed_solar_mw: Total installed solar capacity.

    Returns:
        A tuple of (best_day_score, all_ranked_scores).
    """
    ranked = rank_days(summaries, annual_stats, weights, installed_wind_mw, installed_solar_mw)
    return ranked[0], ranked


# ---------------------------------------------------------------------------
# Profile extraction
# ---------------------------------------------------------------------------


def extract_day_profiles(
    load: np.ndarray,
    wind: np.ndarray,
    solar: np.ndarray,
    day_index: int,
    load_bus_ids: list[int],
    wind_gen_ids: list[str],
    solar_gen_ids: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract the 24-hour profiles for a specific day.

    Slices the full-year arrays at rows [day_index * 24 : (day_index + 1) * 24]
    to produce (24, N) arrays for load, wind, and solar.

    Args:
        load: Full-year load array, shape (8760, N_buses).
        wind: Full-year wind array, shape (8760, N_wind_gens).
        solar: Full-year solar array, shape (8760, N_solar_gens).
        day_index: 0-based day index (0..364).
        load_bus_ids: Bus IDs for the load column axis.
        wind_gen_ids: Generator IDs for the wind column axis.
        solar_gen_ids: Generator IDs for the solar column axis.

    Returns:
        A tuple of (load_24h, wind_24h, solar_24h), each with shape
        (24, N_entities).

    Raises:
        ValueError: If day_index is not in [0, 364].
    """
    if day_index < 0 or day_index > 364:
        msg = f"day_index must be in [0, 364], got {day_index}"
        raise ValueError(msg)

    start = day_index * HOURS_PER_DAY
    end = start + HOURS_PER_DAY

    load_24h = load[start:end]
    wind_24h = wind[start:end]
    solar_24h = solar[start:end]

    return load_24h, wind_24h, solar_24h


def write_canonical_csv(
    data_24h: np.ndarray,
    entity_ids: list[int] | list[str],
    id_column_name: str,
    dest_path: Path,
) -> None:
    """Write a 24-hour profile array to canonical CSV format.

    Transposes the (24, N_entities) array so that each row is one
    entity (bus or generator) and columns are HR_1 through HR_24,
    following the hour-ending convention:
        HR_1 = hour 0 (00:00-01:00) of the source day
        HR_24 = hour 23 (23:00-24:00) of the source day

    Args:
        data_24h: Array of shape (24, N_entities), hourly values in MW.
        entity_ids: List of entity identifiers (bus IDs or gen UIDs).
        id_column_name: Header name for the ID column.
        dest_path: Path to write the CSV file.

    Raises:
        ValueError: If data_24h does not have exactly 24 rows.
        ValueError: If len(entity_ids) != data_24h.shape[1].
    """
    if data_24h.shape[0] != HOURS_PER_DAY:
        msg = f"data_24h must have {HOURS_PER_DAY} rows, got {data_24h.shape[0]}"
        raise ValueError(msg)

    n_entities = data_24h.shape[1] if data_24h.ndim > 1 else 1
    if len(entity_ids) != n_entities:
        msg = f"entity_ids has {len(entity_ids)} entries but data has {n_entities} columns"
        raise ValueError(msg)

    # Ensure 2D
    if data_24h.ndim == 1:
        data_24h = data_24h.reshape(-1, 1)

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Transpose: (24, N) -> rows per entity, columns per hour
    # data_24h[h, e] -> row e, column HR_{h+1}
    header = [id_column_name] + [f"HR_{h + 1}" for h in range(HOURS_PER_DAY)]

    with open(dest_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for e_idx, entity_id in enumerate(entity_ids):
            row_values = [round(float(data_24h[h, e_idx]), 2) for h in range(HOURS_PER_DAY)]
            writer.writerow([entity_id] + row_values)


# ---------------------------------------------------------------------------
# Rationale output
# ---------------------------------------------------------------------------


def build_selection_rationale(
    network_id: SelectionNetworkId,
    best_score: DayScore,
    all_scores: list[DayScore],
    summaries: list[DailySummary],
    annual_stats: AnnualStatistics,
    weights: ScoringWeights,
    installed_wind_mw: float,
    installed_solar_mw: float,
) -> SelectionRationale:
    """Assemble the selection rationale document for one network.

    Args:
        network_id: Which network was analyzed.
        best_score: The DayScore for the selected day.
        all_scores: All DayScore objects sorted by rank.
        summaries: All 365 DailySummary objects.
        annual_stats: Annual statistics.
        weights: Scoring weights used.
        installed_wind_mw: Total installed wind capacity.
        installed_solar_mw: Total installed solar capacity.

    Returns:
        A SelectionRationale with full documentation.
    """
    # Find rank of selected day (1-based)
    rank = 1
    for i, s in enumerate(all_scores):
        if s.day_index == best_score.day_index:
            rank = i + 1
            break

    # Find the selected day's summary
    selected_summary = summaries[best_score.day_index]

    # Top 10 candidates
    top_10 = all_scores[:10]

    # Count days with anomalies
    days_with_anomalies = sum(1 for s in all_scores if s.anomaly_penalty > 0)

    return SelectionRationale(
        network_id=network_id,
        selected_date=best_score.date_str,
        selected_day_index=best_score.day_index,
        rank=rank,
        composite_score=best_score.composite_score,
        score_breakdown=best_score,
        scoring_weights=weights,
        annual_statistics=annual_stats,
        selected_day_summary=selected_summary,
        top_10_candidates=top_10,
        total_candidate_days=len(all_scores),
        days_with_anomalies=days_with_anomalies,
        installed_wind_capacity_mw=installed_wind_mw,
        installed_solar_capacity_mw=installed_solar_mw,
    )


def _round_floats(obj: object, decimals: int = 4) -> object:
    """Recursively round float values in a nested dict/list structure."""
    if isinstance(obj, float):
        return round(obj, decimals)
    if isinstance(obj, dict):
        return {k: _round_floats(v, decimals) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(item, decimals) for item in obj]
    return obj


def _serialize_for_json(obj: object) -> object:
    """Custom JSON serializer for StrEnum values."""
    if isinstance(obj, StrEnum):
        return obj.value
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def write_rationale_json(
    rationale: SelectionRationale,
    dest_path: Path,
) -> None:
    """Serialize a SelectionRationale to a human-readable JSON file.

    Writes indented JSON with snake_case keys matching the dataclass
    field names. Enum values are serialized as their string values.
    Float values are rounded to 4 decimal places.

    Args:
        rationale: The rationale to serialize.
        dest_path: Path to write the JSON file.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(rationale)
    data = _round_floats(data)
    with open(dest_path, "w") as fh:
        json.dump(data, fh, indent=2, default=_serialize_for_json)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def process_network(
    network_id: SelectionNetworkId,
    raw_dir: Path,
    cleaned_m_dir: Path,
    output_dir: Path,
    *,
    target_date: str | None = None,
    weights: ScoringWeights | None = None,
) -> ExtractionResult:
    """Run the full selection and extraction pipeline for one network.

    Loads full-year data, computes daily summaries, scores and ranks
    candidate days, selects the best day (or uses target_date if
    provided), extracts 24-hour profiles, writes canonical CSVs, and
    writes the selection rationale JSON.

    Args:
        network_id: Which network to process.
        raw_dir: Path to ``data/timeseries/<network>/raw/``.
        cleaned_m_dir: Path to ``data/timeseries/`` (contains cleaned
            .m files from D3).
        output_dir: Path to ``data/timeseries/<network>/`` for output.
        target_date: Optional override date. If None, the top-scoring
            day is selected automatically.
        weights: Optional scoring weights override.

    Returns:
        An ExtractionResult documenting the output file paths and
        entity counts.

    Raises:
        FileNotFoundError: If raw companion data or cleaned .m file not found.
        ValueError: If target_date does not match any day in the time series.
    """
    if weights is None:
        weights = ScoringWeights()

    # Load full-year data
    load_arr, bus_ids = load_full_year_load(raw_dir)
    wind_arr, wind_gen_ids = load_full_year_wind(raw_dir)
    solar_arr, solar_gen_ids = load_full_year_solar(raw_dir)

    # Load renewable capacity from cleaned .m file
    installed_wind_mw, installed_solar_mw = load_renewable_capacity(cleaned_m_dir, network_id)

    # Compute daily summaries
    summaries = compute_daily_summaries(load_arr, wind_arr, solar_arr)

    # Score and rank
    annual_stats = compute_annual_statistics(summaries)
    best_score, all_scores = select_day(
        summaries, annual_stats, weights, installed_wind_mw, installed_solar_mw
    )

    # Override with target_date if specified
    if target_date is not None:
        found = False
        for s in summaries:
            if s.date_str == target_date:
                day_index = s.day_index
                found = True
                break
        if not found:
            msg = f"target_date {target_date!r} not found in time series"
            raise ValueError(msg)
        # Find the score for the target day
        for sc in all_scores:
            if sc.day_index == day_index:
                best_score = sc
                break
    else:
        day_index = best_score.day_index

    # Extract profiles
    load_24h, wind_24h, solar_24h = extract_day_profiles(
        load_arr, wind_arr, solar_arr, day_index, bus_ids, wind_gen_ids, solar_gen_ids
    )

    # Write canonical CSVs
    output_dir.mkdir(parents=True, exist_ok=True)
    load_csv_path = output_dir / "load_24h.csv"
    wind_csv_path = output_dir / "wind_actual_24h.csv"
    solar_csv_path = output_dir / "solar_actual_24h.csv"

    write_canonical_csv(load_24h, bus_ids, "bus_id", load_csv_path)
    write_canonical_csv(wind_24h, wind_gen_ids, "gen_uid", wind_csv_path)
    write_canonical_csv(solar_24h, solar_gen_ids, "gen_uid", solar_csv_path)

    # Build and write rationale
    rationale = build_selection_rationale(
        network_id,
        best_score,
        all_scores,
        summaries,
        annual_stats,
        weights,
        installed_wind_mw,
        installed_solar_mw,
    )
    rationale_path = output_dir / "selection_rationale.json"
    write_rationale_json(rationale, rationale_path)

    return ExtractionResult(
        network_id=network_id,
        selected_date=best_score.date_str,
        load_csv_path=str(load_csv_path),
        wind_csv_path=str(wind_csv_path),
        solar_csv_path=str(solar_csv_path),
        load_bus_count=len(bus_ids),
        wind_generator_count=len(wind_gen_ids),
        solar_generator_count=len(solar_gen_ids),
        rationale_json_path=str(rationale_path),
    )


def main(
    timeseries_base_dir: Path | None = None,
    *,
    target_date: str | None = None,
    weights: ScoringWeights | None = None,
) -> list[ExtractionResult]:
    """Entry point: select and extract representative days for all networks.

    Processes ACTIVSg2000 and ACTIVSg10k. Does NOT process case39
    (no companion data).

    Args:
        timeseries_base_dir: Base directory for input/output. Defaults
            to <repo_root>/data/timeseries/.
        target_date: Optional override date for both networks.
        weights: Optional scoring weights override.

    Returns:
        A list of ExtractionResult, one per network processed.
    """
    if timeseries_base_dir is None:
        timeseries_base_dir = Path(__file__).resolve().parent.parent / "timeseries"

    results: list[ExtractionResult] = []
    for network_id in SelectionNetworkId:
        raw_dir = timeseries_base_dir / network_id.value / "raw"
        output_dir = timeseries_base_dir / network_id.value

        result = process_network(
            network_id=network_id,
            raw_dir=raw_dir,
            cleaned_m_dir=timeseries_base_dir,
            output_dir=output_dir,
            target_date=target_date,
            weights=weights,
        )
        results.append(result)

    return results


if __name__ == "__main__":
    main()
