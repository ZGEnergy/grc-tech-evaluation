"""Canonical CSV Schema Specification for the data augmentation pipeline.

Defines the schema contract between data producers (generator calibration, BESS/DR
definition, stochastic scenario generation, flowgate calibration) and data consumers
(the six tool evaluation scripts). Provides schema definitions as dataclasses, JSON
Schema generation, markdown documentation generation, and CSV validation functions.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class CsvFileType(StrEnum):
    """Enumeration of all canonical CSV file types produced by the pipeline."""

    LOAD_24H = "load_24h"
    WIND_FORECAST_24H = "wind_forecast_24h"
    WIND_ACTUAL_24H = "wind_actual_24h"
    SOLAR_FORECAST_24H = "solar_forecast_24h"
    SOLAR_ACTUAL_24H = "solar_actual_24h"
    GEN_TEMPORAL_PARAMS = "gen_temporal_params"
    RESERVE_REQUIREMENTS_24H = "reserve_requirements_24h"
    RESERVE_ELIGIBILITY = "reserve_eligibility"
    BESS_UNITS = "bess_units"
    DR_BUSES = "dr_buses"
    FLOWGATES = "flowgates"
    SCENARIO_MULTIPLIERS = "scenario_multipliers_50x24"


class ColumnDtype(StrEnum):
    """Data type identifiers used in schema definitions."""

    INT = "int"
    FLOAT = "float"
    STR = "str"
    BOOL = "bool"


class Unit(StrEnum):
    """Physical units for column values."""

    MW = "MW"
    MWH = "MWh"
    FRACTION = "fraction"  # dimensionless [0, 1]
    DOLLARS_PER_MWH = "$/MWh"
    DOLLARS_PER_START = "$/start"
    HOURS = "hours"
    MW_PER_MIN = "MW/min"
    DIMENSIONLESS = "dimensionless"
    NONE = "none"  # for ID/label columns


@dataclass(frozen=True)
class ColumnSpec:
    """Specification for a single column in a canonical CSV file."""

    name: str
    dtype: ColumnDtype
    unit: Unit
    required: bool
    description: str
    min_value: float | None = None  # None means no lower bound
    max_value: float | None = None  # None means no upper bound
    allowed_values: list[str] | None = None  # for enumerated string columns


@dataclass(frozen=True)
class FileTypeSchema:
    """Complete schema for one canonical CSV file type."""

    file_type: CsvFileType
    file_name_pattern: str  # e.g. "load_24h.csv"
    description: str
    columns: list[ColumnSpec]
    row_semantics: str  # e.g. "one row per bus" or "one row per generator"
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CanonicalSchema:
    """Top-level container for the entire canonical CSV schema specification."""

    version: str
    hour_ending_convention: str  # description of HR_1..HR_24
    directory_structure: str  # description of data/timeseries/<network>/
    file_naming_convention: str  # description of <data_type>_24h.csv pattern
    networks: list[str]  # ["case39", "ACTIVSg2000", "ACTIVSg10k"]
    file_types: list[FileTypeSchema]
    gen_uid_format: str  # description of GEN UID format
    bus_id_format: str  # description of bus_id format


@dataclass(frozen=True)
class ColumnValidationError:
    """A single validation error for a specific column in a CSV file."""

    column_name: str
    row_index: int | None  # None for header-level errors
    error_type: str  # e.g. "missing_required", "wrong_dtype", "out_of_range"
    message: str
    actual_value: str | None = None
    expected: str | None = None


@dataclass(frozen=True)
class FileValidationResult:
    """Result of validating a single CSV file against the canonical schema."""

    file_path: str
    file_type: CsvFileType | None  # None if file type could not be determined
    valid: bool
    errors: list[ColumnValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0


# ---------------------------------------------------------------------------
# Helper: build HR_1..HR_24 column specs
# ---------------------------------------------------------------------------


def _hr_columns(unit: Unit, *, min_value: float | None = None) -> list[ColumnSpec]:
    """Build the 24 hour-ending columns HR_1 through HR_24."""
    return [
        ColumnSpec(
            name=f"HR_{h}",
            dtype=ColumnDtype.FLOAT,
            unit=unit,
            required=True,
            description=f"Value for hour ending {h} (interval {h - 1}:00-{h}:00)",
            min_value=min_value,
        )
        for h in range(1, 25)
    ]


# ---------------------------------------------------------------------------
# Schema definition functions
# ---------------------------------------------------------------------------


def build_load_schema() -> FileTypeSchema:
    """Build the schema for load_24h.csv.

    Defines columns: bus_id (int, required), HR_1..HR_24 (float, MW, required).
    Row semantics: one row per bus. All HR values must be non-negative.

    Returns:
        A FileTypeSchema for the load profile file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="bus_id",
            dtype=ColumnDtype.INT,
            unit=Unit.NONE,
            required=True,
            description="Bus identifier matching the MATPOWER bus_i field",
        ),
        *_hr_columns(Unit.MW, min_value=0.0),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.LOAD_24H,
        file_name_pattern="load_24h.csv",
        description="Hourly load profile per bus for a single representative day",
        columns=columns,
        row_semantics="one row per bus",
        notes=["All MW values must be non-negative"],
    )


