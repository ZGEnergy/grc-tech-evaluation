"""RTS-GMLC Storage Parameter Reference Table builder.

Downloads the RTS-GMLC gen.csv and storage.csv from the GridMod GitHub repository,
extracts storage unit parameters, derives the complete BESS parameter set (including
charge/discharge efficiency decomposition, SoC bounds, duration, and reserve eligibility),
and writes the result to a canonical reference CSV with provenance metadata.

The RTS-GMLC storage unit (313_STORAGE_1) serves as a template for parameterizing
BESS units in downstream network augmentation deliverables.
"""

from __future__ import annotations

import csv
import io
import math
import sys
from dataclasses import dataclass
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
RTS_GMLC_GEN_RAW_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/GridMod/RTS-GMLC/{commit_hash}/RTS_Data/SourceData/gen.csv"
)
RTS_GMLC_STORAGE_RAW_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/GridMod/RTS-GMLC"
    "/{commit_hash}/RTS_Data/SourceData/storage.csv"
)
RTS_GMLC_GEN_FILE_PATH = "RTS_Data/SourceData/gen.csv"
RTS_GMLC_STORAGE_FILE_PATH = "RTS_Data/SourceData/storage.csv"

# Required columns in gen.csv for storage parsing (after whitespace stripping).
REQUIRED_GEN_COLUMNS = frozenset(
    {
        "GEN UID",
        "Bus ID",
        "Unit Type",
        "Category",
        "PMax MW",
        "PMin MW",
        "Ramp Rate MW/Min",
    }
)

