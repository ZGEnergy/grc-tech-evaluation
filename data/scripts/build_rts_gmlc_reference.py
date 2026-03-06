"""RTS-GMLC Technology Class Reference Table builder.

Downloads the RTS-GMLC gen.csv from the GridMod GitHub repository, parses generator
parameters, classifies generators into technology classes by fuel type and capacity band,
aggregates parameters within each class using median statistics, and writes a canonical
reference CSV with provenance header.

The output table provides template parameters (ramp rates, min up/down times, startup
costs) organized by technology class for use by downstream generator calibration steps.
"""

from __future__ import annotations

import csv
import io
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RTS_GMLC_REPO_URL = "https://github.com/GridMod/RTS-GMLC"
RTS_GMLC_RAW_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/GridMod/RTS-GMLC/{commit_hash}/RTS_Data/SourceData/gen.csv"
)
RTS_GMLC_FILE_PATH = "RTS_Data/SourceData/gen.csv"

# Required columns in the RTS-GMLC gen.csv (after whitespace stripping).
REQUIRED_COLUMNS = frozenset(
    {
        "GEN UID",
        "Bus ID",
        "Unit Type",
        "Fuel",
        "Category",
        "PMax MW",
        "PMin MW",
        "Ramp Rate MW/Min",
        "Min Up Time Hr",
        "Min Down Time Hr",
        "Start Time Cold Hr",
        "Start Time Warm Hr",
        "Start Time Hot Hr",
        "Start Heat Cold MBTU",
        "Start Heat Warm MBTU",
        "Start Heat Hot MBTU",
        "Non Fuel Start Cost $",
        "Non Fuel Shutdown Cost $",
        "Fuel Price $/MMBTU",
        "HR_avg_0",
    }
)

# Fuel name mapping from RTS-GMLC CSV values to our canonical FuelType.
_FUEL_MAP: dict[str, str] = {
    "Coal": "coal",
    "NG": "gas",
    "Oil": "oil",
    "Nuclear": "nuclear",
    "Hydro": "hydro",
    "Wind": "wind",
    "Solar": "solar",
}

# Unit types that should be excluded from the reference table.
_EXCLUDED_UNIT_TYPES = frozenset({"SYNC_COND"})

# Fuel types treated as renewable (zero temporal parameters).
_RENEWABLE_FUELS = frozenset({"wind", "solar"})


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class FuelType(StrEnum):
    """Fuel types recognized in the RTS-GMLC generator fleet."""

    COAL = "coal"
    GAS = "gas"
    OIL = "oil"
    NUCLEAR = "nuclear"
    HYDRO = "hydro"
    WIND = "wind"
    SOLAR = "solar"


class UnitType(StrEnum):
    """Unit types (prime mover categories) in the RTS-GMLC generator fleet."""

    STEAM = "STEAM"
    CT = "CT"
    CC = "CC"
    NUCLEAR = "NUCLEAR"
    HYDRO = "HYDRO"
    WIND = "WIND"
    PV = "PV"
    RTPV = "RTPV"
    SYNC_COND = "SYNC_COND"