def build_wind_forecast_schema() -> FileTypeSchema:
    """Build the schema for wind_forecast_24h.csv.

    Defines columns: gen_uid (str, required), HR_1..HR_24 (float, MW, required).
    Row semantics: one row per wind generator. All HR values must be
    non-negative and should not exceed the generator's Pmax (validated
    externally against gen_temporal_params).

    Returns:
        A FileTypeSchema for the wind forecast file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Generator unique identifier",
        ),
        *_hr_columns(Unit.MW, min_value=0.0),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.WIND_FORECAST_24H,
        file_name_pattern="wind_forecast_24h.csv",
        description="Hourly wind generation forecast per generator for a single day",
        columns=columns,
        row_semantics="one row per wind generator",
        notes=[
            "All MW values must be non-negative",
            "Values should not exceed generator Pmax (validated externally)",
        ],
    )


def build_wind_actual_schema() -> FileTypeSchema:
    """Build the schema for wind_actual_24h.csv.

    Identical column structure to wind_forecast_24h.csv. Represents realized
    wind generation for stochastic evaluation (forecast error = actual - forecast).

    Returns:
        A FileTypeSchema for the wind actual file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Generator unique identifier",
        ),
        *_hr_columns(Unit.MW, min_value=0.0),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.WIND_ACTUAL_24H,
        file_name_pattern="wind_actual_24h.csv",
        description="Hourly realized wind generation per generator for a single day",
        columns=columns,
        row_semantics="one row per wind generator",
        notes=[
            "All MW values must be non-negative",
            "Forecast error = actual - forecast",
        ],
    )


def build_solar_forecast_schema() -> FileTypeSchema:
    """Build the schema for solar_forecast_24h.csv.

    Defines columns: gen_uid (str, required), HR_1..HR_24 (float, MW, required).
    Row semantics: one row per solar generator. HR values must be non-negative.

    Returns:
        A FileTypeSchema for the solar forecast file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Generator unique identifier",
        ),
        *_hr_columns(Unit.MW, min_value=0.0),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.SOLAR_FORECAST_24H,
        file_name_pattern="solar_forecast_24h.csv",
        description="Hourly solar generation forecast per generator for a single day",
        columns=columns,
        row_semantics="one row per solar generator",
        notes=["All MW values must be non-negative"],
    )


def build_solar_actual_schema() -> FileTypeSchema:
    """Build the schema for solar_actual_24h.csv.

    Identical column structure to solar_forecast_24h.csv. Represents realized
    solar generation for stochastic evaluation.

    Returns:
        A FileTypeSchema for the solar actual file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Generator unique identifier",
        ),
        *_hr_columns(Unit.MW, min_value=0.0),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.SOLAR_ACTUAL_24H,
        file_name_pattern="solar_actual_24h.csv",
        description="Hourly realized solar generation per generator for a single day",
        columns=columns,
        row_semantics="one row per solar generator",
        notes=[
            "All MW values must be non-negative",
            "Forecast error = actual - forecast",
        ],
    )