# Required columns in storage.csv (after whitespace stripping).
REQUIRED_STORAGE_COLUMNS = frozenset(
    {
        "GEN UID",
        "Max Volume GWh",
        "Initial Volume GWh",
    }
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class StorageTechClass(StrEnum):
    """Storage technology classes recognized in the RTS-GMLC fleet.

    Currently only one class exists (generic battery/pumped storage).
    The enum is defined for forward compatibility if additional storage
    technologies are added in future phases.
    """

    BATTERY = "battery"


class ParameterScaleType(StrEnum):
    """Classification of a parameter as intensive or extensive.

    Intensive parameters are scale-independent and are copied unchanged
    when creating BESS units of different sizes (e.g., efficiency, SoC bounds).
    Extensive parameters scale linearly with the unit's power or energy
    rating relative to the template (e.g., power_mw, energy_mwh, ramp_rate).
    """

    INTENSIVE = "intensive"
    EXTENSIVE = "extensive"


@dataclass(frozen=True)
class StorageParameterMeta:
    """Metadata for a single storage parameter: name, units, and scale type.

    Used to document the intensive/extensive classification in the output
    CSV and to drive scaling logic in downstream deliverables.
    """

    name: str  # snake_case parameter name, e.g. "power_mw"
    units: str  # human-readable units, e.g. "MW", "MWh", "fraction", "bool"
    scale_type: ParameterScaleType
    source: str  # provenance: "gen.csv", "storage.csv", "derived", or "default"
    description: str  # one-line description


@dataclass(frozen=True)
class RtsGmlcStorageUnit:
    """A single storage unit row parsed from RTS-GMLC gen.csv + storage.csv.

    Represents the raw extracted values before any derivation or default
    assignment. Fields that are not present in the source files are None.
    """

    gen_uid: str  # e.g., "313_STORAGE_1"
    bus_id: int
    unit_type: str  # "STORAGE"
    category: str  # "Storage"
    pmax_mw: float  # from gen.csv PMax MW
    pmin_mw: float  # from gen.csv PMin MW
    ramp_rate_mw_per_min: float  # from gen.csv Ramp Rate MW/Min
    roundtrip_efficiency_pct: float  # from gen.csv Storage Roundtrip Efficiency
    max_volume_gwh: float  # from storage.csv Max Volume GWh (head storage)
    initial_volume_gwh: float  # from storage.csv Initial Volume GWh (head storage)
    inflow_limit_gwh: float  # from storage.csv Inflow Limit GWh (head storage)


@dataclass(frozen=True)
class StorageParamRow:
    """A single row in the output reference table: one storage technology class.

    Contains both the raw extracted values and derived/default parameters.
    All efficiency values are dimensionless fractions [0, 1]. SoC values
    are fractions of energy capacity [0, 1].
    """

    tech_class: str  # StorageTechClass value, e.g. "battery"
    gen_uid: str  # source RTS-GMLC GEN UID
    power_mw: float  # template power rating (charge and discharge, symmetric)
    energy_mwh: float  # template energy capacity
    duration_hr: float  # energy_mwh / power_mw
    roundtrip_efficiency: float  # dimensionless [0, 1], from source
    charge_efficiency: float  # dimensionless [0, 1], derived
    discharge_efficiency: float  # dimensionless [0, 1], derived
    min_soc: float  # fraction of energy_mwh, default
    max_soc: float  # fraction of energy_mwh, default
    init_soc: float  # fraction of energy_mwh, default
    cyclic_soc: bool  # enforce SoC(t=24) == SoC(t=1)
    ramp_rate_mw_per_min: float  # from source
    ramp_rate_mw_per_hr: float  # ramp_rate_mw_per_min * 60
    spinning_eligible: bool  # eligible to provide spinning reserve
    non_spinning_eligible: bool  # eligible to provide non-spinning reserve
    generator_count: int  # number of RTS-GMLC storage units in this class
    source_gen_uids: list[str]  # GEN UIDs of source units


@dataclass(frozen=True)
class StorageProvenance:
    """Provenance metadata for the RTS-GMLC storage data extraction."""

    repo_url: str  # e.g., "https://github.com/GridMod/RTS-GMLC"
    commit_hash: str
    gen_csv_path: str  # e.g., "RTS_Data/SourceData/gen.csv"
    storage_csv_path: str  # e.g., "RTS_Data/SourceData/storage.csv"
    download_timestamp: str  # ISO 8601
    script_version: str
    num_storage_units_parsed: int
    num_rows_produced: int


@dataclass(frozen=True)
class StorageReferenceResult:
    """Complete result of building the storage parameter reference table."""

    provenance: StorageProvenance
    params: list[StorageParamRow]
    parameter_metadata: list[StorageParameterMeta]
    warnings: list[str]


# --- Constants ---

STORAGE_PARAMETER_METADATA: list[StorageParameterMeta] = [
    StorageParameterMeta(
        name="power_mw",
        units="MW",
        scale_type=ParameterScaleType.EXTENSIVE,
        source="gen.csv",
        description="Charge and discharge power rating (symmetric)",
    ),
    StorageParameterMeta(
        name="energy_mwh",
        units="MWh",
        scale_type=ParameterScaleType.EXTENSIVE,
        source="storage.csv",
        description="Usable energy capacity",
    ),
    StorageParameterMeta(
        name="duration_hr",
        units="hr",
        scale_type=ParameterScaleType.INTENSIVE,
        source="derived",
        description="Energy capacity divided by power rating",
    ),
    StorageParameterMeta(
        name="roundtrip_efficiency",
        units="fraction",
        scale_type=ParameterScaleType.INTENSIVE,
        source="gen.csv",
        description="Round-trip AC-to-AC efficiency",
    ),
    StorageParameterMeta(
        name="charge_efficiency",
        units="fraction",
        scale_type=ParameterScaleType.INTENSIVE,
        source="derived",
        description="One-way charging efficiency (sqrt of roundtrip)",
    ),
    StorageParameterMeta(
        name="discharge_efficiency",
        units="fraction",
        scale_type=ParameterScaleType.INTENSIVE,
        source="derived",
        description="One-way discharging efficiency (sqrt of roundtrip)",
    ),
    StorageParameterMeta(
        name="min_soc",
        units="fraction",
        scale_type=ParameterScaleType.INTENSIVE,
        source="default",
        description="Minimum state of charge as fraction of energy capacity",
    ),
    StorageParameterMeta(
        name="max_soc",
        units="fraction",
        scale_type=ParameterScaleType.INTENSIVE,
        source="default",
        description="Maximum state of charge as fraction of energy capacity",
    ),
    StorageParameterMeta(
        name="init_soc",
        units="fraction",
        scale_type=ParameterScaleType.INTENSIVE,
        source="default",
        description="Initial state of charge as fraction of energy capacity",
    ),
    StorageParameterMeta(
        name="cyclic_soc",
        units="bool",
        scale_type=ParameterScaleType.INTENSIVE,
        source="default",
        description="Enforce SoC at hour 24 equals SoC at hour 1",
    ),
    StorageParameterMeta(
        name="ramp_rate_mw_per_min",
        units="MW/min",
        scale_type=ParameterScaleType.EXTENSIVE,
        source="gen.csv",
        description="Maximum ramp rate for charge and discharge",
    ),
    StorageParameterMeta(
        name="ramp_rate_mw_per_hr",
        units="MW/hr",
        scale_type=ParameterScaleType.EXTENSIVE,
        source="derived",
        description="Ramp rate converted to hourly (ramp_rate_mw_per_min * 60)",
    ),
    StorageParameterMeta(
        name="spinning_eligible",
        units="bool",
        scale_type=ParameterScaleType.INTENSIVE,
        source="default",
        description="Eligible to provide spinning reserve",
    ),
    StorageParameterMeta(
        name="non_spinning_eligible",
        units="bool",
        scale_type=ParameterScaleType.INTENSIVE,
        source="default",
        description="Eligible to provide non-spinning reserve",
    ),
]
"""Metadata for every parameter in the output CSV, documenting units,
scale type (intensive/extensive), and provenance (source file or derivation)."""

DEFAULT_MIN_SOC: float = 0.10
"""Minimum SoC floor (fraction). 10% prevents deep discharge damage."""

DEFAULT_MAX_SOC: float = 0.90
"""Maximum SoC ceiling (fraction). 90% prevents overcharge stress."""

DEFAULT_INIT_SOC: float = 0.50
"""Initial SoC (fraction). 50% gives the optimizer freedom in hour 1."""

DEFAULT_CYCLIC_SOC: bool = True
"""Enforce cyclic SoC boundary condition (SoC at t=24 == SoC at t=1)."""

DEFAULT_SPINNING_ELIGIBLE: bool = True
"""BESS is eligible for spinning reserves (can respond within 10 min)."""

DEFAULT_NON_SPINNING_ELIGIBLE: bool = True
"""BESS is eligible for non-spinning reserves (can respond from idle)."""

# CSV output column order
_OUTPUT_COLUMNS = [
    "tech_class",
    "gen_uid",
    "power_mw",
    "energy_mwh",
    "duration_hr",
    "roundtrip_efficiency",
    "charge_efficiency",
    "discharge_efficiency",
    "min_soc",
    "max_soc",
    "init_soc",
    "cyclic_soc",
    "ramp_rate_mw_per_min",
    "ramp_rate_mw_per_hr",
    "spinning_eligible",
    "non_spinning_eligible",
    "generator_count",
    "source_gen_uids",
]


# ---------------------------------------------------------------------------
# Download and parse
# ---------------------------------------------------------------------------


def download_rts_gmlc_storage_csv(
    dest_path: Path,
    *,
    commit_hash: str,
    timeout_seconds: int = 60,
) -> Path:
    """Download storage.csv from the RTS-GMLC GitHub repository at a pinned commit.

    Fetches the raw file from:
        https://raw.githubusercontent.com/GridMod/RTS-GMLC/{commit_hash}/
        RTS_Data/SourceData/storage.csv

    If dest_path already exists, skips the download and returns the existing
    path (idempotent). Creates parent directories if needed.

    Args:
        dest_path: Local file path to write the downloaded CSV.
        commit_hash: Git commit hash or tag to pin the download to.
        timeout_seconds: HTTP request timeout.

    Returns:
        The path to the downloaded (or existing) file.

    Raises:
        ConnectionError: If the download fails after retries.
        ValueError: If the downloaded content does not appear to be a valid CSV
            (e.g., missing expected header columns like 'GEN UID').
    """
    if dest_path.exists():
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    url = RTS_GMLC_STORAGE_RAW_URL_TEMPLATE.format(commit_hash=commit_hash)
    request = Request(url, headers={"User-Agent": "grc-tech-evaluation"})  # noqa: S310

    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            content = response.read().decode("utf-8")
    except (URLError, TimeoutError) as exc:
        msg = f"Failed to download RTS-GMLC storage.csv from {url}: {exc}"
        raise ConnectionError(msg) from exc

    # Basic validation: check for expected header columns.
    first_line = content.split("\n", maxsplit=1)[0]
    header_cols = {col.strip() for col in first_line.split(",")}
    missing = REQUIRED_STORAGE_COLUMNS - header_cols
    if missing:
        msg = f"Downloaded storage CSV is missing required columns: {sorted(missing)}"
        raise ValueError(msg)

    dest_path.write_text(content, encoding="utf-8")
    return dest_path


def download_rts_gmlc_gen_csv(
    dest_path: Path,
    *,
    commit_hash: str,
    timeout_seconds: int = 60,
) -> Path:
    """Download gen.csv from the RTS-GMLC GitHub repository at a pinned commit.

    If dest_path already exists (e.g., cached by Phase 2 D1), skips the
    download and returns the existing path. Creates parent directories if needed.

    Args:
        dest_path: Local file path to write the downloaded CSV.
        commit_hash: Git commit hash or tag to pin the download to.
        timeout_seconds: HTTP request timeout.

    Returns:
        The path to the downloaded (or existing) file.

    Raises:
        ConnectionError: If the download fails after retries.
        ValueError: If the downloaded content does not appear to be a valid CSV.
    """
    if dest_path.exists():
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    url = RTS_GMLC_GEN_RAW_URL_TEMPLATE.format(commit_hash=commit_hash)
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
    missing = REQUIRED_GEN_COLUMNS - header_cols
    if missing:
        msg = f"Downloaded gen CSV is missing required columns: {sorted(missing)}"
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
            f"for unit '{gen_uid}', using 0.0",
            file=sys.stderr,
        )
        return 0.0