class CapacityBand(StrEnum):
    """Capacity band classification for generators within a fuel type."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass(frozen=True)
class CapacityBandThreshold:
    """MW thresholds defining the boundaries of a capacity band for a fuel type.

    A generator with pmax_mw in [min_mw, max_mw) is classified into this band.
    The max_mw of the last band is inclusive (uses <=, not <).
    """

    fuel_type: FuelType
    band: CapacityBand
    min_mw: float  # inclusive lower bound
    max_mw: float  # exclusive upper bound (inclusive for the largest band)


@dataclass(frozen=True)
class RtsGmlcGenerator:
    """A single generator row parsed from RTS-GMLC gen.csv."""

    gen_uid: str
    bus_id: int
    unit_type: str
    fuel: str
    category: str
    pmax_mw: float
    pmin_mw: float
    ramp_rate_mw_per_min: float
    min_up_time_hr: float
    min_down_time_hr: float
    startup_time_cold_hr: float
    startup_time_warm_hr: float
    startup_time_hot_hr: float
    startup_heat_cold_mbtu: float
    startup_heat_warm_mbtu: float
    startup_heat_hot_mbtu: float
    non_fuel_start_cost_dollar: float
    non_fuel_shutdown_cost_dollar: float
    fuel_price_dollar_per_mmbtu: float
    hr_avg_0: float  # average heat rate at minimum output (BTU/kWh)


@dataclass(frozen=True)
class TechClassRow:
    """A single row in the output reference table: one technology class."""

    tech_class: str  # e.g., "coal_large", "gas_CT_small"
    fuel_type: str
    unit_type: str
    capacity_band: str
    pmax_template_mw: float  # median Pmax within the class
    pmin_template_mw: float  # median Pmin within the class
    ramp_rate_mw_per_min: float
    ramp_rate_mw_per_hr: float  # ramp_rate_mw_per_min * 60
    min_up_time_hr: float
    min_down_time_hr: float
    startup_time_cold_hr: float
    startup_time_warm_hr: float
    startup_time_hot_hr: float
    startup_cost_cold_dollar: float  # computed: heat * fuel_price + non_fuel_cost
    startup_cost_warm_dollar: float
    startup_cost_hot_dollar: float
    shutdown_cost_dollar: float
    capacity_band_min_mw: float  # classification threshold: lower bound
    capacity_band_max_mw: float  # classification threshold: upper bound
    generator_count: int  # number of RTS-GMLC generators in this class
    source_gen_uids: list[str]  # GEN UIDs of source generators


@dataclass(frozen=True)
class RtsGmlcProvenance:
    """Provenance metadata for the RTS-GMLC data extraction."""

    repo_url: str  # e.g., "https://github.com/GridMod/RTS-GMLC"
    commit_hash: str
    file_path: str  # e.g., "RTS_Data/SourceData/gen.csv"
    download_timestamp: str  # ISO 8601
    script_version: str
    num_generators_parsed: int
    num_tech_classes_produced: int


@dataclass(frozen=True)
class ReferenceTableResult:
    """Complete result of building the reference table."""

    provenance: RtsGmlcProvenance
    tech_classes: list[TechClassRow]
    capacity_band_thresholds: list[CapacityBandThreshold]
    excluded_gen_uids: list[str]  # e.g., SYNC_COND units
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CSV output column order (excludes source_gen_uids which is list-valued)
# ---------------------------------------------------------------------------

_OUTPUT_COLUMNS = [
    "tech_class",
    "fuel_type",
    "unit_type",
    "capacity_band",
    "pmax_template_mw",
    "pmin_template_mw",
    "ramp_rate_mw_per_min",
    "ramp_rate_mw_per_hr",
    "min_up_time_hr",
    "min_down_time_hr",
    "startup_time_cold_hr",
    "startup_time_warm_hr",
    "startup_time_hot_hr",
    "startup_cost_cold_dollar",
    "startup_cost_warm_dollar",
    "startup_cost_hot_dollar",
    "shutdown_cost_dollar",
    "capacity_band_min_mw",
    "capacity_band_max_mw",
    "generator_count",
]


# ---------------------------------------------------------------------------
# Download and parse
# ---------------------------------------------------------------------------


def download_rts_gmlc_gen_csv(
    dest_path: Path,
    *,
    commit_hash: str,
    timeout_seconds: int = 60,
) -> Path:
    """Download gen.csv from the RTS-GMLC GitHub repository at a pinned commit.

    Fetches the raw file from:
        https://raw.githubusercontent.com/GridMod/RTS-GMLC/{commit_hash}/
        RTS_Data/SourceData/gen.csv

    If dest_path already exists, skips the download and returns the existing
    path (idempotent). Creates parent directories if needed.

    Args:
        dest_path: Local file path to write the downloaded CSV.
        commit_hash: Git commit hash to pin the download to.
        timeout_seconds: HTTP request timeout.

    Returns:
        The path to the downloaded (or existing) file.

    Raises:
        ConnectionError: If the download fails after retries.
        ValueError: If the downloaded content does not appear to be a valid CSV
            (e.g., missing expected header columns).
    """
    if dest_path.exists():
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    url = RTS_GMLC_RAW_URL_TEMPLATE.format(commit_hash=commit_hash)
    request = Request(url, headers={"User-Agent": "grc-tech-evaluation"})  # noqa: S310

    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            content = response.read().decode("utf-8")
    except (URLError, TimeoutError) as exc:
        msg = f"Failed to download RTS-GMLC gen.csv from {url}: {exc}"
        raise ConnectionError(msg) from exc

    # Basic validation: check for expected header columns.
    first_line = content.split("\n", maxsplit=1)[0]
    header_cols = {col.strip() for col in first_line.split(",")}
    missing = REQUIRED_COLUMNS - header_cols
    if missing:
        msg = f"Downloaded CSV is missing required columns: {sorted(missing)}"
        raise ValueError(msg)

    dest_path.write_text(content, encoding="utf-8")
    return dest_path


def _safe_float(value: str, column_name: str, gen_uid: str) -> float:
    """Convert a string value to float, returning 0.0 for empty/non-numeric with a warning."""
    value = value.strip()
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        print(
            f"WARNING: Non-numeric value '{value}' in column '{column_name}' "
            f"for generator '{gen_uid}', using 0.0",
            file=sys.stderr,
        )
        return 0.0


def parse_gen_csv(csv_path: Path) -> list[RtsGmlcGenerator]:
    """Parse the RTS-GMLC gen.csv into a list of generator records.

    Handles the leading-space column name quirk by stripping whitespace from
    all header names. Filters out rows with empty or null GEN UID. Converts
    numeric fields to float, handling any non-numeric entries as NaN with a
    warning.

    Args:
        csv_path: Path to the gen.csv file.

    Returns:
        A list of RtsGmlcGenerator dataclass instances, one per generator row.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns are missing from the CSV header.
    """
    if not csv_path.exists():
        msg = f"File not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    # Strip whitespace from field names.
    if reader.fieldnames is None:
        msg = "CSV file has no header row"
        raise ValueError(msg)

    stripped_fields = [f.strip() for f in reader.fieldnames]
    reader.fieldnames = stripped_fields

    # Validate required columns.
    header_set = set(stripped_fields)
    missing = REQUIRED_COLUMNS - header_set
    if missing:
        msg = f"CSV is missing required columns: {sorted(missing)}"
        raise ValueError(msg)

    generators: list[RtsGmlcGenerator] = []
    for row in reader:
        # Strip keys to handle any residual whitespace.
        row = {k.strip(): v for k, v in row.items()}

        gen_uid = row.get("GEN UID", "").strip()
        if not gen_uid:
            continue

        gen = RtsGmlcGenerator(
            gen_uid=gen_uid,
            bus_id=int(_safe_float(row["Bus ID"], "Bus ID", gen_uid)),
            unit_type=row["Unit Type"].strip(),
            fuel=row["Fuel"].strip(),
            category=row.get("Category", "").strip(),
            pmax_mw=_safe_float(row["PMax MW"], "PMax MW", gen_uid),
            pmin_mw=_safe_float(row["PMin MW"], "PMin MW", gen_uid),
            ramp_rate_mw_per_min=_safe_float(row["Ramp Rate MW/Min"], "Ramp Rate MW/Min", gen_uid),
            min_up_time_hr=_safe_float(row["Min Up Time Hr"], "Min Up Time Hr", gen_uid),
            min_down_time_hr=_safe_float(row["Min Down Time Hr"], "Min Down Time Hr", gen_uid),
            startup_time_cold_hr=_safe_float(
                row["Start Time Cold Hr"], "Start Time Cold Hr", gen_uid
            ),
            startup_time_warm_hr=_safe_float(
                row["Start Time Warm Hr"], "Start Time Warm Hr", gen_uid
            ),
            startup_time_hot_hr=_safe_float(row["Start Time Hot Hr"], "Start Time Hot Hr", gen_uid),
            startup_heat_cold_mbtu=_safe_float(
                row["Start Heat Cold MBTU"], "Start Heat Cold MBTU", gen_uid
            ),
            startup_heat_warm_mbtu=_safe_float(
                row["Start Heat Warm MBTU"], "Start Heat Warm MBTU", gen_uid
            ),
            startup_heat_hot_mbtu=_safe_float(
                row["Start Heat Hot MBTU"], "Start Heat Hot MBTU", gen_uid
            ),
            non_fuel_start_cost_dollar=_safe_float(
                row["Non Fuel Start Cost $"], "Non Fuel Start Cost $", gen_uid
            ),
            non_fuel_shutdown_cost_dollar=_safe_float(
                row["Non Fuel Shutdown Cost $"], "Non Fuel Shutdown Cost $", gen_uid
            ),
            fuel_price_dollar_per_mmbtu=_safe_float(
                row["Fuel Price $/MMBTU"], "Fuel Price $/MMBTU", gen_uid
            ),
            hr_avg_0=_safe_float(row["HR_avg_0"], "HR_avg_0", gen_uid),
        )
        generators.append(gen)

    return generators


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def build_capacity_band_thresholds() -> list[CapacityBandThreshold]:
    """Define capacity band MW thresholds for each fuel type.

    Thresholds are derived from natural breaks in the RTS-GMLC fleet:
    - Coal: small < 100 MW, medium 100-300 MW, large >= 300 MW
    - Gas CT: small < 100 MW, large >= 100 MW
    - Gas CC: single band (large, all 355 MW units)
    - Gas STEAM: single band
    - Oil CT: single band (all 20 MW units)
    - Nuclear: single band (all 400 MW units)
    - Hydro: single band (all 50 MW units)
    - Wind: single band
    - Solar: single band

    Returns:
        A list of CapacityBandThreshold defining all fuel/band combinations.
    """
    thresholds: list[CapacityBandThreshold] = []

    # Coal: three bands based on RTS-GMLC fleet (76 MW, 155 MW, 350 MW units).
    thresholds.extend(
        [
            CapacityBandThreshold(FuelType.COAL, CapacityBand.SMALL, 0.0, 100.0),
            CapacityBandThreshold(FuelType.COAL, CapacityBand.MEDIUM, 100.0, 300.0),
            CapacityBandThreshold(FuelType.COAL, CapacityBand.LARGE, 300.0, float("inf")),
        ]
    )

    # Gas: separate by unit type via tech_class naming; thresholds per sub-type.
    # Gas CT: small (20 MW) and large (55 MW+) -- threshold at 40 MW.
    thresholds.extend(
        [
            CapacityBandThreshold(FuelType.GAS, CapacityBand.SMALL, 0.0, 40.0),
            CapacityBandThreshold(FuelType.GAS, CapacityBand.LARGE, 40.0, float("inf")),
        ]
    )

    # Oil: single band.
    thresholds.append(CapacityBandThreshold(FuelType.OIL, CapacityBand.SMALL, 0.0, float("inf")))

    # Nuclear: single band.
    thresholds.append(
        CapacityBandThreshold(FuelType.NUCLEAR, CapacityBand.LARGE, 0.0, float("inf"))
    )

    # Hydro: single band.
    thresholds.append(CapacityBandThreshold(FuelType.HYDRO, CapacityBand.SMALL, 0.0, float("inf")))

    # Wind: single band.
    thresholds.append(CapacityBandThreshold(FuelType.WIND, CapacityBand.SMALL, 0.0, float("inf")))

    # Solar: single band.
    thresholds.append(CapacityBandThreshold(FuelType.SOLAR, CapacityBand.SMALL, 0.0, float("inf")))

    return thresholds


def _map_fuel(fuel_str: str) -> FuelType | None:
    """Map an RTS-GMLC fuel string to a canonical FuelType."""
    canonical = _FUEL_MAP.get(fuel_str)
    if canonical is None:
        return None
    return FuelType(canonical)


def _build_tech_class_name(fuel_type: FuelType, unit_type: str, band: CapacityBand) -> str:
    """Build a technology class name string.

    Naming conventions:
    - Gas generators include the unit type: gas_CT_small, gas_CC, gas_STEAM
    - Oil generators include the unit type: oil_CT
    - Single-band fuel types omit the band: nuclear, hydro, wind, solar
    - Multi-band fuel types include the band: coal_small, coal_large
    """
    # For gas and oil, always include unit type in the name.
    if fuel_type in (FuelType.GAS, FuelType.OIL):
        # Check if this fuel/unit combination has multiple bands.
        return f"{fuel_type.value}_{unit_type}"

    # For renewables, just use the fuel type.
    if fuel_type in _RENEWABLE_FUELS:
        return fuel_type.value

    # For nuclear and hydro (single-band), just use the fuel type.
    if fuel_type in (FuelType.NUCLEAR, FuelType.HYDRO):
        return fuel_type.value

    # For coal (multi-band), include the band.
    return f"{fuel_type.value}_{band.value}"


def classify_generator(
    gen: RtsGmlcGenerator,
    thresholds: list[CapacityBandThreshold],
) -> str | None:
    """Classify a single RTS-GMLC generator into a technology class string.

    Maps the generator's fuel and unit type to a FuelType, then finds the
    matching capacity band using the thresholds. Returns a technology class
    string like "coal_large" or "gas_CT_small". Returns None for generators
    that should be excluded (e.g., SYNC_COND units).

    Args:
        gen: A parsed RTS-GMLC generator record.
        thresholds: Capacity band thresholds from build_capacity_band_thresholds.

    Returns:
        A technology class string, or None if the generator should be excluded.
    """
    if gen.unit_type in _EXCLUDED_UNIT_TYPES:
        return None

    fuel_type = _map_fuel(gen.fuel)
    if fuel_type is None:
        return None

    # Find matching capacity band for this fuel type.
    fuel_thresholds = [t for t in thresholds if t.fuel_type == fuel_type]
    if not fuel_thresholds:
        return None

    # Sort by min_mw to ensure we check in order.
    fuel_thresholds.sort(key=lambda t: t.min_mw)

    matched_band: CapacityBand | None = None
    for i, threshold in enumerate(fuel_thresholds):
        is_last = i == len(fuel_thresholds) - 1
        if is_last:
            # Last band: inclusive upper bound.
            if gen.pmax_mw >= threshold.min_mw:
                matched_band = threshold.band
                break
        else:
            if threshold.min_mw <= gen.pmax_mw < threshold.max_mw:
                matched_band = threshold.band
                break

    if matched_band is None:
        return None

    return _build_tech_class_name(fuel_type, gen.unit_type, matched_band)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def compute_startup_cost(
    startup_heat_mbtu: float,
    fuel_price_dollar_per_mmbtu: float,
    non_fuel_start_cost_dollar: float,
) -> float:
    """Compute total startup cost from heat rate, fuel price, and non-fuel cost.

    Formula: startup_cost = startup_heat_mbtu * fuel_price + non_fuel_start_cost

    (RTS-GMLC startup heat is already in MBTU, and fuel price is $/MMBTU,
    so the product gives $.)

    Args:
        startup_heat_mbtu: Startup heat requirement in MBTU.
        fuel_price_dollar_per_mmbtu: Fuel price in $/MMBTU.
        non_fuel_start_cost_dollar: Non-fuel startup cost in $.

    Returns:
        Total startup cost in dollars.
    """
    return startup_heat_mbtu * fuel_price_dollar_per_mmbtu + non_fuel_start_cost_dollar


def _median(values: list[float]) -> float:
    """Compute median of a list of floats. Returns 0.0 for empty lists."""
    if not values:
        return 0.0
    return statistics.median(values)


def aggregate_tech_class(
    tech_class: str,
    generators: list[RtsGmlcGenerator],
    thresholds: list[CapacityBandThreshold],
) -> TechClassRow:
    """Aggregate parameters from multiple generators in the same technology class.

    Uses median for all numeric parameters to be robust against outliers.
    Computes startup costs using compute_startup_cost for each generator,
    then takes the median. Records capacity band boundaries from the
    matching threshold. Records the count and GEN UIDs of source generators.

    For renewable classes (wind, solar), all temporal parameters are set to 0.

    Args:
        tech_class: The technology class string (e.g., "coal_large").
        generators: All RTS-GMLC generators classified into this tech class.
        thresholds: Capacity band thresholds for deriving band boundaries.

    Returns:
        A TechClassRow with aggregated parameters.

    Raises:
        ValueError: If generators list is empty.
    """
    if not generators:
        msg = f"Cannot aggregate empty generator list for tech class '{tech_class}'"
        raise ValueError(msg)

    # Determine fuel_type, unit_type, and capacity band from the first generator.
    first = generators[0]
    fuel_type = _map_fuel(first.fuel)
    if fuel_type is None:
        msg = f"Unknown fuel type '{first.fuel}' in tech class '{tech_class}'"
        raise ValueError(msg)

    unit_type_str = first.unit_type
    is_renewable = fuel_type.value in _RENEWABLE_FUELS

    # Find matching capacity band threshold.
    fuel_thresholds = [t for t in thresholds if t.fuel_type == fuel_type]
    fuel_thresholds.sort(key=lambda t: t.min_mw)

    # Match on median pmax.
    median_pmax = _median([g.pmax_mw for g in generators])
    band_min = 0.0
    band_max = float("inf")
    band_name = "small"

    for i, threshold in enumerate(fuel_thresholds):
        is_last = i == len(fuel_thresholds) - 1
        if is_last:
            if median_pmax >= threshold.min_mw:
                band_min = threshold.min_mw
                band_max = threshold.max_mw
                band_name = threshold.band.value
                break
        else:
            if threshold.min_mw <= median_pmax < threshold.max_mw:
                band_min = threshold.min_mw
                band_max = threshold.max_mw
                band_name = threshold.band.value
                break

    gen_uids = sorted(g.gen_uid for g in generators)

    if is_renewable:
        return TechClassRow(
            tech_class=tech_class,
            fuel_type=fuel_type.value,
            unit_type=unit_type_str,
            capacity_band=band_name,
            pmax_template_mw=median_pmax,
            pmin_template_mw=_median([g.pmin_mw for g in generators]),
            ramp_rate_mw_per_min=0.0,
            ramp_rate_mw_per_hr=0.0,
            min_up_time_hr=0.0,
            min_down_time_hr=0.0,
            startup_time_cold_hr=0.0,
            startup_time_warm_hr=0.0,
            startup_time_hot_hr=0.0,
            startup_cost_cold_dollar=0.0,
            startup_cost_warm_dollar=0.0,
            startup_cost_hot_dollar=0.0,
            shutdown_cost_dollar=0.0,
            capacity_band_min_mw=band_min,
            capacity_band_max_mw=band_max,
            generator_count=len(generators),
            source_gen_uids=gen_uids,
        )

    # Compute startup costs per generator, then take medians.
    cold_costs = [
        compute_startup_cost(
            g.startup_heat_cold_mbtu, g.fuel_price_dollar_per_mmbtu, g.non_fuel_start_cost_dollar
        )
        for g in generators
    ]
    warm_costs = [
        compute_startup_cost(
            g.startup_heat_warm_mbtu, g.fuel_price_dollar_per_mmbtu, g.non_fuel_start_cost_dollar
        )
        for g in generators
    ]
    hot_costs = [
        compute_startup_cost(
            g.startup_heat_hot_mbtu, g.fuel_price_dollar_per_mmbtu, g.non_fuel_start_cost_dollar
        )
        for g in generators
    ]

    ramp_rate = _median([g.ramp_rate_mw_per_min for g in generators])

    return TechClassRow(
        tech_class=tech_class,
        fuel_type=fuel_type.value,
        unit_type=unit_type_str,
        capacity_band=band_name,
        pmax_template_mw=median_pmax,
        pmin_template_mw=_median([g.pmin_mw for g in generators]),
        ramp_rate_mw_per_min=ramp_rate,
        ramp_rate_mw_per_hr=ramp_rate * 60.0,
        min_up_time_hr=_median([g.min_up_time_hr for g in generators]),
        min_down_time_hr=_median([g.min_down_time_hr for g in generators]),
        startup_time_cold_hr=_median([g.startup_time_cold_hr for g in generators]),
        startup_time_warm_hr=_median([g.startup_time_warm_hr for g in generators]),
        startup_time_hot_hr=_median([g.startup_time_hot_hr for g in generators]),
        startup_cost_cold_dollar=_median(cold_costs),
        startup_cost_warm_dollar=_median(warm_costs),
        startup_cost_hot_dollar=_median(hot_costs),
        shutdown_cost_dollar=_median([g.non_fuel_shutdown_cost_dollar for g in generators]),
        capacity_band_min_mw=band_min,
        capacity_band_max_mw=band_max,
        generator_count=len(generators),
        source_gen_uids=gen_uids,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def build_reference_table(
    generators: list[RtsGmlcGenerator],
) -> ReferenceTableResult:
    """Build the complete reference table from parsed RTS-GMLC generators.

    Orchestrates the full pipeline: builds capacity band thresholds, classifies
    each generator, groups by technology class, aggregates parameters, and
    assembles the result with provenance metadata.

    Args:
        generators: All parsed RTS-GMLC generator records.

    Returns:
        A ReferenceTableResult containing the tech class rows, thresholds,
        excluded generators, and any warnings.
    """
    thresholds = build_capacity_band_thresholds()
    warnings: list[str] = []

    # Classify each generator.
    classified: dict[str, list[RtsGmlcGenerator]] = {}
    excluded_uids: list[str] = []

    for gen in generators:
        tech_class = classify_generator(gen, thresholds)
        if tech_class is None:
            excluded_uids.append(gen.gen_uid)
            continue
        classified.setdefault(tech_class, []).append(gen)

    # Aggregate each technology class.
    tech_classes: list[TechClassRow] = []
    for tc_name in sorted(classified.keys()):
        tc_gens = classified[tc_name]
        row = aggregate_tech_class(tc_name, tc_gens, thresholds)
        tech_classes.append(row)

    # Sort by fuel_type then capacity_band for stable output.
    tech_classes.sort(key=lambda r: (r.fuel_type, r.capacity_band))

    provenance = RtsGmlcProvenance(
        repo_url=RTS_GMLC_REPO_URL,
        commit_hash="",  # Filled in by caller.
        file_path=RTS_GMLC_FILE_PATH,
        download_timestamp=datetime.now(tz=timezone.utc).isoformat(),
        script_version=__version__,
        num_generators_parsed=len(generators),
        num_tech_classes_produced=len(tech_classes),
    )

    return ReferenceTableResult(
        provenance=provenance,
        tech_classes=tech_classes,
        capacity_band_thresholds=thresholds,
        excluded_gen_uids=sorted(excluded_uids),
        warnings=warnings,
    )


def write_reference_csv(
    result: ReferenceTableResult,
    dest_path: Path,
    *,
    provenance: RtsGmlcProvenance,
) -> None:
    """Write the reference table to a CSV file with provenance header.

    The first lines of the CSV are comment lines (starting with #) containing
    provenance metadata. Followed by the CSV header row and data rows.

    Args:
        result: The complete reference table result.
        dest_path: File path to write the CSV output.
        provenance: Provenance metadata for the header comments.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    # Provenance header comments.
    lines.append("# RTS-GMLC Technology Class Reference Table")
    lines.append(f"# Repository: {provenance.repo_url}")
    lines.append(f"# Commit: {provenance.commit_hash}")
    lines.append(f"# Source file: {provenance.file_path}")
    lines.append(f"# Download timestamp: {provenance.download_timestamp}")
    lines.append(f"# Script version: {provenance.script_version}")
    lines.append(f"# Generators parsed: {provenance.num_generators_parsed}")
    lines.append(f"# Technology classes: {provenance.num_tech_classes_produced}")
    lines.append("#")

    # Write CSV content using csv module.
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_OUTPUT_COLUMNS)
    writer.writeheader()

    for row in result.tech_classes:
        row_dict = asdict(row)
        # Remove source_gen_uids from CSV output.
        row_dict.pop("source_gen_uids", None)
        writer.writerow(row_dict)

    lines.append(output.getvalue().rstrip("\n"))

    dest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(result: ReferenceTableResult) -> None:
    """Print a human-readable summary of the reference table to stdout.

    Lists each technology class with its generator count and key parameters.
    Flags any excluded generators and warnings.

    Args:
        result: The complete reference table result.
    """
    print("=" * 72)
    print("RTS-GMLC Technology Class Reference Table Summary")
    print("=" * 72)
    print(f"Generators parsed: {result.provenance.num_generators_parsed}")
    print(f"Technology classes: {result.provenance.num_tech_classes_produced}")
    print(f"Excluded generators: {len(result.excluded_gen_uids)}")
    print()

    fmt = "{:<20s} {:>5d}  {:>8.1f}  {:>8.2f}  {:>6.1f}  {:>6.1f}"
    header = f"{'Tech Class':<20s} {'Count':>5s}  {'Pmax MW':>8s}  {'Ramp/min':>8s}  {'MinUp':>6s}  {'MinDn':>6s}"  # noqa: E501
    print(header)
    print("-" * len(header))

    for tc in result.tech_classes:
        print(
            fmt.format(
                tc.tech_class,
                tc.generator_count,
                tc.pmax_template_mw,
                tc.ramp_rate_mw_per_min,
                tc.min_up_time_hr,
                tc.min_down_time_hr,
            )
        )

    if result.excluded_gen_uids:
        print(f"\nExcluded GEN UIDs: {', '.join(result.excluded_gen_uids)}")

    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")

    print()