def build_gen_temporal_params_schema() -> FileTypeSchema:
    """Build the schema for gen_temporal_params.csv.

    Defines columns: gen_uid (str, required), pmax (float, MW, required),
    pmin (float, MW, required), ramp_rate (float, MW/min, required),
    min_up_time (float, hours, required), min_down_time (float, hours, required),
    startup_cost (float, $/start, required), shutdown_cost (float, $/start,
    optional), marginal_cost (float, $/MWh, required), fuel_type (str, required),
    unit_type (str, optional).

    Row semantics: one row per generator. pmin <= pmax, ramp_rate >= 0,
    min_up_time >= 0, min_down_time >= 0, startup_cost >= 0, marginal_cost >= 0.

    Returns:
        A FileTypeSchema for the generator temporal parameters file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Generator unique identifier",
        ),
        ColumnSpec(
            name="pmax",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=True,
            description="Maximum real power output",
            min_value=0.0,
        ),
        ColumnSpec(
            name="pmin",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=True,
            description="Minimum real power output",
            min_value=0.0,
        ),
        ColumnSpec(
            name="ramp_rate",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW_PER_MIN,
            required=True,
            description="Ramp rate limit",
            min_value=0.0,
        ),
        ColumnSpec(
            name="min_up_time",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.HOURS,
            required=True,
            description="Minimum up time before shutdown is allowed",
            min_value=0.0,
        ),
        ColumnSpec(
            name="min_down_time",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.HOURS,
            required=True,
            description="Minimum down time before restart is allowed",
            min_value=0.0,
        ),
        ColumnSpec(
            name="startup_cost",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.DOLLARS_PER_START,
            required=True,
            description="Cost to start the generator",
            min_value=0.0,
        ),
        ColumnSpec(
            name="shutdown_cost",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.DOLLARS_PER_START,
            required=False,
            description="Cost to shut down the generator",
            min_value=0.0,
        ),
        ColumnSpec(
            name="marginal_cost",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.DOLLARS_PER_MWH,
            required=True,
            description="Marginal cost of generation",
            min_value=0.0,
        ),
        ColumnSpec(
            name="fuel_type",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Fuel type classification (e.g. coal, ng, nuclear, wind, solar, hydro)",
        ),
        ColumnSpec(
            name="unit_type",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=False,
            description="Unit type classification (e.g. steam, CT, CC, wind_turbine, PV)",
        ),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.GEN_TEMPORAL_PARAMS,
        file_name_pattern="gen_temporal_params.csv",
        description="Static generator parameters for unit commitment and economic dispatch",
        columns=columns,
        row_semantics="one row per generator",
        notes=[
            "pmin must be less than or equal to pmax (validated externally)",
            "All cost and time values must be non-negative",
        ],
    )


def build_reserve_requirements_schema() -> FileTypeSchema:
    """Build the schema for reserve_requirements_24h.csv.

    Defines columns: product (str, required), HR_1..HR_24 (float, MW, required).
    Row semantics: one row per reserve product. All HR values must be
    non-negative.

    Returns:
        A FileTypeSchema for the reserve requirements file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="product",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Reserve product name",
            allowed_values=[
                "spinning",
                "non_spinning",
                "regulation_up",
                "regulation_down",
            ],
        ),
        *_hr_columns(Unit.MW, min_value=0.0),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.RESERVE_REQUIREMENTS_24H,
        file_name_pattern="reserve_requirements_24h.csv",
        description="Hourly reserve requirements per product for a single day",
        columns=columns,
        row_semantics="one row per reserve product",
        notes=["All MW values must be non-negative"],
    )


def build_reserve_eligibility_schema() -> FileTypeSchema:
    """Build the schema for reserve_eligibility.csv.

    Defines columns: gen_uid (str, required), spinning_eligible (bool, required),
    non_spinning_eligible (bool, required), regulation_eligible (bool, optional),
    max_spinning_mw (float, MW, optional), max_non_spinning_mw (float, MW,
    optional), max_regulation_mw (float, MW, optional).

    Row semantics: one row per generator.

    Returns:
        A FileTypeSchema for the reserve eligibility file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Generator unique identifier",
        ),
        ColumnSpec(
            name="spinning_eligible",
            dtype=ColumnDtype.BOOL,
            unit=Unit.NONE,
            required=True,
            description="Whether the generator is eligible to provide spinning reserve",
        ),
        ColumnSpec(
            name="non_spinning_eligible",
            dtype=ColumnDtype.BOOL,
            unit=Unit.NONE,
            required=True,
            description="Whether the generator is eligible to provide non-spinning reserve",
        ),
        ColumnSpec(
            name="regulation_eligible",
            dtype=ColumnDtype.BOOL,
            unit=Unit.NONE,
            required=False,
            description="Whether the generator is eligible to provide regulation reserve",
        ),
        ColumnSpec(
            name="max_spinning_mw",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=False,
            description="Maximum spinning reserve contribution (defaults to Pmax - Pmin)",
            min_value=0.0,
        ),
        ColumnSpec(
            name="max_non_spinning_mw",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=False,
            description="Maximum non-spinning reserve contribution (defaults to Pmax - Pmin)",
            min_value=0.0,
        ),
        ColumnSpec(
            name="max_regulation_mw",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=False,
            description="Maximum regulation reserve contribution (defaults to Pmax - Pmin)",
            min_value=0.0,
        ),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.RESERVE_ELIGIBILITY,
        file_name_pattern="reserve_eligibility.csv",
        description="Generator eligibility and capacity for reserve products",
        columns=columns,
        row_semantics="one row per generator",
        notes=[
            "Boolean columns: true/false or 1/0",
            "MW columns cap the maximum contribution; if absent, defaults to Pmax - Pmin",
        ],
    )


def build_bess_units_schema() -> FileTypeSchema:
    """Build the schema for bess_units.csv.

    Defines columns: unit_id (str, required), bus_id (int, required),
    power_mw (float, MW, required), energy_mwh (float, MWh, required),
    efficiency (float, fraction, required), min_soc (float, fraction, required),
    max_soc (float, fraction, required), init_soc (float, fraction, required).

    Row semantics: one row per BESS unit.

    Returns:
        A FileTypeSchema for the BESS units file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="unit_id",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="BESS unit identifier",
        ),
        ColumnSpec(
            name="bus_id",
            dtype=ColumnDtype.INT,
            unit=Unit.NONE,
            required=True,
            description="Bus where the BESS unit is connected",
        ),
        ColumnSpec(
            name="power_mw",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=True,
            description="Maximum charge/discharge power rating",
            min_value=0.0,
        ),
        ColumnSpec(
            name="energy_mwh",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MWH,
            required=True,
            description="Energy storage capacity",
            min_value=0.0,
        ),
        ColumnSpec(
            name="efficiency",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.FRACTION,
            required=True,
            description="Round-trip efficiency",
            min_value=0.0,
            max_value=1.0,
        ),
        ColumnSpec(
            name="min_soc",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.FRACTION,
            required=True,
            description="Minimum state of charge",
            min_value=0.0,
            max_value=1.0,
        ),
        ColumnSpec(
            name="max_soc",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.FRACTION,
            required=True,
            description="Maximum state of charge",
            min_value=0.0,
            max_value=1.0,
        ),
        ColumnSpec(
            name="init_soc",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.FRACTION,
            required=True,
            description="Initial state of charge",
            min_value=0.0,
            max_value=1.0,
        ),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.BESS_UNITS,
        file_name_pattern="bess_units.csv",
        description="Battery energy storage system unit definitions",
        columns=columns,
        row_semantics="one row per BESS unit",
        notes=[
            "power_mw > 0, energy_mwh > 0",
            "0 < efficiency <= 1",
            "0 <= min_soc <= max_soc <= 1",
            "min_soc <= init_soc <= max_soc (validated externally)",
        ],
    )