def parse_storage_from_gen_csv(csv_path: Path) -> list[RtsGmlcStorageUnit]:
    """Parse storage unit rows from the RTS-GMLC gen.csv.

    Filters rows where Category == "Storage" or Unit Type == "STORAGE".
    Handles the leading-space column name quirk by stripping whitespace
    from all header names. Extracts power, ramp rate, and round-trip
    efficiency fields.

    The RTS-GMLC v3.2 gen.csv contains exactly one storage unit
    (313_STORAGE_1, 50 MW, 85% round-trip efficiency). The function
    returns partial RtsGmlcStorageUnit records with energy fields set
    to 0.0 -- these are populated by join_storage_sources.

    Args:
        csv_path: Path to the gen.csv file.

    Returns:
        A list of partially populated RtsGmlcStorageUnit records (one per
        storage row found in gen.csv).

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns (GEN UID, PMax MW, Category,
            Storage Roundtrip Efficiency) are missing.
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
    missing = REQUIRED_GEN_COLUMNS - header_set
    if missing:
        msg = f"gen.csv is missing required columns: {sorted(missing)}"
        raise ValueError(msg)

    units: list[RtsGmlcStorageUnit] = []
    for row in reader:
        # Strip keys to handle any residual whitespace.
        row = {k.strip(): v for k, v in row.items()}

        gen_uid = row.get("GEN UID", "").strip()
        if not gen_uid:
            continue

        category = row.get("Category", "").strip()
        unit_type = row.get("Unit Type", "").strip()

        # Filter for storage units.
        if category != "Storage" and unit_type != "STORAGE":
            continue

        # Extract round-trip efficiency -- column may or may not exist.
        rte_str = row.get("Storage Roundtrip Efficiency", "0").strip()
        rte_pct = _safe_float(rte_str, "Storage Roundtrip Efficiency", gen_uid)

        unit = RtsGmlcStorageUnit(
            gen_uid=gen_uid,
            bus_id=int(_safe_float(row["Bus ID"], "Bus ID", gen_uid)),
            unit_type=unit_type,
            category=category,
            pmax_mw=_safe_float(row["PMax MW"], "PMax MW", gen_uid),
            pmin_mw=_safe_float(row["PMin MW"], "PMin MW", gen_uid),
            ramp_rate_mw_per_min=_safe_float(row["Ramp Rate MW/Min"], "Ramp Rate MW/Min", gen_uid),
            roundtrip_efficiency_pct=rte_pct,
            max_volume_gwh=0.0,
            initial_volume_gwh=0.0,
            inflow_limit_gwh=0.0,
        )
        units.append(unit)

    return units


def parse_storage_csv(csv_path: Path) -> dict[str, dict[str, float]]:
    """Parse the RTS-GMLC storage.csv into a lookup of energy parameters.

    Returns a dict keyed by GEN UID, where each value is a dict containing:
    - max_volume_gwh: from the "head" position row's Max Volume GWh
    - initial_volume_gwh: from the "head" position row's Initial Volume GWh
    - inflow_limit_gwh: from the "head" position row's Inflow Limit GWh

    For units with both head and tail storage rows (e.g., 313_STORAGE_1),
    only the head row is used for energy capacity (the tail row is the
    lower reservoir in pumped hydro, not relevant for generic BESS modeling).

    Args:
        csv_path: Path to the storage.csv file.

    Returns:
        A dict mapping GEN UID to energy parameter dicts.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns (GEN UID, Max Volume GWh, position)
            are missing.
    """
    if not csv_path.exists():
        msg = f"File not found: {csv_path}"
        raise FileNotFoundError(msg)

    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        msg = "CSV file has no header row"
        raise ValueError(msg)

    stripped_fields = [f.strip() for f in reader.fieldnames]
    reader.fieldnames = stripped_fields

    header_set = set(stripped_fields)
    missing = REQUIRED_STORAGE_COLUMNS - header_set
    if missing:
        msg = f"storage.csv is missing required columns: {sorted(missing)}"
        raise ValueError(msg)

    result: dict[str, dict[str, float]] = {}

    for row in reader:
        row = {k.strip(): v for k, v in row.items()}

        gen_uid = row.get("GEN UID", "").strip()
        if not gen_uid:
            continue

        # Only use the "head" position row (or the first row if no position column).
        position = row.get("Storage", "").strip().lower()
        if position and position != "head":
            continue

        # Don't overwrite if we already have the head row for this UID.
        if gen_uid in result:
            continue

        inflow_str = row.get("Inflow Limit GWh", "0").strip()

        result[gen_uid] = {
            "max_volume_gwh": _safe_float(row["Max Volume GWh"], "Max Volume GWh", gen_uid),
            "initial_volume_gwh": _safe_float(
                row["Initial Volume GWh"], "Initial Volume GWh", gen_uid
            ),
            "inflow_limit_gwh": _safe_float(inflow_str, "Inflow Limit GWh", gen_uid),
        }

    return result


def join_storage_sources(
    gen_units: list[RtsGmlcStorageUnit],
    storage_params: dict[str, dict[str, float]],
) -> list[RtsGmlcStorageUnit]:
    """Join gen.csv storage rows with storage.csv energy parameters.

    For each storage unit from gen.csv, looks up the matching GEN UID in
    storage_params and populates the energy capacity fields (max_volume_gwh,
    initial_volume_gwh, inflow_limit_gwh). Units with no match in
    storage.csv are returned with energy fields at 0.0 and a warning
    is printed.

    Args:
        gen_units: Partially populated storage units from parse_storage_from_gen_csv.
        storage_params: Energy parameters from parse_storage_csv.

    Returns:
        A list of fully populated RtsGmlcStorageUnit records.

    Raises:
        ValueError: If gen_units is empty (no storage units found in gen.csv).
    """
    if not gen_units:
        msg = "No storage units found in gen.csv"
        raise ValueError(msg)

    joined: list[RtsGmlcStorageUnit] = []
    for unit in gen_units:
        params = storage_params.get(unit.gen_uid)
        if params is None:
            print(
                f"WARNING: No storage.csv entry for {unit.gen_uid}, energy fields will be 0.0",
                file=sys.stderr,
            )
            joined.append(unit)
            continue

        joined.append(
            RtsGmlcStorageUnit(
                gen_uid=unit.gen_uid,
                bus_id=unit.bus_id,
                unit_type=unit.unit_type,
                category=unit.category,
                pmax_mw=unit.pmax_mw,
                pmin_mw=unit.pmin_mw,
                ramp_rate_mw_per_min=unit.ramp_rate_mw_per_min,
                roundtrip_efficiency_pct=unit.roundtrip_efficiency_pct,
                max_volume_gwh=params["max_volume_gwh"],
                initial_volume_gwh=params["initial_volume_gwh"],
                inflow_limit_gwh=params["inflow_limit_gwh"],
            )
        )

    return joined


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


def decompose_roundtrip_efficiency(
    roundtrip_efficiency: float,
) -> tuple[float, float]:
    """Decompose round-trip efficiency into charge and discharge components.

    Uses the symmetric square-root split:
        charge_efficiency = sqrt(roundtrip_efficiency)
        discharge_efficiency = sqrt(roundtrip_efficiency)

    This is the standard decomposition when individual charge/discharge
    efficiencies are not separately measured. The product of the two
    components equals the original round-trip efficiency.

    Args:
        roundtrip_efficiency: Round-trip efficiency as a fraction [0, 1].

    Returns:
        A tuple of (charge_efficiency, discharge_efficiency), both as
        fractions [0, 1].

    Raises:
        ValueError: If roundtrip_efficiency is not in (0, 1].
    """
    if roundtrip_efficiency <= 0.0 or roundtrip_efficiency > 1.0:
        msg = f"roundtrip_efficiency must be in (0, 1], got {roundtrip_efficiency}"
        raise ValueError(msg)

    sqrt_eff = math.sqrt(roundtrip_efficiency)
    return (sqrt_eff, sqrt_eff)


def build_storage_param_row(
    unit: RtsGmlcStorageUnit,
) -> StorageParamRow:
    """Build a reference table row from a parsed RTS-GMLC storage unit.

    Applies the following transformations:
    1. Converts energy from GWh to MWh (multiply by 1000).
    2. Computes duration_hr = energy_mwh / power_mw.
    3. Converts roundtrip_efficiency_pct to a fraction (divide by 100).
    4. Decomposes round-trip efficiency into charge/discharge via
       decompose_roundtrip_efficiency.
    5. Assigns domain defaults for min_soc, max_soc, init_soc, cyclic_soc.
    6. Computes ramp_rate_mw_per_hr = ramp_rate_mw_per_min * 60.
    7. Sets reserve eligibility flags to True.
    8. Assigns tech_class = "battery".

    Args:
        unit: A fully populated RtsGmlcStorageUnit record.

    Returns:
        A StorageParamRow with all fields populated.

    Raises:
        ValueError: If power_mw <= 0 or energy capacity <= 0.
    """
    if unit.pmax_mw <= 0.0:
        msg = f"power_mw must be positive, got {unit.pmax_mw} for {unit.gen_uid}"
        raise ValueError(msg)

    energy_mwh = unit.max_volume_gwh * 1000.0
    if energy_mwh <= 0.0:
        msg = (
            f"energy capacity must be positive, got {energy_mwh} MWh "
            f"(from {unit.max_volume_gwh} GWh) for {unit.gen_uid}"
        )
        raise ValueError(msg)

    duration_hr = energy_mwh / unit.pmax_mw
    roundtrip_eff = unit.roundtrip_efficiency_pct / 100.0
    charge_eff, discharge_eff = decompose_roundtrip_efficiency(roundtrip_eff)

    return StorageParamRow(
        tech_class=StorageTechClass.BATTERY.value,
        gen_uid=unit.gen_uid,
        power_mw=unit.pmax_mw,
        energy_mwh=energy_mwh,
        duration_hr=duration_hr,
        roundtrip_efficiency=roundtrip_eff,
        charge_efficiency=charge_eff,
        discharge_efficiency=discharge_eff,
        min_soc=DEFAULT_MIN_SOC,
        max_soc=DEFAULT_MAX_SOC,
        init_soc=DEFAULT_INIT_SOC,
        cyclic_soc=DEFAULT_CYCLIC_SOC,
        ramp_rate_mw_per_min=unit.ramp_rate_mw_per_min,
        ramp_rate_mw_per_hr=unit.ramp_rate_mw_per_min * 60.0,
        spinning_eligible=DEFAULT_SPINNING_ELIGIBLE,
        non_spinning_eligible=DEFAULT_NON_SPINNING_ELIGIBLE,
        generator_count=1,
        source_gen_uids=[unit.gen_uid],
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def build_storage_reference(
    gen_csv_path: Path,
    storage_csv_path: Path,
) -> StorageReferenceResult:
    """Build the complete storage parameter reference table.

    Orchestrates the full pipeline: parse gen.csv for storage rows,
    parse storage.csv for energy parameters, join the two sources,
    build the reference row(s), and assemble the result with provenance
    metadata and parameter classification.

    Args:
        gen_csv_path: Path to the cached gen.csv file.
        storage_csv_path: Path to the cached storage.csv file.

    Returns:
        A StorageReferenceResult containing the parameter rows,
        parameter metadata, and any warnings.
    """
    warnings: list[str] = []

    # Parse sources.
    gen_units = parse_storage_from_gen_csv(gen_csv_path)
    storage_params = parse_storage_csv(storage_csv_path)

    # Join.
    joined_units = join_storage_sources(gen_units, storage_params)

    # Build param rows.
    params: list[StorageParamRow] = []
    for unit in joined_units:
        try:
            row = build_storage_param_row(unit)
            params.append(row)
        except ValueError as exc:
            warnings.append(f"Skipped {unit.gen_uid}: {exc}")

    provenance = StorageProvenance(
        repo_url=RTS_GMLC_REPO_URL,
        commit_hash="",  # Filled in by caller.
        gen_csv_path=RTS_GMLC_GEN_FILE_PATH,
        storage_csv_path=RTS_GMLC_STORAGE_FILE_PATH,
        download_timestamp=datetime.now(tz=timezone.utc).isoformat(),
        script_version=__version__,
        num_storage_units_parsed=len(joined_units),
        num_rows_produced=len(params),
    )

    return StorageReferenceResult(
        provenance=provenance,
        params=params,
        parameter_metadata=STORAGE_PARAMETER_METADATA,
        warnings=warnings,
    )


def write_storage_reference_csv(
    result: StorageReferenceResult,
    dest_path: Path,
    *,
    provenance: StorageProvenance,
) -> None:
    """Write the storage parameter reference table to a CSV file.

    The first lines of the CSV are comment lines (starting with #) containing:
    - RTS-GMLC repository URL
    - Commit hash
    - Source file paths (gen.csv and storage.csv)
    - Download timestamp
    - Script version
    - Number of storage units parsed
    - Parameter classification summary (intensive vs extensive)

    Followed by the CSV header row and data rows, one per storage
    technology class.

    Column order: tech_class, gen_uid, power_mw, energy_mwh, duration_hr,
    roundtrip_efficiency, charge_efficiency, discharge_efficiency, min_soc,
    max_soc, init_soc, cyclic_soc, ramp_rate_mw_per_min, ramp_rate_mw_per_hr,
    spinning_eligible, non_spinning_eligible, generator_count, source_gen_uids.

    Boolean columns are written as "true" / "false" (lowercase) for
    consistent parsing across Python, Julia, and Octave.

    Args:
        result: The complete storage reference result.
        dest_path: File path to write the CSV output.
        provenance: Provenance metadata for the header comments.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    # Provenance header comments.
    lines.append("# RTS-GMLC Storage Parameter Reference Table")
    lines.append(f"# Repository: {provenance.repo_url}")
    lines.append(f"# Commit: {provenance.commit_hash}")
    lines.append(f"# Source files: {provenance.gen_csv_path}, {provenance.storage_csv_path}")
    lines.append(f"# Download timestamp: {provenance.download_timestamp}")
    lines.append(f"# Script version: {provenance.script_version}")
    lines.append(f"# Storage units parsed: {provenance.num_storage_units_parsed}")
    lines.append(f"# Rows produced: {provenance.num_rows_produced}")

    # Parameter classification summary.
    intensive = [
        m.name for m in result.parameter_metadata if m.scale_type == ParameterScaleType.INTENSIVE
    ]
    extensive = [
        m.name for m in result.parameter_metadata if m.scale_type == ParameterScaleType.EXTENSIVE
    ]
    lines.append(f"# Intensive parameters: {', '.join(intensive)}")
    lines.append(f"# Extensive parameters: {', '.join(extensive)}")
    lines.append("#")

    # Write CSV content.
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_OUTPUT_COLUMNS)
    writer.writeheader()

    for row in result.params:
        row_dict: dict[str, str] = {
            "tech_class": row.tech_class,
            "gen_uid": row.gen_uid,
            "power_mw": str(row.power_mw),
            "energy_mwh": str(row.energy_mwh),
            "duration_hr": str(row.duration_hr),
            "roundtrip_efficiency": str(row.roundtrip_efficiency),
            "charge_efficiency": str(row.charge_efficiency),
            "discharge_efficiency": str(row.discharge_efficiency),
            "min_soc": str(row.min_soc),
            "max_soc": str(row.max_soc),
            "init_soc": str(row.init_soc),
            "cyclic_soc": str(row.cyclic_soc).lower(),
            "ramp_rate_mw_per_min": str(row.ramp_rate_mw_per_min),
            "ramp_rate_mw_per_hr": str(row.ramp_rate_mw_per_hr),
            "spinning_eligible": str(row.spinning_eligible).lower(),
            "non_spinning_eligible": str(row.non_spinning_eligible).lower(),
            "generator_count": str(row.generator_count),
            "source_gen_uids": ";".join(row.source_gen_uids),
        }
        writer.writerow(row_dict)

    lines.append(output.getvalue().rstrip("\n"))

    dest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_parameter_metadata_csv(
    metadata: list[StorageParameterMeta],
    dest_path: Path,
) -> None:
    """Write the parameter classification metadata to a companion CSV.

    Produces a CSV with columns: name, units, scale_type, source, description.
    One row per parameter. This file documents the intensive/extensive
    classification for downstream scaling logic and for human reference.

    Args:
        metadata: The parameter metadata list (STORAGE_PARAMETER_METADATA).
        dest_path: File path to write the metadata CSV.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    output = io.StringIO()
    fieldnames = ["name", "units", "scale_type", "source", "description"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for meta in metadata:
        writer.writerow(
            {
                "name": meta.name,
                "units": meta.units,
                "scale_type": meta.scale_type.value,
                "source": meta.source,
                "description": meta.description,
            }
        )

    dest_path.write_text(output.getvalue(), encoding="utf-8")


def print_summary(result: StorageReferenceResult) -> None:
    """Print a human-readable summary of the storage reference table to stdout.

    Args:
        result: The complete storage reference result.
    """
    print("=" * 72)
    print("RTS-GMLC Storage Parameter Reference Table Summary")
    print("=" * 72)
    print(f"Storage units parsed: {result.provenance.num_storage_units_parsed}")
    print(f"Rows produced: {result.provenance.num_rows_produced}")
    print()

    for row in result.params:
        print(f"  Tech class: {row.tech_class}")
        print(f"  GEN UID: {row.gen_uid}")
        print(f"  Power: {row.power_mw} MW")
        print(f"  Energy: {row.energy_mwh} MWh")
        print(f"  Duration: {row.duration_hr} hr")
        print(f"  Roundtrip efficiency: {row.roundtrip_efficiency:.4f}")
        print(f"  Charge efficiency: {row.charge_efficiency:.4f}")
        print(f"  Discharge efficiency: {row.discharge_efficiency:.4f}")
        print(f"  SoC bounds: [{row.min_soc}, {row.max_soc}]")
        print(f"  Initial SoC: {row.init_soc}")
        print(f"  Cyclic SoC: {row.cyclic_soc}")
        print(f"  Ramp rate: {row.ramp_rate_mw_per_min} MW/min")
        print(
            f"  Reserve eligible: spin={row.spinning_eligible}, "
            f"non-spin={row.non_spinning_eligible}"
        )
        print()

    if result.warnings:
        print("Warnings:")
        for w in result.warnings:
            print(f"  - {w}")
        print()


def main(
    output_dir: Path | None = None,
    *,
    commit_hash: str = "master",
) -> StorageReferenceResult:
    """Entry point: download sources, build reference table, write outputs.

    Orchestrates the full workflow:
    1. Download gen.csv and storage.csv from RTS-GMLC at the pinned commit.
    2. Parse storage units from gen.csv and energy params from storage.csv.
    3. Join the two sources.
    4. Build the storage parameter reference table.
    5. Write the reference CSV to data/reference/rts_gmlc_storage_params.csv.
    6. Write the parameter metadata CSV to
       data/reference/rts_gmlc_storage_param_metadata.csv.
    7. Print a summary to stdout.

    Creates data/reference/ and data/reference/raw/ directories if they
    do not exist.

    Args:
        output_dir: Base directory for output. Defaults to
            <repo_root>/data/reference/.
        commit_hash: RTS-GMLC commit hash or tag to pin. Defaults to "master"
            pending resolution of OQ-D3.01-01.

    Returns:
        The complete StorageReferenceResult.
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
    storage_csv_path = download_rts_gmlc_storage_csv(
        raw_dir / "storage.csv",
        commit_hash=commit_hash,
    )

    # Step 2-4: Build reference table.
    result = build_storage_reference(gen_csv_path, storage_csv_path)

    # Update provenance with commit hash.
    result = StorageReferenceResult(
        provenance=StorageProvenance(
            repo_url=result.provenance.repo_url,
            commit_hash=commit_hash,
            gen_csv_path=result.provenance.gen_csv_path,
            storage_csv_path=result.provenance.storage_csv_path,
            download_timestamp=result.provenance.download_timestamp,
            script_version=result.provenance.script_version,
            num_storage_units_parsed=result.provenance.num_storage_units_parsed,
            num_rows_produced=result.provenance.num_rows_produced,
        ),
        params=result.params,
        parameter_metadata=result.parameter_metadata,
        warnings=result.warnings,
    )

    # Step 5: Write reference CSV.
    output_csv = output_dir / "rts_gmlc_storage_params.csv"
    write_storage_reference_csv(result, output_csv, provenance=result.provenance)

    # Step 6: Write parameter metadata CSV.
    metadata_csv = output_dir / "rts_gmlc_storage_param_metadata.csv"
    write_parameter_metadata_csv(result.parameter_metadata, metadata_csv)

    # Step 7: Print summary.
    print_summary(result)

    return result


if __name__ == "__main__":
    main()