def main(
    output_dir: Path | None = None,
    *,
    commit_hash: str = "v0.2.3",
) -> ReferenceTableResult:
    """Entry point: download gen.csv, build reference table, write output.

    Orchestrates the full workflow:
    1. Download gen.csv from RTS-GMLC at the pinned commit.
    2. Parse into generator records.
    3. Build the reference table (classify, aggregate).
    4. Write the CSV to data/reference/rts_gmlc_tech_classes.csv.
    5. Print the summary.

    Args:
        output_dir: Base directory for output. Defaults to
            <repo_root>/data/reference/.
        commit_hash: RTS-GMLC commit hash or tag to pin. Defaults to "v0.2.3"
            pending resolution of OQ-P2-01.

    Returns:
        The complete ReferenceTableResult.
    """
    if output_dir is None:
        # Default: data/reference/ relative to this script's repo root.
        repo_root = Path(__file__).resolve().parent.parent
        output_dir = repo_root / "reference"

    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Download.
    gen_csv_path = download_rts_gmlc_gen_csv(
        raw_dir / "gen.csv",
        commit_hash=commit_hash,
    )

    # Step 2: Parse.
    generators = parse_gen_csv(gen_csv_path)

    # Step 3: Build reference table.
    result = build_reference_table(generators)

    # Update provenance with commit hash.
    result = ReferenceTableResult(
        provenance=RtsGmlcProvenance(
            repo_url=result.provenance.repo_url,
            commit_hash=commit_hash,
            file_path=result.provenance.file_path,
            download_timestamp=result.provenance.download_timestamp,
            script_version=result.provenance.script_version,
            num_generators_parsed=result.provenance.num_generators_parsed,
            num_tech_classes_produced=result.provenance.num_tech_classes_produced,
        ),
        tech_classes=result.tech_classes,
        capacity_band_thresholds=result.capacity_band_thresholds,
        excluded_gen_uids=result.excluded_gen_uids,
        warnings=result.warnings,
    )

    # Step 4: Write CSV.
    output_csv = output_dir / "rts_gmlc_tech_classes.csv"
    write_reference_csv(result, output_csv, provenance=result.provenance)

    # Step 5: Print summary.
    print_summary(result)

    return result


if __name__ == "__main__":
    main()