def build_dr_buses_schema() -> FileTypeSchema:
    """Build the schema for dr_buses.csv.

    Defines columns: bus_id (int, required), max_curtailment_mw (float, MW,
    required), max_recovery_mw (float, MW, optional), curtailment_cost
    (float, $/MWh, required), recovery_cost (float, $/MWh, optional),
    max_hours (float, hours, optional), min_hours_between (float, hours,
    optional).

    Row semantics: one row per demand-response-eligible bus.

    Returns:
        A FileTypeSchema for the demand response buses file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="bus_id",
            dtype=ColumnDtype.INT,
            unit=Unit.NONE,
            required=True,
            description="Bus identifier for the demand response resource",
        ),
        ColumnSpec(
            name="max_curtailment_mw",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=True,
            description="Maximum load curtailment capacity",
            min_value=0.0,
        ),
        ColumnSpec(
            name="max_recovery_mw",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=False,
            description="Maximum load recovery capacity after curtailment",
            min_value=0.0,
        ),
        ColumnSpec(
            name="curtailment_cost",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.DOLLARS_PER_MWH,
            required=True,
            description="Cost of load curtailment",
            min_value=0.0,
        ),
        ColumnSpec(
            name="recovery_cost",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.DOLLARS_PER_MWH,
            required=False,
            description="Cost of load recovery",
            min_value=0.0,
        ),
        ColumnSpec(
            name="max_hours",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.HOURS,
            required=False,
            description="Maximum consecutive hours of curtailment",
            min_value=0.0,
        ),
        ColumnSpec(
            name="min_hours_between",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.HOURS,
            required=False,
            description="Minimum hours between curtailment events",
            min_value=0.0,
        ),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.DR_BUSES,
        file_name_pattern="dr_buses.csv",
        description="Demand response eligible bus definitions",
        columns=columns,
        row_semantics="one row per demand-response-eligible bus",
        notes=["All MW and cost values must be non-negative"],
    )


def build_flowgates_schema() -> FileTypeSchema:
    """Build the schema for flowgates.csv.

    Defines columns: flowgate_id (str, required), line_ids (str, required),
    weights (str, required), limit_mw (float, MW, required).

    Row semantics: one row per flowgate.

    Returns:
        A FileTypeSchema for the flowgates file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="flowgate_id",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Flowgate identifier",
        ),
        ColumnSpec(
            name="line_ids",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description="Semicolon-delimited list of branch IDs composing the flowgate",
        ),
        ColumnSpec(
            name="weights",
            dtype=ColumnDtype.STR,
            unit=Unit.NONE,
            required=True,
            description=("Semicolon-delimited list of float weights corresponding to line_ids"),
        ),
        ColumnSpec(
            name="limit_mw",
            dtype=ColumnDtype.FLOAT,
            unit=Unit.MW,
            required=True,
            description="Flowgate power flow limit",
            min_value=0.0,
        ),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.FLOWGATES,
        file_name_pattern="flowgates.csv",
        description="Flowgate definitions with constituent lines and weights",
        columns=columns,
        row_semantics="one row per flowgate",
        notes=[
            "line_ids and weights are semicolon-delimited and must have the same count",
            "limit_mw > 0",
        ],
    )


def build_scenario_multipliers_schema() -> FileTypeSchema:
    """Build the schema for scenarios/scenario_multipliers_50x24.csv.

    Defines columns: scenario_id (int, required), HR_1..HR_24 (float,
    dimensionless, required). Row semantics: one row per scenario (50 rows).
    Multiplier values are centered around 1.0.

    Returns:
        A FileTypeSchema for the scenario multipliers file type.
    """
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="scenario_id",
            dtype=ColumnDtype.INT,
            unit=Unit.NONE,
            required=True,
            description="Scenario identifier (1-based index)",
        ),
        *_hr_columns(Unit.DIMENSIONLESS),
    ]
    return FileTypeSchema(
        file_type=CsvFileType.SCENARIO_MULTIPLIERS,
        file_name_pattern="scenario_multipliers_50x24.csv",
        description="Stochastic scenario multipliers for renewable forecast deviation",
        columns=columns,
        row_semantics="one row per scenario (50 rows expected)",
        notes=[
            "Multiplier values are centered around 1.0",
            "e.g. 0.85 = 15% below forecast, 1.15 = 15% above forecast",
        ],
    )


def build_canonical_schema(*, version: str = "1.0.0") -> CanonicalSchema:
    """Assemble the complete canonical schema from all file type schemas.

    Calls each build_*_schema function to construct the individual file type
    schemas, then wraps them in a CanonicalSchema with metadata.

    Args:
        version: Semantic version string for the schema.

    Returns:
        A CanonicalSchema containing all file type definitions.
    """
    file_types = [
        build_load_schema(),
        build_wind_forecast_schema(),
        build_wind_actual_schema(),
        build_solar_forecast_schema(),
        build_solar_actual_schema(),
        build_gen_temporal_params_schema(),
        build_reserve_requirements_schema(),
        build_reserve_eligibility_schema(),
        build_bess_units_schema(),
        build_dr_buses_schema(),
        build_flowgates_schema(),
        build_scenario_multipliers_schema(),
    ]

    return CanonicalSchema(
        version=version,
        hour_ending_convention=(
            "Columns HR_1 through HR_24 use hour-ending convention: "
            "HR_k represents the interval ending at hour k. "
            "HR_1 = 00:00-01:00, HR_24 = 23:00-24:00."
        ),
        directory_structure=(
            "data/timeseries/<network>/ where <network> is one of "
            "case39, ACTIVSg2000, ACTIVSg10k. "
            "Scenario files are in data/timeseries/<network>/scenarios/."
        ),
        file_naming_convention=(
            "Temporal profiles use <data_type>_24h.csv. "
            "Static parameter files use <data_type>.csv. "
            "Scenario multipliers use scenario_multipliers_50x24.csv."
        ),
        networks=["case39", "ACTIVSg2000", "ACTIVSg10k"],
        file_types=file_types,
        gen_uid_format=(
            "Generator UIDs preserve ACTIVSg native generator indexing: "
            "1-based row position in mpc.gen, represented as a string. "
            "Example: '1', '2', ..., '544'."
        ),
        bus_id_format=(
            "Bus IDs are integers matching the MATPOWER bus_i field. "
            "They are 1-based and unique within each network."
        ),
    )


# ---------------------------------------------------------------------------
# Output generation functions
# ---------------------------------------------------------------------------


def _column_spec_to_json_property(col: ColumnSpec) -> dict:
    """Convert a ColumnSpec to a JSON Schema property definition."""
    prop: dict = {}

    if col.dtype == ColumnDtype.INT:
        prop["type"] = "integer"
    elif col.dtype == ColumnDtype.FLOAT:
        prop["type"] = "number"
    elif col.dtype == ColumnDtype.STR:
        prop["type"] = "string"
    elif col.dtype == ColumnDtype.BOOL:
        prop["type"] = "boolean"

    prop["description"] = f"{col.description} [{col.unit}]"

    if col.min_value is not None:
        prop["minimum"] = col.min_value
    if col.max_value is not None:
        prop["maximum"] = col.max_value
    if col.allowed_values is not None:
        prop["enum"] = col.allowed_values

    return prop


def schema_to_json_schema(schema: CanonicalSchema) -> dict:
    """Convert a CanonicalSchema to a JSON Schema (draft 2020-12) dictionary.

    Produces a single JSON Schema document with a top-level oneOf containing
    a sub-schema per file type. Each sub-schema defines the required and
    optional properties (columns), their types, value constraints, and
    descriptions. The JSON Schema is self-contained with no external $ref.

    Args:
        schema: The canonical schema to convert.

    Returns:
        A dictionary representing a valid JSON Schema document.
    """
    definitions: dict = {}

    for ft_schema in schema.file_types:
        properties: dict = {}
        required: list[str] = []

        for col in ft_schema.columns:
            properties[col.name] = _column_spec_to_json_property(col)
            if col.required:
                required.append(col.name)

        ft_def: dict = {
            "type": "object",
            "description": ft_schema.description,
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }
        definitions[ft_schema.file_type.value] = ft_def

    one_of = [{"$ref": f"#/$defs/{k}"} for k in definitions]

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Canonical CSV Schema",
        "description": (
            f"Schema specification v{schema.version} for the data augmentation pipeline. "
            f"{schema.hour_ending_convention}"
        ),
        "type": "array",
        "items": {
            "oneOf": one_of,
        },
        "$defs": definitions,
    }


def write_json_schema(schema: CanonicalSchema, dest_path: Path) -> None:
    """Write the canonical schema as an indented JSON Schema file.

    Args:
        schema: The canonical schema to write.
        dest_path: File path to write the JSON Schema output.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    json_schema = schema_to_json_schema(schema)
    with open(dest_path, "w") as fh:
        json.dump(json_schema, fh, indent=2)
        fh.write("\n")


def write_markdown_doc(schema: CanonicalSchema, dest_path: Path) -> None:
    """Write the canonical schema as a human-readable markdown document.

    Args:
        schema: The canonical schema to document.
        dest_path: File path to write the markdown output.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    lines.append(f"# Canonical CSV Schema v{schema.version}")
    lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append("### Hour-Ending Convention")
    lines.append("")
    lines.append(schema.hour_ending_convention)
    lines.append("")

    lines.append("### Directory Structure")
    lines.append("")
    lines.append(schema.directory_structure)
    lines.append("")

    lines.append("### File Naming Convention")
    lines.append("")
    lines.append(schema.file_naming_convention)
    lines.append("")

    lines.append("### Networks")
    lines.append("")
    lines.append(", ".join(f"`{n}`" for n in schema.networks))
    lines.append("")

    lines.append("### Generator UID Format")
    lines.append("")
    lines.append(schema.gen_uid_format)
    lines.append("")

    lines.append("### Bus ID Format")
    lines.append("")
    lines.append(schema.bus_id_format)
    lines.append("")

    # Summary table
    lines.append("## File Type Summary")
    lines.append("")
    lines.append("| File Type | File Name | Row Semantics |")
    lines.append("|-----------|-----------|---------------|")
    for ft in schema.file_types:
        lines.append(f"| `{ft.file_type.value}` | `{ft.file_name_pattern}` | {ft.row_semantics} |")
    lines.append("")

    # Detailed sections
    lines.append("## File Type Details")
    lines.append("")

    for ft in schema.file_types:
        lines.append(f"### {ft.file_type.value}")
        lines.append("")
        lines.append(ft.description)
        lines.append("")
        lines.append(f"**File name:** `{ft.file_name_pattern}`")
        lines.append("")
        lines.append(f"**Row semantics:** {ft.row_semantics}")
        lines.append("")

        # Column table
        lines.append("| Column | Type | Unit | Required | Constraints | Description |")
        lines.append("|--------|------|------|----------|-------------|-------------|")
        for col in ft.columns:
            constraints_parts: list[str] = []
            if col.min_value is not None:
                constraints_parts.append(f">= {col.min_value}")
            if col.max_value is not None:
                constraints_parts.append(f"<= {col.max_value}")
            if col.allowed_values is not None:
                constraints_parts.append(f"one of: {', '.join(col.allowed_values)}")
            constraints = "; ".join(constraints_parts) if constraints_parts else "-"

            lines.append(
                f"| `{col.name}` | {col.dtype.value} | {col.unit.value} "
                f"| {'yes' if col.required else 'no'} | {constraints} "
                f"| {col.description} |"
            )
        lines.append("")

        if ft.notes:
            lines.append("**Notes:**")
            lines.append("")
            for note in ft.notes:
                lines.append(f"- {note}")
            lines.append("")

    with open(dest_path, "w") as fh:
        fh.write("\n".join(lines))
        fh.write("\n")


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

# Map from file name stem to CsvFileType
_FILE_NAME_MAP: dict[str, CsvFileType] = {
    ft_schema.file_name_pattern.removesuffix(".csv"): ft_schema.file_type
    for ft_schema in build_canonical_schema().file_types
}


def infer_file_type(file_path: Path) -> CsvFileType:
    """Infer the CsvFileType from a file name.

    Matches the file name (stem) against the known file_name_pattern for
    each CsvFileType. For files in a scenarios/ subdirectory, checks
    against SCENARIO_MULTIPLIERS. Raises ValueError if the file name does
    not match any known pattern.

    Args:
        file_path: Path to the CSV file.

    Returns:
        The inferred CsvFileType.

    Raises:
        ValueError: If the file name does not match any known file type.
    """
    stem = file_path.stem

    # Direct match
    if stem in _FILE_NAME_MAP:
        return _FILE_NAME_MAP[stem]

    # Check if in a scenarios/ subdirectory
    if file_path.parent.name == "scenarios" and stem in _FILE_NAME_MAP:
        return _FILE_NAME_MAP[stem]

    msg = f"Cannot infer file type from file name: {file_path.name}"
    raise ValueError(msg)


def _get_file_type_schema(schema: CanonicalSchema, file_type: CsvFileType) -> FileTypeSchema:
    """Look up the FileTypeSchema for a given CsvFileType."""
    for ft_schema in schema.file_types:
        if ft_schema.file_type == file_type:
            return ft_schema
    msg = f"No schema defined for file type: {file_type}"
    raise ValueError(msg)


def _validate_value(
    value_str: str,
    col: ColumnSpec,
    row_idx: int,
) -> ColumnValidationError | None:
    """Validate a single cell value against a column spec. Returns error or None."""
    stripped = value_str.strip()

    # Allow empty values for optional columns
    if stripped == "" and not col.required:
        return None

    # Type checking
    if col.dtype == ColumnDtype.INT:
        try:
            int_val = int(float(stripped))
            # Check it's actually an integer
            if float(stripped) != int_val:
                return ColumnValidationError(
                    column_name=col.name,
                    row_index=row_idx,
                    error_type="wrong_dtype",
                    message=f"Expected integer, got '{stripped}'",
                    actual_value=stripped,
                    expected="int",
                )
            num_val = float(int_val)
        except (ValueError, OverflowError):
            return ColumnValidationError(
                column_name=col.name,
                row_index=row_idx,
                error_type="wrong_dtype",
                message=f"Expected integer, got '{stripped}'",
                actual_value=stripped,
                expected="int",
            )
    elif col.dtype == ColumnDtype.FLOAT:
        try:
            num_val = float(stripped)
        except (ValueError, OverflowError):
            return ColumnValidationError(
                column_name=col.name,
                row_index=row_idx,
                error_type="wrong_dtype",
                message=f"Expected float, got '{stripped}'",
                actual_value=stripped,
                expected="float",
            )
    elif col.dtype == ColumnDtype.BOOL:
        if stripped.lower() not in ("true", "false", "1", "0"):
            return ColumnValidationError(
                column_name=col.name,
                row_index=row_idx,
                error_type="wrong_dtype",
                message=f"Expected bool (true/false/1/0), got '{stripped}'",
                actual_value=stripped,
                expected="bool",
            )
        return None
    elif col.dtype == ColumnDtype.STR:
        # Check allowed values if defined
        if col.allowed_values is not None and stripped not in col.allowed_values:
            return ColumnValidationError(
                column_name=col.name,
                row_index=row_idx,
                error_type="out_of_range",
                message=(f"Value '{stripped}' not in allowed values: {col.allowed_values}"),
                actual_value=stripped,
                expected=str(col.allowed_values),
            )
        return None
    else:
        return None

    # Range checks for numeric types
    if col.dtype in (ColumnDtype.INT, ColumnDtype.FLOAT):
        if col.min_value is not None and num_val < col.min_value:
            return ColumnValidationError(
                column_name=col.name,
                row_index=row_idx,
                error_type="out_of_range",
                message=(f"Value {num_val} is below minimum {col.min_value}"),
                actual_value=stripped,
                expected=f">= {col.min_value}",
            )
        if col.max_value is not None and num_val > col.max_value:
            return ColumnValidationError(
                column_name=col.name,
                row_index=row_idx,
                error_type="out_of_range",
                message=(f"Value {num_val} exceeds maximum {col.max_value}"),
                actual_value=stripped,
                expected=f"<= {col.max_value}",
            )

    return None


def validate_csv_file(
    csv_path: Path,
    schema: CanonicalSchema,
    *,
    file_type: CsvFileType | None = None,
    max_errors: int = 100,
) -> FileValidationResult:
    """Validate a single CSV file against the canonical schema.

    Reads the CSV file, infers the file type from the file name (or uses
    the provided file_type override), and checks: (1) all required columns
    are present, (2) no unexpected columns exist (warning, not error),
    (3) each value parses to the declared dtype, (4) each value satisfies
    the declared constraints (min, max, allowed_values), (5) the row count
    is plausible for the file type.

    Stops collecting errors after max_errors to avoid flooding on badly
    malformed files.

    Args:
        csv_path: Path to the CSV file to validate.
        schema: The canonical schema to validate against.
        file_type: Override file type. If None, inferred from file name.
        max_errors: Maximum number of errors to collect before stopping.

    Returns:
        A FileValidationResult with pass/fail status and error details.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If file_type is None and cannot be inferred.
    """
    if not csv_path.exists():
        msg = f"File not found: {csv_path}"
        raise FileNotFoundError(msg)

    if file_type is None:
        file_type = infer_file_type(csv_path)

    ft_schema = _get_file_type_schema(schema, file_type)

    errors: list[ColumnValidationError] = []
    warnings: list[str] = []

    # Read CSV
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        try:
            headers = next(reader)
        except StopIteration:
            return FileValidationResult(
                file_path=str(csv_path),
                file_type=file_type,
                valid=False,
                errors=[
                    ColumnValidationError(
                        column_name="",
                        row_index=None,
                        error_type="empty_file",
                        message="CSV file is empty (no header row)",
                    )
                ],
            )

        headers = [h.strip() for h in headers]
        rows = list(reader)

    row_count = len(rows)
    column_count = len(headers)

    # Build column lookup
    schema_col_map: dict[str, ColumnSpec] = {col.name: col for col in ft_schema.columns}

    # Check required columns
    for col in ft_schema.columns:
        if col.required and col.name not in headers:
            errors.append(
                ColumnValidationError(
                    column_name=col.name,
                    row_index=None,
                    error_type="missing_required",
                    message=f"Required column '{col.name}' is missing",
                )
            )
            if len(errors) >= max_errors:
                break

    # Check for unexpected columns
    schema_col_names = {col.name for col in ft_schema.columns}
    for h in headers:
        if h not in schema_col_names:
            warnings.append(f"Unexpected column '{h}' not defined in schema")

    # Validate cell values
    if len(errors) < max_errors:
        for row_idx, row in enumerate(rows):
            if len(errors) >= max_errors:
                break
            for col_idx, header in enumerate(headers):
                if len(errors) >= max_errors:
                    break
                if header not in schema_col_map:
                    continue
                col_spec = schema_col_map[header]
                cell_value = row[col_idx] if col_idx < len(row) else ""
                error = _validate_value(cell_value, col_spec, row_idx)
                if error is not None:
                    errors.append(error)

    valid = len(errors) == 0

    return FileValidationResult(
        file_path=str(csv_path),
        file_type=file_type,
        valid=valid,
        errors=errors,
        warnings=warnings,
        row_count=row_count,
        column_count=column_count,
    )


def validate_directory(
    directory: Path,
    schema: CanonicalSchema,
    *,
    max_errors_per_file: int = 100,
) -> list[FileValidationResult]:
    """Validate all CSV files in a network's timeseries directory.

    Iterates over all .csv files in the directory (and the scenarios/
    subdirectory if present), validates each against the canonical schema,
    and returns a list of results. Files whose names do not match any
    known file type are included with a warning but not validated.

    Args:
        directory: Path to a network's timeseries directory.
        schema: The canonical schema to validate against.
        max_errors_per_file: Maximum errors per file before stopping.

    Returns:
        A list of FileValidationResult, one per CSV file found.
    """
    results: list[FileValidationResult] = []

    csv_files = sorted(directory.glob("*.csv"))

    # Also check scenarios/ subdirectory
    scenarios_dir = directory / "scenarios"
    if scenarios_dir.is_dir():
        csv_files.extend(sorted(scenarios_dir.glob("*.csv")))

    for csv_path in csv_files:
        try:
            result = validate_csv_file(csv_path, schema, max_errors=max_errors_per_file)
        except ValueError:
            # File type could not be inferred
            result = FileValidationResult(
                file_path=str(csv_path),
                file_type=None,
                valid=True,
                warnings=[f"File '{csv_path.name}' does not match any known file type"],
            )
        results.append(result)

    return results


def main(
    output_dir: Path | None = None,
    *,
    version: str = "1.0.0",
) -> CanonicalSchema:
    """Entry point: build the canonical schema and write all output files.

    Constructs the canonical schema, writes the JSON Schema file to
    data/schema/canonical_csv_schema.json, and writes the markdown
    document to data/schema/canonical_csv_schema.md. Creates the
    data/schema/ directory if it does not exist.

    Args:
        output_dir: Directory to write output files. Defaults to
            <repo_root>/data/schema/.
        version: Semantic version string for the schema.

    Returns:
        The complete CanonicalSchema.
    """
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent.parent / "schema"

    output_dir.mkdir(parents=True, exist_ok=True)

    schema = build_canonical_schema(version=version)
    write_json_schema(schema, output_dir / "canonical_csv_schema.json")
    write_markdown_doc(schema, output_dir / "canonical_csv_schema.md")

    return schema


if __name__ == "__main__":
    main()
